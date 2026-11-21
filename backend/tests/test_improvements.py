import io
import tarfile
import zipfile
from unittest.mock import MagicMock

import pytest
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

from catscan.checkers.common.layout import check_sections
from catscan.checkers.latex.engine import RuleBasedLatexChecker
from catscan.checkers.pasj.word_checker import PasjWordChecker, classify_paragraphs
from catscan.checkers.registry import detect_template
from catscan.indico.comment import render_comment
from catscan.indico.client import IndicoClient
from catscan.indico.service import IndicoScanService
from catscan.services import reports
from .conftest import EXAMPLE_DIR, load_example


def _make_zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_tar_gz_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in entries.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _document_bytes(doc) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.parametrize("change", ["height", "columns"])
def test_pasj_word_reports_wrong_a4_height_and_body_columns(change):
    doc = Document(io.BytesIO(load_example("PASJ_Sample_Paper.docx")))
    if change == "height":
        doc.sections[0].page_height = Mm(250)
    else:
        for section in doc.sections:
            section._sectPr.find(qn("w:cols")).set(qn("w:num"), "1")
    margins = PasjWordChecker().check(_document_bytes(doc))["summary"]["Margins"]
    assert not margins["ok"]
    if change == "height":
        assert "250" in margins["details"][0]["page_size"]
        assert "297" in margins["details"][0]["notes"]
    else:
        assert margins["details"][0]["col_ok"], "The title section can be single-column."
        assert not margins["details"][1]["col_ok"]
        assert margins["details"][1]["expected_columns"] == 2


def test_pasj_word_mixed_size_title_and_body_report_the_offending_runs():
    doc = Document(io.BytesIO(load_example("PASJ_Sample_Paper.docx")))
    parts = classify_paragraphs(doc)
    title = parts.etitle_p
    title.runs[0].font.size = Pt(24)
    title.runs[-1].font.size = Pt(12)
    paragraph = next(p for p in parts.body_p if p.style.name == "00) pasj-本文")
    paragraph.add_run(" Oversized body text").font.size = Pt(18)

    report = PasjWordChecker().check(_document_bytes(doc))["summary"]
    title_result = report["Title"]["details"][1]
    assert title_result["style_ok"] is False
    assert f"「{title.runs[0].text.strip()}」 24 pt → 12 pt" in title_result["notes"]
    assert any("「Oversized body text」 18 pt → 10 pt" in detail["status"]
               for detail in report["Paragraphs"]["details"])


def test_template_detection_uses_applied_word_styles_and_active_tex_class(client):
    english_doc = Document()
    english_doc.styles.add_style("00) pasj-本文", WD_STYLE_TYPE.PARAGRAPH)
    english_doc.add_paragraph("An English paragraph.")
    assert detect_template(_document_bytes(english_doc)) == "jacow"

    doc = Document(io.BytesIO(load_example("PASJ_Sample_Paper.docx")))
    jacow_style = doc.styles.add_style("JACoW_Paper Title", WD_STYLE_TYPE.PARAGRAPH)
    assert detect_template(_document_bytes(doc)) == "pasj"
    doc.add_paragraph("Conflicting title", jacow_style)
    result = client.post("/api/scan/file", files={"file": ("paper.docx", _document_bytes(doc))})
    assert result.status_code == 400
    assert "Select the intended template" in result.json()["error"]

    tex = b"%\\documentclass{PASJ2026}\n\\documentclass{jacow}\n" + "日本語の注釈".encode()
    assert detect_template(tex, "latex") == "jacow"


