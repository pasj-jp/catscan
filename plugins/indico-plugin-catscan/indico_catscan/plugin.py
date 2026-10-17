import logging
import threading
import requests
from flask import g
from sqlalchemy import event as sa_event

from indico.core import signals
from indico.core.plugins import IndicoPlugin
from indico.modules.events.editing.models.editable import EditableType
from indico.modules.events.editing.models.revisions import EditingRevision, RevisionType
from indico.util.i18n import _
from indico.web.forms.base import IndicoForm
from wtforms.fields import BooleanField, StringField
from wtforms.validators import DataRequired

logger = logging.getLogger('indico.plugin.catscan')


class SettingsForm(IndicoForm):
    api_url = StringField(
        _('CatScan Internal API URL'),
        [DataRequired()],
        description=_('Internal HTTP URL to the CatScan backend service (default: http://127.0.0.1:8000)'),
    )
    auto_scan = BooleanField(
        _('Auto-scan on manuscript upload'),
        default=True,
        description=_('Automatically trigger CatScan review whenever an author submits or updates a paper manuscript.'),
    )
    token = StringField(
        _('CatScan API Token (Optional)'),
        description=_('Optional bearer token or shared secret if CatScan requires authentication.'),
    )


class CatScanPlugin(IndicoPlugin):
    """CatScan Automated Paper Review Plugin

    Connects Indico Paper Editing to CatScan.
    Automatically triggers formatting checks and publishes review feedback
    to the editing timeline when authors upload Word (.docx) or LaTeX (.tex) papers.
    """

    configurable = True
    settings_form = SettingsForm
    default_settings = {
        'api_url': 'http://127.0.0.1:8000',
        'auto_scan': True,
        'token': '',
    }

    def init(self):
        super().init()
        # Connect to Celery task import signal
        self.connect(signals.core.import_tasks, self._import_tasks)
        # Connect to transaction commit signal
        self.connect(signals.core.after_commit, self._after_commit)
        # Listen for new revision insertions
        sa_event.listen(EditingRevision, 'after_insert', self._on_revision_insert)
        logger.info('[CatScan Plugin] Plugin initialized and listeners attached.')

    def _import_tasks(self, sender, **kwargs):
        import indico_catscan.tasks  # noqa: F401

    def _on_revision_insert(self, mapper, connection, target):
        """
        Captured during DB flush when a new EditingRevision is inserted.
        We check if this revision belongs to a Paper and is an upload by the author.
        """
        try:
            # Check if auto_scan is enabled
            if not self.settings.get('auto_scan'):
                return

            # Check if this revision is for a paper
            editable = target.editable
            if not editable or editable.type != EditableType.paper:
                return

            # Only trigger on submissions: new (1), ready_for_review (2), replacement (9)
            if target.type not in (RevisionType.new, RevisionType.ready_for_review, RevisionType.replacement):
                return

            contrib = editable.contribution
            if not contrib:
                return

            event_id = contrib.event_id
            contrib_id = contrib.id

            # Save in Flask g context to trigger once the transaction successfully commits
            if not hasattr(g, '_catscan_pending_scans'):
                g._catscan_pending_scans = set()
            g._catscan_pending_scans.add((event_id, contrib_id))
            logger.info(
                f"[CatScan Plugin] Queued paper scan for Event {event_id}, Contribution {contrib_id} (Rev ID: {target.id})"
            )
        except Exception as e:
            logger.exception(f"[CatScan Plugin] Error inspecting revision insert: {e}")

    def _after_commit(self, sender, **kwargs):
        """
        Executed immediately after the database transaction successfully commits.
        Dispatches Celery tasks or background threads to notify CatScan.
        """
        pending = getattr(g, '_catscan_pending_scans', None)
        if not pending:
            return

        g._catscan_pending_scans = set()
        api_url = self.settings.get('api_url') or 'http://127.0.0.1:8000'
        token = self.settings.get('token') or ''

        for event_id, contrib_id in pending:
            self._dispatch_scan(api_url, event_id, contrib_id, token)

    def _dispatch_scan(self, api_url, event_id, contrib_id, token):
        try:
            from indico_catscan.tasks import trigger_catscan_scan
            trigger_catscan_scan.delay(api_url, event_id, contrib_id, token)
            logger.info(
                f"[CatScan Plugin] Dispatched Celery scan task for Event {event_id}, Contribution {contrib_id}"
            )
        except Exception as e:
            logger.warning(f"[CatScan Plugin] Celery dispatch failed ({e}), falling back to background thread...")
            t = threading.Thread(
                target=self._direct_trigger,
                args=(api_url, event_id, contrib_id, token),
                daemon=True,
            )
            t.start()

    def _direct_trigger(self, api_url, event_id, contrib_id, token):
        endpoint = f"{api_url.rstrip('/')}/api/indico/events/{event_id}/contributions/{contrib_id}/scan"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                json={"post_comment": True},
                timeout=120,
            )
            logger.info(f"[CatScan Plugin] Direct scan trigger response: {resp.status_code}")
        except Exception as e:
            logger.error(f"[CatScan Plugin] Direct scan trigger failed: {e}")
