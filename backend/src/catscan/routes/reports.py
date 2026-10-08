from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..storage.report_store import ReportStore

router = APIRouter(tags=["reports"])


class WordResultQuery(BaseModel):
    results: Optional[str] = None
    conference: Optional[int] = None
    name: Optional[str] = None


@router.get("/api/reports/{report_id}")
async def get_report_by_id(report_id: str):
    """
    Retrieve a previously generated validation report.
    """
    report = ReportStore.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.post("/word")
@router.post("/catscan/word")
async def get_word_result_legacy(query: WordResultQuery):
    """
    Legacy compatibility endpoint for catscan-interface.
    Handles { "results": "<report_id>" } queries when viewing saved reports.
    """
    if query.results:
        report = ReportStore.get_report(query.results)
        if not report:
            return JSONResponse(status_code=404, content={"error": "Report not found."})
        return report

    return JSONResponse(
        status_code=400,
        content={"error": "Direct file scan must use /api/scan/word."}
    )


@router.get("/conferences")
@router.get("/catscan/conferences")
async def list_conferences():
    """
    Returns available conferences for paper checking.
    """
    return [
        {"id": 1, "code": "PASJ Annual Meeting (Current)"},
        {"id": 2, "code": "IPAC'25"},
        {"id": 3, "code": "JACoW Test Conference"}
    ]
