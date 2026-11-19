import importlib
import sys
import types
from enum import Enum
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _install_indico_stubs():
    """Install minimal stubs for Indico/Flask/WTForms so plugin logic can be unit-tested standalone."""
    indico = types.ModuleType("indico")
    indico_core = types.ModuleType("indico.core")
    indico_signals = types.ModuleType("indico.core.signals")
    indico_signals.core = SimpleNamespace(import_tasks=object(), after_commit=object())

    indico_celery_mod = types.ModuleType("indico.core.celery")

    class _FakeCelery:
        def task(self, *args, **kwargs):
            def decorator(fn):
                class _TaskWrapper:
                    def __call__(self, *a, **kw):
                        return fn(self, *a, **kw)

                    def retry(self, exc=None):
                        raise RuntimeError("RETRY_TRIGGERED") from exc

                    delay = MagicMock()

                return _TaskWrapper()

            return decorator

    indico_celery_mod.celery = _FakeCelery()

    indico_plugins_mod = types.ModuleType("indico.core.plugins")

    class _FakeIndicoPlugin:
        settings = {}

        def init(self):
            pass

        def connect(self, *args, **kwargs):
            pass

    indico_plugins_mod.IndicoPlugin = _FakeIndicoPlugin

    indico_util = types.ModuleType("indico.util")
    indico_i18n = types.ModuleType("indico.util.i18n")
    indico_i18n.make_bound_gettext = lambda domain: (lambda s: s)

    class _EditableType(Enum):
        paper = 1
        poster = 2

    class _RevisionType(Enum):
        new = 1
        ready_for_review = 2
        replacement = 9
        changes_acceptance = 5

    indico_editable = types.ModuleType("indico.modules.events.editing.models.editable")
    indico_editable.EditableType = _EditableType

    indico_revisions = types.ModuleType("indico.modules.events.editing.models.revisions")
    indico_revisions.EditingRevision = object()
    indico_revisions.RevisionType = _RevisionType

    indico_forms_base = types.ModuleType("indico.web.forms.base")
    indico_forms_base.IndicoForm = type("IndicoForm", (), {})

    indico_forms_fields = types.ModuleType("indico.web.forms.fields")
    indico_forms_fields.IndicoPasswordField = lambda *a, **kw: ("password", a, kw)

    flask_mod = types.ModuleType("flask")
    flask_mod.g = SimpleNamespace()

    sa_mod = types.ModuleType("sqlalchemy")
    sa_mod.event = SimpleNamespace(listen=MagicMock())

    wtforms_mod = types.ModuleType("wtforms")
    wtforms_fields = types.ModuleType("wtforms.fields")
    wtforms_fields.BooleanField = lambda *a, **kw: ("bool", a, kw)
    wtforms_fields.StringField = lambda *a, **kw: ("str", a, kw)
    wtforms_validators = types.ModuleType("wtforms.validators")
    wtforms_validators.DataRequired = lambda *a, **kw: ("required", a, kw)

    modules = {
        "indico": indico,
        "indico.core": indico_core,
        "indico.core.signals": indico_signals,
        "indico.core.celery": indico_celery_mod,
        "indico.core.plugins": indico_plugins_mod,
        "indico.util": indico_util,
        "indico.util.i18n": indico_i18n,
        "indico.modules": types.ModuleType("indico.modules"),
        "indico.modules.events": types.ModuleType("indico.modules.events"),
        "indico.modules.events.editing": types.ModuleType("indico.modules.events.editing"),
        "indico.modules.events.editing.models": types.ModuleType("indico.modules.events.editing.models"),
        "indico.modules.events.editing.models.editable": indico_editable,
        "indico.modules.events.editing.models.revisions": indico_revisions,
        "indico.web": types.ModuleType("indico.web"),
        "indico.web.forms": types.ModuleType("indico.web.forms"),
        "indico.web.forms.base": indico_forms_base,
        "indico.web.forms.fields": indico_forms_fields,
        "flask": flask_mod,
        "sqlalchemy": sa_mod,
        "wtforms": wtforms_mod,
        "wtforms.fields": wtforms_fields,
        "wtforms.validators": wtforms_validators,
    }
    try:
        import requests  # noqa: F401
    except ModuleNotFoundError:
        requests_mod = types.ModuleType("requests")

        class _RequestException(Exception):
            pass

        class _HTTPError(_RequestException):
            pass

        requests_mod.RequestException = _RequestException
        requests_mod.HTTPError = _HTTPError
        requests_mod.post = MagicMock()
        modules["requests"] = requests_mod
    return modules


