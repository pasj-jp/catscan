import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..indico.client import IndicoClient, IndicoAPIError
from ..indico.config import IndicoConfig
from ..indico.service import IndicoScanService

logger = logging.getLogger("catscan.routes.indico")
router = APIRouter(prefix="/api/indico", tags=["indico"])


class ScanRequest(BaseModel):
    post_comment: bool = True
    template: Optional[str] = None


@router.get("/config")
async def get_indico_config():
    """Returns the current Indico integration configuration."""
    cfg = IndicoConfig.get_default()
    return {
        "indico_base_url": cfg.base_url,
        "catscan_base_url": cfg.catscan_base_url,
        "token_configured": bool(cfg.api_token),
    }


@router.get("/events/{event_id}/papers")
async def list_event_papers(event_id: int):
    """
    List all paper submissions for an Indico conference event.
    """
    service = IndicoScanService()
    try:
        papers = service.list_papers(event_id)
        return papers
    except IndicoAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/events/{event_id}/contributions/{contribution_id}")
async def get_contribution(event_id: int, contribution_id: int):
    """
    Get detailed paper editing status and file list for a contribution.
    """
    client = IndicoClient()
    try:
        paper_data = client.get_contribution_paper(event_id, contribution_id)
        return paper_data
    except IndicoAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/events/{event_id}/contributions/{contribution_id}/scan")
async def scan_contribution_paper(
    event_id: int,
    contribution_id: int,
    body: Optional[ScanRequest] = None,
):
    """
    Download the latest revision manuscript (Word .docx or LaTeX .tex) from Indico,
    perform CatScan automated format checks, save the report, and post the review
    comment back to the Indico revision timeline.
    """
    service = IndicoScanService()
    post_comment = body.post_comment if body else True
    template = body.template if body else None

    try:
        result = service.scan_contribution_paper(
            event_id=event_id,
            contribution_id=contribution_id,
            post_comment=post_comment,
            template=template,
        )
        return result
    except IndicoAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error scanning Indico contribution")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/events/{event_id}/scan-all")
async def scan_all_event_papers(
    event_id: int,
    post_comment: bool = Query(True, description="Post review comments to Indico timelines"),
):
    """
    Batch scan all submitted papers in an Indico conference event.
    """
    service = IndicoScanService()
    try:
        papers = service.list_papers(event_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch papers: {str(e)}")

    results = []
    errors = []

    for p in papers:
        contrib_id = p.get("id")
        code = p.get("code") or f"Contrib-{contrib_id}"
        editable = p.get("editable")
        if not editable or editable.get("revision_count", 0) == 0:
            continue

        try:
            res = service.scan_contribution_paper(
                event_id=event_id,
                contribution_id=contrib_id,
                post_comment=post_comment,
            )
            results.append({
                "contribution_id": contrib_id,
                "code": code,
                "status": "success",
                "filename": res.get("filename"),
                "report_id": res.get("report_id"),
                "report_url": res.get("report_url"),
                "comment_posted": res.get("comment_posted"),
            })
        except Exception as e:
            errors.append({
                "contribution_id": contrib_id,
                "code": code,
                "status": "error",
                "error": str(e),
            })

    return {
        "event_id": event_id,
        "scanned_count": len(results),
        "failed_count": len(errors),
        "results": results,
        "errors": errors,
    }
