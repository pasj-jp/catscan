import pytest
from catscan.checkers.latex_engine import RuleBasedLatexChecker
from catscan.checkers.jacow.word_checker import JacowWordChecker
from catscan.checkers.pasj.word_checker import PasjWordChecker
from .conftest import load_example


@pytest.mark.parametrize(
    ("rules_name", "filename", "expected_issues", "expected_refs"),
    [
        ("jacow_latex", "latex_jacow_perfect.tex", 0, 2),
        ("pasj_latex", "latex_pasj_perfect.tex", 0, 2),
    ],
)
def test_latex_perfect_samples(rules_name, filename, expected_issues, expected_refs):
    checker = RuleBasedLatexChecker(rules_name)
    data = load_example(filename)
    result = checker.check(data, filename=filename)
    assert result["statusCode"] == 200
    assert result["issuesFound"] == expected_issues
    assert result["total_references"] == expected_refs


@pytest.mark.parametrize(
    ("rules_name", "filename", "expected_issues", "expected_keywords"),
    [
        (
            "jacow_latex",
            "latex_jacow_issues.tex",
            5,
            ["bad_etal", "bad_doi_space", "bad_doi_url", "bad_vol_issue", "bad_no_prefix"],
        ),
        (
            "pasj_latex",
            "latex_pasj_issues.tex",
            14,
            [
                "documentclass",
                "Japanese title",
                "Author names should be separated",
                "English author block",
                "Abstract must be written entirely in English",
                "full-width comma",
                "Figure and Table captions must be written in English",
                "Figure caption does not end with a period",
            ],
        ),
    ],
)
def test_latex_issue_samples(rules_name, filename, expected_issues, expected_keywords):
    checker = RuleBasedLatexChecker(rules_name)
    data = load_example(filename)
    result = checker.check(data, filename=filename)
    assert result["statusCode"] == 200
    assert result["issuesFound"] == expected_issues
    body = result["body"]
    for kw in expected_keywords:
        assert kw in body


@pytest.mark.parametrize(
    ("checker_cls", "filename", "expected_zero_categories"),
    [
        (PasjWordChecker, "PASJ_Sample_Paper.docx", ["Title", "Authors", "Abstract", "Paragraphs", "total"]),
        (JacowWordChecker, "JACoW_MSWord_Style_Guide.docx", ["Title"]),
    ],
)
def test_word_perfect_samples(checker_cls, filename, expected_zero_categories):
    checker = checker_cls()
    data = load_example(filename)
    result = checker.check(data, filename=filename)
    scores = result["scores"]
    for cat in expected_zero_categories:
        assert scores[cat][2] == 0


@pytest.mark.parametrize(
    ("checker_cls", "filename", "validator"),
    [
        (
            PasjWordChecker,
            "word_pasj_issues.docx",
            lambda s: s["Title"][2] > 0 and s["Authors"][2] > 0 and s["Abstract"][2] > 0 and s["Paragraphs"][2] > 0 and s["total"][2] >= 4,
        ),
        (
            JacowWordChecker,
            "word_jacow_issues.docx",
            lambda s: s["Title"][2] == 1,
        ),
    ],
)
def test_word_issue_samples(checker_cls, filename, validator):
    checker = checker_cls()
    data = load_example(filename)
    result = checker.check(data, filename=filename)
    assert validator(result["scores"])
