import pytest
from starlette.testclient import TestClient
from catscan.main import app
from catscan.checkers.factory import get_checker
from catscan.checkers.jacow.latex_checker import JacowLatexChecker


SAMPLE_VALID_TEX = r"""
\documentclass{article}
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
\documentclass{article}
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
    checker = JacowLatexChecker(check_online_dois=False)
    result = checker.validate(SAMPLE_VALID_TEX, filename="valid.tex")

    assert result["statusCode"] == 200
    assert result["issuesFound"] == 0
    assert result["body"] == "No issues found"
    assert result["total_references"] == 2  # commented ref was ignored


def test_latex_checker_issues_detected():
    checker = JacowLatexChecker(check_online_dois=False)
    result = checker.validate(SAMPLE_INVALID_TEX, filename="invalid.tex")

    assert result["statusCode"] == 200
    assert result["issuesFound"] >= 5
    body = result["body"]

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


def test_latex_factory_dispatch():
    checker, template = get_checker(doc_type="latex")
    assert isinstance(checker, JacowLatexChecker)
    assert template == "jacow"


def test_api_scan_latex_endpoint():
    client = TestClient(app)

    # Valid LaTeX upload
    res = client.post(
        "/api/scan/latex",
        json={"filename": "test.tex", "content": SAMPLE_VALID_TEX}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["issuesFound"] == 0
    assert data["body"] == "No issues found"

    # Invalid LaTeX upload
    res_bad = client.post(
        "/api/scan/latex",
        json={"filename": "invalid.tex", "content": SAMPLE_INVALID_TEX}
    )
    assert res_bad.status_code == 200
    data_bad = res_bad.json()
    assert data_bad["issuesFound"] >= 5
