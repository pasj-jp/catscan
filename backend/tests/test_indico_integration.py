import os
import io
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

from catscan.main import app
from catscan.indico.config import IndicoConfig
from catscan.indico.client import IndicoClient, IndicoAPIError
from catscan.indico.service import IndicoScanService
from catscan.storage.report_store import ReportStore


def test_indico_config_defaults():
    cfg = IndicoConfig()
    assert cfg.base_url.startswith("http")
    assert isinstance(cfg.api_token, str)
    assert cfg.catscan_base_url.startswith("http")


def test_indico_client_headers():
    client = IndicoClient(IndicoConfig(base_url="http://indico.example.com", api_token="test-token"))
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Host"] == "indico.example.com"


def test_indico_service_mock_word():
    mock_client = MagicMock(spec=IndicoClient)
    mock_client.get_contribution_paper.return_value = {
        "id": 2,
        "contribution": {"id": 3, "code": "MOP001"},
        "revisions": [
            {
                "id": 1,
                "files": [
                    {
                        "id": 1,
                        "filename": "MOP001.docx",
                        "download_url": "/event/1/contributions/3/editing/paper/1/1/MOP001.docx",
                    }
                ],
            }
        ],
    }

    # Use actual sample docx bytes
    sample_docx_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../example/JACoW_MSWord_Style_Guide.docx"))
    with open(sample_docx_path, "rb") as f:
        mock_client.download_file.return_value = f.read()

    mock_client.create_comment.return_value = True

    service = IndicoScanService(client=mock_client)
    res = service.scan_contribution_paper(event_id=1, contribution_id=3, post_comment=True)

    assert res["contribution_id"] == 3
    assert res["revision_id"] == 1
    assert res["filename"] == "MOP001.docx"
    assert res["doc_type"] == "word"
    assert res["comment_posted"] is True
    assert "report_id" in res
    assert "scores" in res["result"]
    assert "### 🐱 CatScan Automated Format Validation" in res["comment_text"]

    # Verify report is retrievable
    report = ReportStore.get_report(res["report_id"])
    assert report is not None
    assert report["filename"] == "MOP001.docx"


def test_indico_service_mock_latex():
    mock_client = MagicMock(spec=IndicoClient)
    mock_client.get_contribution_paper.return_value = {
        "id": 3,
        "contribution": {"id": 4, "code": "MOP002"},
        "revisions": [
            {
                "id": 2,
                "files": [
                    {
                        "id": 2,
                        "filename": "MOP002.tex",
                        "download_url": "/event/1/contributions/4/editing/paper/2/2/MOP002.tex",
                    }
                ],
            }
        ],
    }

    sample_tex_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../example/paper.tex"))
    with open(sample_tex_path, "rb") as f:
        mock_client.download_file.return_value = f.read()

    mock_client.create_comment.return_value = True

    service = IndicoScanService(client=mock_client)
    res = service.scan_contribution_paper(event_id=1, contribution_id=4, post_comment=True)

    assert res["contribution_id"] == 4
    assert res["revision_id"] == 2
    assert res["filename"] == "MOP002.tex"
    assert res["doc_type"] == "latex"
    assert res["comment_posted"] is True
    assert res["result"]["report_type"] == "latex"
    assert res["result"]["issuesFound"] > 0
    assert "### 🐱 CatScan Automated Reference & Style Validation" in res["comment_text"]

    # Verify report is retrievable
    report = ReportStore.get_report(res["report_id"])
    assert report is not None
    assert report["report_type"] == "latex"


def test_api_indico_config_endpoint():
    client = TestClient(app)
    res = client.get("/api/indico/config")
    assert res.status_code == 200
    data = res.json()
    assert "indico_base_url" in data
    assert "token_configured" in data


def test_api_indico_scan_endpoint_mock():
    client = TestClient(app)
    sample_docx_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../example/JACoW_MSWord_Style_Guide.docx"))
    with open(sample_docx_path, "rb") as f:
        docx_bytes = f.read()

    with patch.object(IndicoClient, "get_contribution_paper") as mock_get, \
         patch.object(IndicoClient, "download_file") as mock_dl, \
         patch.object(IndicoClient, "create_comment") as mock_comment:

        mock_get.return_value = {
            "id": 2,
            "contribution": {"id": 3, "code": "MOP001"},
            "revisions": [
                {
                    "id": 1,
                    "files": [
                        {"id": 1, "filename": "MOP001.docx", "download_url": "/test/url"}
                    ]
                }
            ]
        }
        mock_dl.return_value = docx_bytes
        mock_comment.return_value = True

        res = client.post("/api/indico/events/1/contributions/3/scan")
        assert res.status_code == 200
        data = res.json()
        assert data["doc_type"] == "word"
        assert data["comment_posted"] is True
        assert "report_id" in data
