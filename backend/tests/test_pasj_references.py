import io
from copy import deepcopy

import pytest
from docx import Document

from catscan.checkers.pasj.word_checker import classify_paragraphs
from catscan.indico.comment import render_comment

from .conftest import load_example


@pytest.fixture
def manuscript():
    doc = Document(io.BytesIO(load_example("PASJ_Sample_Paper.docx")))
    return doc, classify_paragraphs(doc)


def scan(client, doc):
    data = io.BytesIO()
    doc.save(data)
    response = client.post(
        "/api/scan/file", files={"file": ("paper.docx", data.getvalue())}, data={"template": "pasj"}
    )
    assert response.status_code == 200
    return response.json()


def findings(report, code):
    return [row for row in report["summary"]["References"]["details"] if row.get("citation_issue") == code]


def paragraph_number(doc, paragraph):
    return next(i for i, item in enumerate(doc.paragraphs, 1) if item._p is paragraph._p)


def test_pasj_reference_checks_accept_official_sample_and_ranges(client, manuscript):
    doc, parts = manuscript
    ranged = next(p for p in parts.body_p if "[2-5]" in p.text)
    ranged.text = ranged.text.replace("[2-5]", "［２–５］", 1)
    report = scan(client, doc)
    assert report["summary"]["References"]["ok"] is True
    assert report["scores"]["References"][1:] == [0, 0]


def test_pasj_reference_checks_locate_body_citation_without_reference(client, manuscript):
    doc, parts = manuscript
    deleted = next(p for p in parts.ref_p if p.text.startswith("[7]"))
    deleted._p.getparent().remove(deleted._p)
    citation = next(p for p in parts.body_p if "[7]" in p.text)
    report = scan(client, doc)

    matching = next(row for row in findings(report, "missing_reference") if "[7]" in row["text"])
    assert matching["paragraph_number"] == paragraph_number(doc, citation)
    assert "キャピタライゼーション" in matching["text"]
    assert "[7] がありません" in matching["notes"]
    assert report["scores"]["References"][2] > 0
    comment = render_comment(report, "https://example.org/report")
    assert matching["location"] in comment and "[7] がありません" in comment


def test_pasj_reference_checks_locate_duplicate_entry(client, manuscript):
    doc, parts = manuscript
    original = next(p for p in parts.ref_p if p.text.startswith("[3]"))
    original._p.addnext(deepcopy(original._p))
    report = scan(client, doc)

    duplicate, = findings(report, "duplicate_reference")
    original_number = paragraph_number(doc, original)
    assert duplicate["paragraph_number"] == original_number + 1
    assert f"Paragraph {original_number}" in duplicate["notes"]
    assert duplicate["text"].startswith("[3]")
    assert report["summary"]["References"]["ok"] is False


def test_pasj_reference_checks_track_first_citation_order(client, manuscript):
    doc, parts = manuscript
    first_citation = next(p for p in parts.body_p if "[1]" in p.text)
    first_citation.text = first_citation.text.replace("[1]", "[2, 1]", 1)
    report = scan(client, doc)

    order, = findings(report, "citation_order")
    assert order["paragraph_number"] == paragraph_number(doc, first_citation)
    assert "[2, 1]" in order["text"]
    assert "[2] が [1] より先" in order["notes"]


def test_pasj_reference_checks_warn_about_uncited_entries(client, manuscript):
    doc, parts = manuscript
    citation = next(p for p in parts.body_p if "[13, 14]" in p.text)
    citation.text = citation.text.replace("[13, 14]", "[13]", 1)
    report = scan(client, doc)

    unused, = findings(report, "uncited_reference")
    assert unused["text"].startswith("[14]")
    assert unused["citation_ok"] == 2
    assert report["scores"]["References"][1:] == [1, 0]


def test_pasj_reference_checks_warn_if_bibliography_number_not_readable(client, manuscript):
    doc, parts = manuscript
    entry = next(p for p in parts.ref_p if p.text.startswith("[14]"))
    entry.text = entry.text.removeprefix("[14]\t")
    report = scan(client, doc)

    unknown, = findings(report, "unknown_reference_number")
    assert unknown["paragraph_number"] == paragraph_number(doc, entry)
    assert unknown["citation_ok"] == 2
    assert not findings(report, "missing_reference")
    assert report["scores"]["References"][1:] == [1, 0]
