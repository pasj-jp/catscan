from ..latex_engine import BibItem, Issue, Location, RuleBasedLatexChecker  # noqa: F401 (re-exported)


class PasjLatexChecker(RuleBasedLatexChecker):
    """
    PASJ Japanese LaTeX manuscript validator.
    Inspects .tex source code for PASJ conventions:
    - Document class (PASJ202x)
    - Bilingual titles (\\jtitle & \\title)
    - Bilingual authors (\\jauthor & \\author) and half-width comma delimiter
    - English abstract (\\Abstract)
    - Japanese punctuation rules (「、」「。」 vs 「，」「．」)
    - English figure & table captions & trailing period on figure captions
    - Bibliography formatting & DOI/URL conventions

    The rules themselves live in ``checkers/rules/pasj_latex.yaml``.
    """

    rules_name = "pasj_latex"
