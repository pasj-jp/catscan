import os
import pytest
from catscan.checkers.jacow.latex_checker import JacowLatexChecker
from catscan.checkers.jacow.word_checker import JacowWordChecker
from catscan.checkers.pasj.latex_checker import PasjLatexChecker
from catscan.checkers.pasj.word_checker import PasjWordChecker


EXAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "example"))


def test_latex_jacow_perfect():
    checker = JacowLatexChecker()
    filepath = os.path.join(EXAMPLE_DIR, "latex_jacow_perfect.tex")
    result = checker.validate(filepath)
    assert result["statusCode"] == 200
    assert result["issuesFound"] == 0
    assert result["total_references"] == 2


def test_latex_jacow_issues():
    checker = JacowLatexChecker()
    filepath = os.path.join(EXAMPLE_DIR, "latex_jacow_issues.tex")
    result = checker.validate(filepath)
    assert result["statusCode"] == 200
    assert result["issuesFound"] == 5
    body = result["body"]
    assert "bad_etal" in body
    assert "bad_doi_space" in body
    assert "bad_doi_url" in body
    assert "bad_vol_issue" in body
    assert "bad_no_prefix" in body


def test_latex_pasj_perfect():
    checker = PasjLatexChecker()
    filepath = os.path.join(EXAMPLE_DIR, "latex_pasj_perfect.tex")
    result = checker.validate(filepath)
    assert result["statusCode"] == 200
    assert result["issuesFound"] == 0
    assert result["total_references"] == 2


def test_latex_pasj_issues():
    checker = PasjLatexChecker()
    filepath = os.path.join(EXAMPLE_DIR, "latex_pasj_issues.tex")
    result = checker.validate(filepath)
    assert result["statusCode"] == 200
    assert result["issuesFound"] == 14
    body = result["body"]
    assert "INCORRECT_DOCUMENT_CLASS" in body or "documentclass" in body
    assert "MISSING_JAPANESE_TITLE" in body or "Japanese title" in body
    assert "AUTHORS_DELIMITER_FULLWIDTH" in body or "Author names should be separated by a half-width comma" in body
    assert "MISSING_ENGLISH_AUTHORS" in body or "English author block" in body
    assert "ABSTRACT_CONTAINS_JAPANESE" in body or "Abstract must be written entirely in English" in body
    assert "PUNCTUATION_FULLWIDTH_COMMA" in body or "full-width comma" in body
    assert "FIGURE_CAPTION_CONTAINS_JAPANESE" in body or "Figure and Table captions must be written in English" in body
    assert "FIGURE_CAPTION_MISSING_PERIOD" in body or "Figure caption does not end with a period" in body


def test_word_pasj_perfect():
    checker = PasjWordChecker()
    filepath = os.path.join(EXAMPLE_DIR, "PASJ_Sample_Paper.docx")
    result = checker.validate(filepath)
    scores = result["scores"]
    assert scores["Title"][2] == 0
    assert scores["Authors"][2] == 0
    assert scores["Abstract"][2] == 0
    assert scores["Paragraphs"][2] == 0
    assert scores["total"][2] == 0


def test_word_pasj_issues():
    checker = PasjWordChecker()
    filepath = os.path.join(EXAMPLE_DIR, "word_pasj_issues.docx")
    result = checker.validate(filepath)
    scores = result["scores"]
    # Verify the 4 intentional issue categories triggered failures
    assert scores["Title"][2] > 0
    assert scores["Authors"][2] > 0
    assert scores["Abstract"][2] > 0
    assert scores["Paragraphs"][2] > 0
    assert scores["total"][2] >= 4


def test_word_jacow_perfect():
    checker = JacowWordChecker()
    filepath = os.path.join(EXAMPLE_DIR, "JACoW_MSWord_Style_Guide.docx")
    result = checker.validate(filepath)
    scores = result["scores"]
    assert scores["Title"][2] == 0


def test_word_jacow_issues():
    checker = JacowWordChecker()
    filepath = os.path.join(EXAMPLE_DIR, "word_jacow_issues.docx")
    result = checker.validate(filepath)
    scores = result["scores"]
    assert scores["Title"][2] == 1