@pytest.fixture
def plugin_modules(monkeypatch):
    stubs = _install_indico_stubs()
    for name, mod in stubs.items():
        monkeypatch.setitem(sys.modules, name, mod)
    for mod_name in ("indico_catscan", "indico_catscan.plugin", "indico_catscan.tasks"):
        sys.modules.pop(mod_name, None)
    plugin_mod = importlib.import_module("indico_catscan.plugin")
    tasks_mod = importlib.import_module("indico_catscan.tasks")
    return plugin_mod, tasks_mod, stubs


def test_task_sends_bearer_token_and_returns_result(plugin_modules, monkeypatch):
    _, tasks_mod, _ = plugin_modules
    fake_resp = MagicMock(status_code=200)
    fake_resp.json.return_value = {"report_id": "abc123", "template": "pasj"}
    post_mock = MagicMock(return_value=fake_resp)
    monkeypatch.setattr(tasks_mod.requests, "post", post_mock)

    res = tasks_mod.trigger_catscan_scan("http://127.0.0.1:8001/", 5, 19, token="secret-tok")
    assert res["report_id"] == "abc123"
    _, kwargs = post_mock.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret-tok"
    assert post_mock.call_args.args[0] == "http://127.0.0.1:8001/api/indico/events/5/contributions/19/scan"


def test_task_does_not_retry_on_400_client_error(plugin_modules, monkeypatch):
    _, tasks_mod, _ = plugin_modules
    fake_resp = MagicMock(status_code=400, text="No editable Word or LaTeX file")
    monkeypatch.setattr(tasks_mod.requests, "post", MagicMock(return_value=fake_resp))

    res = tasks_mod.trigger_catscan_scan("http://127.0.0.1:8001", 5, 19, token="secret-tok")
    assert res["status"] == "skipped"
    assert res["http_status"] == 400


def test_task_retries_on_503_server_error(plugin_modules, monkeypatch):
    _, tasks_mod, _ = plugin_modules
    fake_resp = MagicMock(status_code=503, text="Service unavailable")
    fake_resp.raise_for_status.side_effect = tasks_mod.requests.HTTPError("503")
    monkeypatch.setattr(tasks_mod.requests, "post", MagicMock(return_value=fake_resp))

    with pytest.raises(RuntimeError, match="RETRY_TRIGGERED"):
        tasks_mod.trigger_catscan_scan("http://127.0.0.1:8001", 5, 19)


def test_revision_insert_queues_only_paper_submissions(plugin_modules):
    plugin_mod, _, stubs = plugin_modules
    EditableType = stubs["indico.modules.events.editing.models.editable"].EditableType
    RevisionType = stubs["indico.modules.events.editing.models.revisions"].RevisionType
    flask_g = stubs["flask"].g

    plugin = plugin_mod.CatScanPlugin()
    plugin.settings = {"auto_scan": True, "api_url": "http://127.0.0.1:8001", "token": "tok"}

    # Non-paper editable should be ignored
    poster_target = SimpleNamespace(
        id=1,
        type=RevisionType.new,
        editable=SimpleNamespace(type=EditableType.poster, contribution=SimpleNamespace(event_id=1, id=2)),
    )
    plugin._on_revision_insert(None, None, poster_target)
    assert not hasattr(flask_g, "_catscan_pending_scans")

    # Non-submission revision type should be ignored
    comment_rev = SimpleNamespace(
        id=2,
        type=RevisionType.changes_acceptance,
        editable=SimpleNamespace(type=EditableType.paper, contribution=SimpleNamespace(event_id=1, id=2)),
    )
    plugin._on_revision_insert(None, None, comment_rev)
    assert not hasattr(flask_g, "_catscan_pending_scans")

    # Valid paper submission should be queued
    valid_rev = SimpleNamespace(
        id=3,
        type=RevisionType.ready_for_review,
        editable=SimpleNamespace(type=EditableType.paper, contribution=SimpleNamespace(event_id=7, id=42)),
    )
    plugin._on_revision_insert(None, None, valid_rev)
    assert flask_g._catscan_pending_scans == {(7, 42)}
