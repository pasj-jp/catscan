import io
import tarfile
import zipfile
from unittest.mock import MagicMock

from docx import Document
from docx.shared import Mm, Pt

from catscan.checkers.common.layout import check_sections
from catscan.checkers.latex.engine import RuleBasedLatexChecker
from catscan.checkers.pasj.word_checker import PasjWordChecker
from catscan.indico.client import IndicoClient
from catscan.indico.service import IndicoScanService
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
    assert data_zip["issuesFound"] == 0

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