@pytest.mark.parametrize(
    "filename",
    ["JACoW_MSWord_Style_Guide.docx", "paper.tex"],
)
def test_scan_requests_confirmation_for_explicit_template_mismatch(client, filename):
    files = {"file": (filename, load_example(filename))}
    response = client.post("/api/scan/file", files=files, data={"template": "pasj", "verify_template": "true"})
    assert response.status_code == 409
    assert response.json()["code"] == "template_mismatch"
    assert response.json()["selected_template"] == "pasj"
    assert response.json()["detected_template"] == "jacow"

    for choice in ("pasj", "jacow"):
        confirmed = client.post("/api/scan/file", files=files, data={"template": choice, "verify_template": "false"})
        assert confirmed.status_code == 200
        assert confirmed.json()["detected_template"] == choice
        assert confirmed.json()["report_id"]


def test_scan_does_not_treat_english_text_as_a_confirmed_jacow_template(client):
    doc = Document()
    doc.add_paragraph("An English paragraph with no template style.")
    result = client.post(
        "/api/scan/file",
        files={"file": ("draft.docx", _document_bytes(doc))},
        data={"template": "pasj", "verify_template": "true"},
    )
    assert result.status_code == 200
    assert result.json()["detected_template"] == "pasj"


def test_latex_archive_resolves_nested_inputs_and_preserves_source_locations(client):
    tex = load_example("latex_pasj_perfect.tex").replace(
        b"\\maketitle", b"\\maketitle\n% \\input{ignored}\n\\input{sections/start}",
    )
    archive = _make_zip_bytes({
        "paper/main.tex": tex,
        "paper/sections/start.tex": b"\\include{more}\n",
        "paper/sections/more.tex": "日本語です。\nここに，誤った句読点です．\n".encode(),
    })
    result = client.post("/api/scan/file", files={"file": ("paper.zip", archive)})
    assert result.status_code == 200
    report = result.json()
    assert not report["coverage_notices"]
    assert {(issue["type"], issue["file"], issue["line"]) for issue in report["issues"]} == {
        ("BODY_PUNCTUATION_COMMA", "paper/sections/more.tex", 2),
        ("BODY_PUNCTUATION_PERIOD", "paper/sections/more.tex", 2),
    }


@pytest.mark.parametrize("structured", [False, True])
def test_saved_legacy_latex_reports_use_structured_issues(client, isolated_reports_dir, structured):
    message = "要旨は英語で記述してください。 / Write the abstract in English."
    stored = {
        "report_type": "latex",
        "filename": "legacy.tex",
        "template_name": "PASJ 和文原稿",
        "issuesFound": 1,
        "body": f"Issue found in abstract: {message}",
        "isabbreviated": False,
    }
    if structured:
        stored["issues"] = [{"name": "abstract", "message": message, "file": "legacy.tex", "line": 6}]
    report_id = reports.save(stored)
    file_path = isolated_reports_dir / f"{report_id}.json"
    original = file_path.read_bytes()

    response = client.get(f"/api/reports/{report_id}.json")

    assert response.status_code == 200
    report = response.json()
    assert report["report_id"] == report_id
    assert report["detected_template"] == "pasj"
    issue, = report["issues"]
    assert issue["name"] == "abstract"
    assert issue["message"] == "Write the abstract in English."
    assert issue["message_ja"] == "要旨は英語で記述してください。"
    if structured:
        assert (issue["file"], issue["line"]) == ("legacy.tex", 6)
    assert "body" not in report
    assert file_path.read_bytes() == original


def test_latex_checks_cross_references_through_expanded_source(client):
    archive = _make_zip_bytes({
        "main.tex": (
            b"\\documentclass{jacow}\n"
            b"\\begin{document}\n\\input{section}\n"
            b"\\label{defined}\n\\end{document}"
        ),
        "section.tex": b"% \\ref{ignored}\n\\ref{defined}\n\\ref{absent}\n",
    })
    response = client.post("/api/scan/file", files={"file": ("paper.zip", archive)})

    assert response.status_code == 200
    issue, = response.json()["issues"]
    assert (issue["type"], issue["file"], issue["line"]) == ("UNDEFINED_REFERENCE", "section.tex", 3)
    assert issue["name"] == "absent"


