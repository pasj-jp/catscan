import logging
from typing import Any, Dict, List, Optional, Tuple

from ..errors import DocumentError
from ..services.scanning import scan_document
from ..settings import get_settings
from .client import IndicoClient, IndicoAPIError
from .comment import render_comment

logger = logging.getLogger("catscan.indico.service")


def _pick_source_file(files: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
    """Find the editable Word, LaTeX, or source archive file in the revision."""
    for f in files:
        fname = f.get("filename", "").lower()
        if fname.endswith(".docx"):
            return f, "word"
    for f in files:
        fname = f.get("filename", "").lower()
        if fname.endswith(".tex"):
            return f, "latex"
    for f in files:
        fname = f.get("filename", "").lower()
        if fname.endswith((".zip", ".tar.gz", ".tgz")):
            return f, "archive"
    raise DocumentError(
        "No editable Word (.docx), LaTeX (.tex), or source archive (.zip/.tar.gz) found in revision."
    )


class IndicoScanService:
    """
    Coordinates fetching papers from Indico, running Word/LaTeX validation,
    storing reports, and posting feedback comments to the Indico revision timeline.
    """

    def __init__(self, client: Optional[IndicoClient] = None):
        self._owns_client = client is None
        self.client = client or IndicoClient()

    def close(self) -> None:
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()

    def __enter__(self) -> "IndicoScanService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def list_papers(self, event_id: int) -> List[Dict[str, Any]]:
        """List all paper contributions for an event."""
        return self.client.get_papers(event_id)

    def scan_contribution_paper(
        self,
        event_id: int,
        contribution_id: int,
        post_comment: bool = True,
        template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate the latest revision of a paper submission and optionally post results back.
        """
        paper_data = self.client.get_contribution_paper(event_id, contribution_id)
        revisions = paper_data.get("revisions", [])
        if not revisions:
            raise DocumentError(f"No revisions found for event {event_id}, contribution {contribution_id}.")

        latest_rev = revisions[-1]
        rev_id = latest_rev["id"]
        files = latest_rev.get("files", [])

        target_file, _ = _pick_source_file(files)
        filename = target_file["filename"]
        download_url = target_file.get("download_url") or target_file.get("external_download_url")
        if not download_url:
            raise DocumentError(f"File {filename} has no download URL in revision {rev_id}.")

        file_bytes = self.client.download_file(download_url)

        extra = {
            "event_id": event_id,
            "contribution_id": contribution_id,
            "revision_id": rev_id,
        }
        result = scan_document(
            data=file_bytes,
            filename=filename,
            template=template or "auto",
            extra=extra,
        )
        doc_type = result["report_type"]

        settings = get_settings()
        report_url = f"{settings.catscan_base_url}/?results={result['report_id']}"

        comment_text = render_comment(result, report_url)
        comment_posted = False

        if post_comment:
            try:
                self.client.create_comment(
                    event_id=event_id,
                    contribution_id=contribution_id,
                    revision_id=rev_id,
                    text=comment_text,
                    internal=False,
                )
                comment_posted = True
            except Exception as e:
                logger.error(f"Failed to post comment to Indico: {e}")

        return {
            "event_id": event_id,
            "contribution_id": contribution_id,
            "revision_id": rev_id,
            "filename": filename,
            "doc_type": doc_type,
            "template": result["detected_template"],
            "report_id": result["report_id"],
            "report_url": report_url,
            "comment_posted": comment_posted,
            "comment_text": comment_text,
            "result": result,
        }

    def scan_event(self, event_id: int, post_comment: bool = True) -> Dict[str, Any]:
        """Batch scan all submitted papers in an Indico conference event."""
        papers = self.list_papers(event_id)
        results = []
        errors = []

        for p in papers:
            contrib_id = p.get("id")
            code = p.get("code") or f"Contrib-{contrib_id}"
            editable = p.get("editable")
            if not editable or editable.get("revision_count", 0) == 0:
                continue

            try:
                res = self.scan_contribution_paper(
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
                logger.error(f"Failed scanning paper {contrib_id} in event {event_id}: {e}")
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
