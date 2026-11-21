from catscan.checkers.registry import get_checker
from catscan.checkers.latex.engine import RuleBasedLatexChecker


SAMPLE_VALID_TEX = r"""
\documentclass{jacow}
\begin{document}
\title{Sample Paper}
\author{A. Author}
\maketitle

Some text citing \cite{ref1} and \cite{ref2}.

\begin{thebibliography}{9}
\bibitem{ref1}
A. Author \emph{et al.}, \textquotedblleft{Paper Title,}\textquotedblright{} \textit{Phys. Rev.}, vol. 10, no. 2, pp. 100--105, 2020. \url{doi:10.18429/JACoW-IPAC2020-MOPGW001}

% \bibitem{commented_ref}
% This is commented out and should not be parsed: et al. doi: 10.1234/bad

\bibitem{ref2}
B. Author, \textquotedblleft{Second Paper,}\textquotedblright{} \textit{J. Appl. Phys.}, vol. 5, no. 1, 2021. \url{doi:10.1016/0168-583x(91)95671-y}
\end{thebibliography}
\end{document}
"""

SAMPLE_INVALID_TEX = r"""
\documentclass{jacow}
\begin{document}
\begin{thebibliography}{9}

\bibitem{bad_etal}
A. Author et al., "No italics on et al.", 2020.

\bibitem{bad_doi_space}
B. Author, "Space in DOI", \url{doi: 10.18429/JACoW-IPAC2020-001}

\bibitem{bad_doi_url}
C. Author, "DOI as web URL", \url{https://doi.org/10.18429/JACoW-IPAC2020-002}

\bibitem{bad_volume_issue}
D. Author, "Bad volume issue", Vol. 12, Issue 3, 2022.

\bibitem{bad_no_prefix}
E. Author, "No doi prefix", \url{10.18429/JACoW-IPAC2020-003}

\end{thebibliography}
\end{document}
"""


def test_latex_checker_valid():
    checker = RuleBasedLatexChecker("jacow_latex", check_online_dois=False)
    result = checker.check(SAMPLE_VALID_TEX.encode("utf-8"), filename="valid.tex")

    assert len(result["issues"]) == 0
    assert result["total_references"] == 2  # commented ref was ignored


def test_latex_checker_issues_detected():
    checker = RuleBasedLatexChecker("jacow_latex", check_online_dois=False)
    result = checker.check(SAMPLE_INVALID_TEX.encode("utf-8"), filename="invalid.tex")

    assert len(result["issues"]) >= 5
    body = "\n".join(f"{issue['name']} {issue['message']}" for issue in result["issues"])

    # Verify all expected issues were flagged
    assert "bad_etal" in body
    assert "et al. is not wrapped in a command to make it italic" in body

    assert "bad_doi_space" in body
    assert "DOI contains a space after the colon" in body

    assert "bad_doi_url" in body
    assert "DOI is written as a web URL" in body

    assert "bad_volume_issue" in body
    assert "JACoW references use vol. X and no. X" in body

    assert "bad_no_prefix" in body
    assert 'DOI does not contain "doi:" prefix' in body


def test_jacow_latex_checks_manuscript_structure():
    source = SAMPLE_VALID_TEX.replace("{jacow}", "{article}", 1).replace(
        r"\maketitle",
        r"""\maketitle
\begin{abstract}
See \cite{ref1}.
\end{abstract}
\begin{figure*}
% \caption{This is commented out.}
\end{figure*}""",
        1,
    )
    report = RuleBasedLatexChecker("jacow_latex").check(source.encode(), filename="paper.tex")

    assert {issue["type"] for issue in report["issues"]} == {
        "INCORRECT_DOCUMENT_CLASS", "ABSTRACT_CITATION", "MISSING_FIGURE_CAPTION",
    }
    assert all(issue["file"] == "paper.tex" and issue["line"] > 0 for issue in report["issues"])


def test_latex_factory_dispatch():
    checker = get_checker("jacow", "latex")
    assert isinstance(checker, RuleBasedLatexChecker)
    assert checker.rules_name == "jacow_latex"


def test_api_scan_latex_endpoint(client):
    # Valid LaTeX upload
    res = client.post(
        "/api/scan/file",
        files={"file": ("test.tex", SAMPLE_VALID_TEX.encode())}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["issues"]) == 0

    # Invalid LaTeX upload
    res_bad = client.post(
        "/api/scan/file",
        files={"file": ("invalid.tex", SAMPLE_INVALID_TEX.encode())}
    )
    assert res_bad.status_code == 200
    data_bad = res_bad.json()
    assert len(data_bad["issues"]) >= 5