def test_latex_coverage_reports_missing_files_and_never_prints_passed():
    source = b"\\documentclass{jacow}\n\\begin{document}\n\\input{section}\n\\bibliography{refs}\n\\end{document}"
    report = RuleBasedLatexChecker("jacow_latex").check(source, "main.tex")
    assert len(report["issues"]) == 0
    assert {(notice["file"], notice["line"]) for notice in report["coverage_notices"]} >= {
        ("main.tex", 3), ("main.tex", 4),
    }
    comment = render_comment(report, "https://example.org/report")
    assert "CHECKS INCOMPLETE" in comment
    assert "PASSED" not in comment


def test_latex_archive_reads_bib_keys_but_marks_formatted_output_unchecked(client):
    archive = _make_tar_gz_bytes({
        "paper/main.tex": b"\\documentclass{jacow}\n\\addbibresource{refs.bib}\n"
                          b"\\begin{document}\n\\cite{known,unknown}\n"
                          b"\\printbibliography\n\\end{document}",
        "paper/refs.bib": b"@article{known, title={Example}}\n",
    })
    result = client.post("/api/scan/file", files={"file": ("paper.tgz", archive)})
    assert result.status_code == 200
    report = result.json()
    assert len(report["issues"]) == 0
    assert len(report["coverage_notices"]) == 2
    assert "formatted output" in report["coverage_notices"][0]["message"]
    assert report["coverage_notices"][1]["message"].endswith(": unknown")
    assert report["coverage_notices"][1]["line"] == 4


def test_jacow_template_checks_the_selected_bibliography_branch():
    tex = load_example("paper.tex")
    checker = RuleBasedLatexChecker("jacow_latex")
    manual = checker.check(tex)
    assert manual["total_references"] > 0
    assert not manual["coverage_notices"]

    biblatex = checker.check(tex.replace(b"%biblatex,", b"biblatex,"))
    assert biblatex["total_references"] == 0
    assert any("formatted output" in notice["message"] for notice in biblatex["coverage_notices"])


def test_pasj_word_catches_font_override_and_multi_paragraph_abstract():
    doc = Document(io.BytesIO(load_example("PASJ_Sample_Paper.docx")))
    # Override Japanese title font size to 24pt (should now fail font check)
    for p in doc.paragraphs:
        if "和文タイトル" in (p.style.name if p.style else ""):
            for r in p.runs:
                r.font.size = Pt(24)
            break

    # Insert an extra paragraph right after Abstract body before section 1
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip().startswith("This template has been prepared"):
            next_p = doc.paragraphs[i + 1]
            next_p.insert_paragraph_before("Second paragraph of abstract violating single-paragraph rule.")
            break

    buf = io.BytesIO()
    doc.save(buf)

    res = PasjWordChecker().check(buf.getvalue(), filename="modified.docx")
    assert res["summary"]["Title"]["ok"] is False
    assert res["summary"]["Title"]["details"][0]["style_ok"] is False
    assert res["summary"]["Abstract"]["ok"] is False
    assert any("一段落のみ" in d["notes"] for d in res["summary"]["Abstract"]["details"])


def test_pasj_margins_reject_letter_and_accept_5mm_gutter():
    doc = Document(io.BytesIO(load_example("PASJ_Sample_Paper.docx")))
    # PASJ sample should pass A4 check
    assert all(s["margins_ok"] for s in check_sections(doc, require_a4=True))

    # Set page size to US Letter -> PASJ require_a4=True must reject
    doc.sections[0].page_width = Mm(215.9)
    doc.sections[0].page_height = Mm(279.4)
    assert check_sections(doc, require_a4=True)[0]["margins_ok"] is False

    # 5.0 mm = 0.50 cm (283 twips) gutter must pass
    doc2 = Document(io.BytesIO(load_example("PASJ_Sample_Paper.docx")))
    for c1 in doc2.sections[1]._sectPr.iterchildren():
        if "cols" in str(c1):
            c1.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space", "283")
    assert check_sections(doc2, require_a4=True)[1]["col_ok"] is True


