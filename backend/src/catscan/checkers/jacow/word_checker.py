import io
from typing import Dict, Any, Union

from ...errors import DocumentError
from ..common.docx_utils import open_docx, doc_metadata
from ..common.score import score
from .doc import create_upload_variables


class JacowWordChecker:
    """
    Standard JACoW Word document format checker.
    Checks styles, margins, typography, headings, tables, figures, citations.
    """

    def check(
        self,
        data: bytes,
        filename: str = "document.docx",
    ) -> Dict[str, Any]:
        doc = open_docx(data)

        details, err = create_upload_variables(doc)
        if details is None:
            raise DocumentError(err or "Failed to parse document structure.")

        summary, authors, title = details
        scores = score(summary)

        return {
            "scores": scores,
            "summary": summary,
            "metadata": doc_metadata(doc),
            "filename": filename,
        }

    def validate(
        self,
        file_source: Union[str, bytes, io.BytesIO],
        filename: str = "document.docx",
        conference_id: Any = None,
    ) -> Dict[str, Any]:
        if isinstance(file_source, bytes):
            data = file_source
        elif isinstance(file_source, io.BytesIO):
            data = file_source.getvalue()
        elif isinstance(file_source, str):
            with open(file_source, "rb") as f:
                data = f.read()
        else:
            raise DocumentError("Invalid file source provided.")
        return self.check(data, filename=filename)
