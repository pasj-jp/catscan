import pytest

from .conftest import EXAMPLE_DIR, load_example
from catscan.checkers.registry import get_checker, detect_template, detect_latex_template
from catscan.checkers.pasj.word_checker import PasjWordChecker
from catscan.checkers.latex_engine import RuleBasedLatexChecker

SAMPLE_PASJ_DOCX = EXAMPLE_DIR / "PASJ_Sample_Paper.docx"
SAMPLE_PASJ_TEX = EXAMPLE_DIR / "PASJ_Sample_Paper.tex"

INVALID_PASJ_TEX = r"""
\documentclass{article}
\begin{document}
\title{Only English Title}
\author{A. Author}
\Abstract{This abstract has 日本語 in it.}
\maketitle
これは本文ですが，公用文ルールでは読点に注意が必要です．
\begin{figure}
\caption{日本語のキャプション}
\end{figure}
\begin{thebibliography}{9}
\bibitem{ref1}
A. Author, et al., "Title", 2020. \url{doi:10.1234/bad.}
\end{thebibliography}
\end{document}
"""


def test_pasj_latex_checker_sample():
    checker = RuleBasedLatexChecker("pasj_latex")
    content = SAMPLE_PASJ_TEX.read_bytes()
    res = checker.check(content, filename="PASJ_Sample_Paper.tex")

    assert res["statusCode"] == 200
    assert res["total_references"] >= 20
    assert res["report_type"] == "latex"


def test_pasj_latex_checker_invalid():
    checker = RuleBasedLatexChecker("pasj_latex")
    res = checker.check(INVALID_PASJ_TEX.encode("utf-8"), filename="bad.tex")

    assert res["statusCode"] == 200
    assert res["issuesFound"] >= 6
    body = res["body"]

    assert "documentclass" in body
    assert "Japanese title" in body
    assert "Japanese author" in body
    assert "Abstract must be written entirely in English" in body
    assert "Punctuation rule" in body
    assert "Figure and Table captions must be written in English" in body


def test_pasj_word_checker_sample():
    checker = PasjWordChecker()
    res = checker.check(SAMPLE_PASJ_DOCX.read_bytes(), filename="PASJ_Sample_Paper.docx")

    assert "scores" in res
    assert "summary" in res
    assert res["filename"] == "PASJ_Sample_Paper.docx"

    scores = res["scores"]
    assert "Title" in scores
    assert "Authors" in scores
    assert "Abstract" in scores
    assert "Headings" in scores
    assert "Paragraphs" in scores
    assert "Figures" in scores
    assert "Tables" in scores
    assert "References" in scores
    assert "Margins" in scores
    assert "Styles" in scores
    assert "total" in scores
    assert scores["total"][0] > 0


def test_pasj_factory_dispatch():
    # Word dispatch
    wc = get_checker("pasj", "word")
    assert isinstance(wc, PasjWordChecker)

    # LaTeX dispatch
    lc = get_checker("pasj", "latex")
    assert isinstance(lc, RuleBasedLatexChecker)
    assert lc.rules_name == "pasj_latex"

    # Auto-detection for Word
    doc_bytes = SAMPLE_PASJ_DOCX.read_bytes()
    assert detect_template(doc_bytes) == "pasj"

    # Auto-detection for LaTeX
    tex_bytes = SAMPLE_PASJ_TEX.read_bytes()
    assert detect_latex_template(tex_bytes) == "pasj"


def test_api_scan_latex_pasj(client):
    res = client.post(
        "/api/scan/latex",
        json={"filename": "test_pasj.tex", "content": INVALID_PASJ_TEX, "template": "pasj"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_template"] == "pasj"
    assert data["template_name"] == "PASJ 和文原稿"
    assert data["issuesFound"] >= 6
    assert "report_id" in data


def test_api_scan_word_pasj(client):
    with open(SAMPLE_PASJ_DOCX, "rb") as f:
        res = client.post(
            "/api/scan/word",
            files={"file": ("PASJ_Sample_Paper.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"template": "pasj"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_template"] == "pasj"
    assert data["template_name"] == "PASJ 和文原稿"
    assert "scores" in data
    assert "report_id" in data
