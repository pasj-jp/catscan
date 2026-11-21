from fastapi import APIRouter, UploadFile, File, Form

from ..errors import DocumentError
from ..services.scanning import scan_document

router = APIRouter(prefix="/api/scan", tags=["scan"])
SUPPORTED_UPLOAD_SUFFIXES = (".docx", ".tex", ".zip", ".tar.gz", ".tgz")


@router.post("/file")
def scan_uploaded_file(
    file: UploadFile = File(...),
    template: str = Form("auto"),
    verify_template: bool = Form(False),
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
    return scan_document(data=data, filename=filename, template=template, verify_template=verify_template)
