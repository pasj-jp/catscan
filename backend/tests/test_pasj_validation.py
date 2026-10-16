import os
import pytest
from starlette.testclient import TestClient

from catscan.main import app
from catscan.checkers.factory import get_checker, detect_template, detect_latex_template
from catscan.checkers.pasj.word_checker import PasjWordChecker
from catscan.checkers.pasj.latex_checker import PasjLatexChecker

SAMPLE_PASJ_DOCX = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../example/PASJ_Sample_Paper.docx"))
SAMPLE_PASJ_TEX = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../example/PASJ_Sample_Paper.tex"))

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
    checker = PasjLatexChecker()
    with open(SAMPLE_PASJ_TEX, "r", encoding="utf-8") as f:
        content = f.read()
    res = checker.validate(content, filename="PASJ_Sample_Paper.tex")

    assert res["statusCode"] == 200
    assert res["detected_template"] == "pasj"
    assert res["template_name"] == "PASJ 和文原稿"
    assert res["total_references"] >= 20
    assert res["report_type"] == "latex"


def test_pasj_latex_checker_invalid():
    checker = PasjLatexChecker()
    res = checker.validate(INVALID_PASJ_TEX, filename="bad.tex")

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
    with open(SAMPLE_PASJ_DOCX, "rb") as f:
        res = checker.validate(f.read(), filename="PASJ_Sample_Paper.docx")

    assert "scores" in res
    assert "summary" in res
    assert res["detected_template"] == "pasj"
    assert res["template_name"] == "PASJ 和文原稿"

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
    wc, w_template = get_checker(doc_type="word", template="pasj")
    assert isinstance(wc, PasjWordChecker)
    assert w_template == "pasj"

    # LaTeX dispatch
    lc, l_template = get_checker(doc_type="latex", template="pasj")
    assert isinstance(lc, PasjLatexChecker)
    assert l_template == "pasj"

    # Auto-detection for Word
    with open(SAMPLE_PASJ_DOCX, "rb") as f:
        doc_bytes = f.read()
    assert detect_template(doc_bytes) == "pasj"

    # Auto-detection for LaTeX
    with open(SAMPLE_PASJ_TEX, "r", encoding="utf-8") as f:
        tex_str = f.read()
    assert detect_latex_template(tex_str) == "pasj"


def test_api_scan_latex_pasj():
    client = TestClient(app)
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


def test_api_scan_word_pasj():
    client = TestClient(app)
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
