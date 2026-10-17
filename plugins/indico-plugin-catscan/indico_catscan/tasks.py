import logging
import requests
from indico.core.celery import celery

logger = logging.getLogger('indico.plugin.catscan')


@celery.task(name='catscan.trigger_scan', bind=True, max_retries=3, default_retry_delay=10)
def trigger_catscan_scan(self, api_url: str, event_id: int, contribution_id: int, token: str = None):
    """
    Background Celery task that notifies CatScan to download and scan the uploaded manuscript.
    """
    endpoint = f"{api_url.rstrip('/')}/api/indico/events/{event_id}/contributions/{contribution_id}/scan"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    logger.info(
        f"[CatScan Plugin] Triggering paper scan: Event {event_id}, Contribution {contribution_id} -> {endpoint}"
    )
    try:
        resp = requests.post(
            endpoint,
            headers=headers,
            json={"post_comment": True},
            timeout=120,
        )
        if resp.status_code != 200:
            logger.warning(f"[CatScan Plugin] API response HTTP {resp.status_code}: {resp.text}")
            resp.raise_for_status()

        res_data = resp.json()
        logger.info(
            f"[CatScan Plugin] Scan succeeded for Contribution {contribution_id}. "
            f"Report ID: {res_data.get('report_id')}, Template: {res_data.get('template')}"
        )
        return res_data
    except Exception as exc:
        logger.error(f"[CatScan Plugin] Failed to trigger CatScan: {exc}")
        raise self.retry(exc=exc)
