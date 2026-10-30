from .conftest import EXAMPLE_DIR, load_example
from catscan.checkers.registry import get_checker
from catscan.services import reports

SAMPLE_DOC = EXAMPLE_DIR / "JACoW_MSWord_Style_Guide.docx"


def test_jacow_word_checker_direct():
    assert SAMPLE_DOC.is_file(), f"Sample document not found at {SAMPLE_DOC}"
    checker = get_checker("jacow", "word")
    data = load_example("JACoW_MSWord_Style_Guide.docx")
    result = checker.check(data, filename="JACoW_MSWord_Style_Guide.docx")

    assert "error" not in result
    assert "scores" in result
    assert "summary" in result
    assert "metadata" in result
    assert result["filename"] == "JACoW_MSWord_Style_Guide.docx"

    total = result["scores"]["total"]
    assert len(total) == 3
    assert total[0] > 0  # success count > 0

    # Test report persistence
    report_id = reports.save(result)
    assert report_id is not None
    retrieved = reports.load(report_id)
    assert retrieved is not None
    assert retrieved["filename"] == result["filename"]


def test_api_scan_word_upload(client):
    # Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Direct file upload scan
    with open(SAMPLE_DOC, "rb") as f:
        upload_res = client.post(
            "/api/scan/word",
            files={"file": ("test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"template": "jacow"}
        )

    assert upload_res.status_code == 200
    data = upload_res.json()
    assert "report_id" in data
    assert "scores" in data
    assert data["scores"]["total"][0] > 0

    # Retrieve report via /api/reports/{id}
    report_id = data["report_id"]
    get_res = client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["report_id"] == report_id


def test_api_scan_word_upload_pasj(client):
    with open(SAMPLE_DOC, "rb") as f:
        res = client.post(
            "/api/scan/word",
            files={"file": ("test_pasj.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"template": "pasj"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_template"] == "pasj"
    assert data["template_name"] == "PASJ 和文原稿"
    assert "scores" in data
    assert "report_id" in data
