from docx.document import Document

from ..common.docx_utils import doc_metadata, open_docx
from ..common.score import score
from .doc import build_summary


class JacowWordChecker:
    def check(self, data: bytes, filename: str = "document.docx") -> dict:
        return self.check_document(open_docx(data), filename)

    def check_document(self, doc: Document, filename: str) -> dict:
        summary = build_summary(doc)
        return {
            "scores": score(summary),
            "summary": summary,
            "metadata": doc_metadata(doc),
            "filename": filename,
        }
