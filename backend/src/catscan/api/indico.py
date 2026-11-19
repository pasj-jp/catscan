import hmac
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header, Query

from ..errors import AuthenticationError, CatScanError
from ..indico.client import IndicoClient
from ..indico.service import IndicoScanService
from ..settings import get_settings

logger = logging.getLogger("catscan.api.indico")


def verify_internal_token(authorization: Optional[str] = Header(default=None)) -> None:
    """Require Bearer token authentication for internal Indico integration routes."""
    settings = get_settings()
    if settings.internal_api_token:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError("Missing internal Bearer token.")
        token = authorization[len("Bearer "):].strip()
        if not hmac.compare_digest(token, settings.internal_api_token):
            raise AuthenticationError("Invalid internal API token.", status_code=403)
        return

    if settings.require_indico_auth:
        raise CatScanError(
            "Indico API endpoints require CATSCAN_INTERNAL_TOKEN to be configured.",
            status_code=503,
        )


router = APIRouter(
    prefix="/api/indico",
    tags=["indico"],
    dependencies=[Depends(verify_internal_token)],
)


class ScanRequest(BaseModel):
    post_comment: bool = True
    template: Optional[str] = None


@router.get("/config")
def get_indico_config():
    """Returns the current Indico integration configuration."""
    settings = get_settings()
    return {
        "indico_base_url": settings.indico_base_url,
        "catscan_base_url": settings.catscan_base_url,
        "token_configured": bool(settings.indico_api_token),
        "auth_required": settings.require_indico_auth or bool(settings.internal_api_token),
    }


@router.get("/events/{event_id}/papers")
def list_event_papers(event_id: int):
    """
    List all paper submissions for an Indico conference event.
    """
    with IndicoScanService() as service:
        return service.list_papers(event_id)


@router.get("/events/{event_id}/contributions/{contribution_id}")
def get_contribution(event_id: int, contribution_id: int):
    """
    Get detailed paper editing status and file list for a contribution.
    """
    with IndicoClient() as client:
        return client.get_contribution_paper(event_id, contribution_id)


@router.post("/events/{event_id}/contributions/{contribution_id}/scan")
def scan_contribution_paper(
    event_id: int,
    contribution_id: int,
    body: Optional[ScanRequest] = None,
):
    """
    Download the latest revision manuscript (Word .docx, LaTeX .tex, or archive) from Indico,
    perform CatScan automated format checks, save the report, and post the review
    comment back to the Indico revision timeline.
    """
    post_comment = body.post_comment if body else True
    template = body.template if body else None

    with IndicoScanService() as service:
        return service.scan_contribution_paper(
            event_id=event_id,
            contribution_id=contribution_id,
            post_comment=post_comment,
            template=template,
        )


@router.post("/events/{event_id}/scan-all")
def scan_all_event_papers(
    event_id: int,
    post_comment: bool = Query(True, description="Post review comments to Indico timelines"),
):
    """
    Batch scan all submitted papers in an Indico conference event.
    """
    with IndicoScanService() as service:
        return service.scan_event(event_id, post_comment=post_comment)