def test_latex_decodes_cp932_and_euc_jp():
    tex = (
        "\\documentclass{PASJ2026}\n"
        "\\begin{document}\n"
        "\\jtitle{加速器テスト}\n"
        "\\title{ACCELERATOR TEST}\n"
        "\\jauthor{加速太郎, 粒子花子}\n"
        "\\author{Taro Kasoku, Hanako Ryushi}\n"
        "\\Abstract{English only abstract.}\n"
        "\\maketitle\n"
        "\\section{はじめに}\n"
        "これは日本語のテストです，全角カンマを含みます。\n"
        "\\end{document}\n"
    )
    for enc in ("cp932", "euc_jp"):
        res = RuleBasedLatexChecker("pasj_latex").check(tex.encode(enc), filename="jp.tex")
        issue_types = {i["type"] for i in res["issues"]}
        assert "BODY_PUNCTUATION_COMMA" in issue_types
        assert "MISSING_JAPANESE_TITLE" not in issue_types


def test_api_scan_file_supports_zip_and_tar_gz(client):
    tex_bytes = load_example("latex_pasj_perfect.tex")
    zip_bytes = _make_zip_bytes({
        "__MACOSX/._main.tex": b"junk",
        "paper/helper.tex": b"% helper macros\n",
        "paper/main.tex": tex_bytes,
    })

    res_zip = client.post(
        "/api/scan/file",
        files={"file": ("submission.zip", io.BytesIO(zip_bytes), "application/zip")},
        data={"template": "auto"},
    )
    assert res_zip.status_code == 200
    data_zip = res_zip.json()
    assert data_zip["report_type"] == "latex"
    assert data_zip["detected_template"] == "pasj"
    assert data_zip["filename"] == "main.tex"
    assert data_zip["archive_filename"] == "submission.zip"
    assert len(data_zip["issues"]) == 0

    tgz_bytes = _make_tar_gz_bytes({"paper/PASJ_Sample_Paper.tex": load_example("PASJ_Sample_Paper.tex")})
    res_tgz = client.post(
        "/api/scan/file",
        files={"file": ("submission.tar.gz", io.BytesIO(tgz_bytes), "application/gzip")},
        data={"template": "auto"},
    )
    assert res_tgz.status_code == 200
    assert res_tgz.json()["detected_template"] == "pasj"


def test_api_scan_file_rejects_zip_slip(client):
    evil_zip = _make_zip_bytes({"../evil.tex": b"\\documentclass{PASJ2026}"})
    res = client.post(
        "/api/scan/file",
        files={"file": ("evil.zip", io.BytesIO(evil_zip), "application/zip")},
        data={"template": "auto"},
    )
    assert res.status_code == 400
    assert "Unsafe archive entry path" in res.json()["error"]


def test_indico_service_scans_zip_archive():
    mock_client = MagicMock(spec=IndicoClient)
    mock_client.get_contribution_paper.return_value = {
        "id": 9,
        "revisions": [
            {
                "id": 4,
                "files": [
                    {"id": 1, "filename": "paper.pdf", "download_url": "/dl/paper.pdf"},
                    {"id": 2, "filename": "source.zip", "download_url": "/dl/source.zip"},
                ],
            }
        ],
    }
    mock_client.download_file.return_value = _make_zip_bytes({
        "PASJ_Sample_Paper.tex": load_example("PASJ_Sample_Paper.tex"),
    })
    mock_client.create_comment.return_value = True

    service = IndicoScanService(client=mock_client)
    res = service.scan_contribution_paper(event_id=5, contribution_id=9, post_comment=True)
    assert res["doc_type"] == "latex"
    assert res["template"] == "pasj"
    assert res["comment_posted"] is True
