import os
from typing import Optional

from ..latex_engine import BibItem, Issue, Location, RuleBasedLatexChecker  # noqa: F401 (re-exported)


class JacowLatexChecker(RuleBasedLatexChecker):
    """
    JACoW LaTeX paper format and reference validator.
    Inspects .tex source code for JACoW bibliography conventions, DOI formatting,
    and italicization rules without requiring an external TeX compiler.

    The rules themselves live in ``checkers/rules/jacow_latex.yaml``.
    """

    rules_name = "jacow_latex"

    def __init__(self, check_online_dois: Optional[bool] = None):
        if check_online_dois is None:
            check_online_dois = os.environ.get("CATSCAN_CHECK_DOI", "false").lower() in ("true", "1")
        super().__init__(check_online_dois=check_online_dois)
