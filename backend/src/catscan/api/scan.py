from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form

from ..errors import DocumentError
from ..services.scanning import scan_document

router = APIRouter(prefix="/api/scan", tags=["scan"])
SUPPORTED_UPLOAD_SUFFIXES = (".docx", ".tex", ".zip", ".tar.gz", ".tgz")


class LatexScanRequest(BaseModel):
    content: str
    filename: str = "document.tex"
    template: str = "auto"


@router.post("/word")
def scan_word(
    file: UploadFile = File(...),
    template: str = Form("auto"),
):
    """
    Validate a Microsoft Word (.docx) paper.
    """
    filename = file.filename or "document.docx"
    if not filename.lower().endswith(".docx"):
        raise DocumentError("Invalid file format. Only .docx files are accepted.")
    data = file.file.read()
    return scan_document(data=data, filename=filename, template=template)


@router.post("/latex")
def scan_latex(req: LatexScanRequest):
    """
    Validate a LaTeX (.tex) manuscript.
    """
    data = req.content.encode("utf-8")
    return scan_document(data=data, filename=req.filename, template=req.template)


@router.post("/file")
def scan_uploaded_file(
    file: UploadFile = File(...),
    template: str = Form("auto"),
):
    """
    Validate a manuscript uploaded as .docx, .tex, .zip, .tar.gz, or .tgz.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(SUPPORTED_UPLOAD_SUFFIXES):
        raise DocumentError(
            "Invalid file format. Supported formats: .docx, .tex, .zip, .tar.gz, .tgz."
        )
    data = file.file.read()
    return scan_document(data=data, filename=filename, template=template)
