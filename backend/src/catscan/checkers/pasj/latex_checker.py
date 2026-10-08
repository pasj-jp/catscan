import io
from typing import Any, Dict, Optional, Union

from ..base import BasePaperChecker


class PasjLatexChecker(BasePaperChecker):
    """Placeholder for the future PASJ LaTeX checker."""

    def validate(
        self,
        file_source: Union[str, bytes, io.BytesIO],
        filename: str = "document.tex",
        conference_id: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        return {
            "error": "PASJ LaTeX validation has not been implemented yet.",
            "code": "checker_not_implemented",
            "template_type": "pasj",
            "filename": filename,
        }
