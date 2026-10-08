import io
from typing import Dict, Any, Optional, Union
from docx import Document

from ..base import BasePaperChecker
from .doc import create_upload_variables
from .page import check_tracking_on
from .score import score
from .refdb import get_references, create_spms_variables


class JacowWordChecker(BasePaperChecker):
    """
    Standard JACoW Word document format checker.
    Checks styles, margins, typography, headings, tables, figures, citations.
    """

    def validate(
        self,
        file_source: Union[str, bytes, io.BytesIO],
        filename: str = "document.docx",
        conference_id: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        if isinstance(file_source, bytes):
            file_obj = io.BytesIO(file_source)
        elif isinstance(file_source, str):
            with open(file_source, "rb") as f:
                file_obj = io.BytesIO(f.read())
        elif isinstance(file_source, io.BytesIO):
            file_obj = file_source
        else:
            return {"error": "Invalid file source provided."}

        try:
            doc = Document(docx=file_obj)
        except KeyError:
            return {
                "error": "Document may not be in a supported format.\nTry re-saving the file as a 'Word Document' (.docx) and try again."
            }
        except Exception as e:
            return {"error": f"Failed to open document: {str(e)}"}

        try:
            if check_tracking_on(doc):
                return {
                    "error": "Cannot process file: Track Changes (revision tracking) is turned on.\nPlease accept/reject all changes and turn tracking off before submitting."
                }
        except Exception:
            pass

        details, err = create_upload_variables(doc)
        if details is None:
            return {"error": err or "Failed to parse document structure."}

        summary, authors, title = details

        if conference_id:
            try:
                paper_code = filename.rsplit(".", 1)[0].upper()
                refs = get_references(paper_code, str(conference_id))
                ref_summary, _ = create_spms_variables(paper_code, authors, title, refs)
                if ref_summary:
                    summary.update(ref_summary)
            except Exception:
                pass

        scores = score(summary)

        meta = {}
        metadata = doc.core_properties
        if metadata:
            meta = {
                "author": metadata.author,
                "revision": metadata.revision,
                "version": metadata.version,
                "language": metadata.language,
            }
            if metadata.created:
                meta["created"] = metadata.created.strftime("%d/%m/%Y %H:%M")
            if metadata.modified:
                meta["modified"] = metadata.modified.strftime("%d/%m/%Y %H:%M")

        return {
            "scores": scores,
            "summary": summary,
            "metadata": meta,
            "filename": filename,
        }
