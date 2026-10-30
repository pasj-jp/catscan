from fastapi import APIRouter
from ..services import reports

router = APIRouter(tags=["reports"])


@router.get("/api/reports/{report_id}")
def get_report_by_id(report_id: str):
    """
    Retrieve a previously generated validation report.
    """
    return reports.load(report_id)
