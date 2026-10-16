from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from ..checkers.factory import get_checker
from ..storage.report_store import ReportStore

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("/word")
async def scan_word(
    file: UploadFile = File(...),
    template: str = Form("auto"),
    conference: Optional[str] = Form(None)
):
    """
    Validate a Microsoft Word (.docx) paper.
    Direct upload without S3 or payload size restrictions.
    """
    if not file.filename.lower().endswith(".docx"):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file format. Only .docx files are accepted."}
        )

    try:
        content = await file.read()
        checker, effective_template = get_checker(doc_type="word", template=template, file_source=content)
        
        conference_id = int(conference) if conference and conference.isdigit() else None
        result = checker.validate(
            file_source=content,
            filename=file.filename,
            conference_id=conference_id
        )

        if "error" in result and result.get("scores") is None:
            status_code = 501 if result.get("code") == "checker_not_implemented" else 400
            return JSONResponse(status_code=status_code, content=result)

        result["detected_template"] = effective_template
        result["template_name"] = "JACoW 英文原稿" if effective_template == "jacow" else "PASJ 和文原稿"

        # Store report for persistent retrieval
        report_id = ReportStore.generate_report_id(result)
        result["report_id"] = report_id
        result["filename"] = file.filename
        ReportStore.save_report(result, report_id=report_id)

        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred while validating the document: {str(e)}"}
        )


class LatexScanRequest(BaseModel):
    filename: str = "document.tex"
    content: str
    template: str = "auto"


@router.post("/latex")
async def scan_latex(req: LatexScanRequest):
    """
    Validate a LaTeX (.tex) manuscript using the requested template checker.
    """
    try:
        checker, effective_template = get_checker(doc_type="latex", template=req.template, file_source=req.content)
        result = checker.validate(req.content, filename=req.filename)
        if "error" in result:
            status_code = 501 if result.get("code") == "checker_not_implemented" else 400
            return JSONResponse(status_code=status_code, content=result)

        result["report_type"] = "latex"
        result["detected_template"] = effective_template
        result["template_name"] = "JACoW 英文原稿" if effective_template == "jacow" else "PASJ 和文原稿"
        report_id = ReportStore.generate_report_id(result)
        result["report_id"] = report_id
        ReportStore.save_report(result, report_id=report_id)
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred while validating LaTeX document: {str(e)}"}
        )
