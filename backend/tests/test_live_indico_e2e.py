#!/usr/bin/env python3
"""
Live End-to-End Integration Verification Script
Tests CatScan scanning Word and LaTeX manuscripts directly from Indico Event 1,
saving reports, and posting review feedback to the Indico timeline.
"""
import os
import sys
import json
import logging
import pytest
from catscan.indico.config import IndicoConfig
from catscan.indico.client import IndicoClient
from catscan.indico.service import IndicoScanService
from catscan.storage.report_store import ReportStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("catscan.e2e")

EVENT_ID = int(os.environ.get("INDICO_TEST_EVENT_ID", "1"))
WORD_CONTRIB_ID = int(os.environ.get("INDICO_TEST_WORD_CONTRIB_ID", "3"))
LATEX_CONTRIB_ID = int(os.environ.get("INDICO_TEST_LATEX_CONTRIB_ID", "4"))


@pytest.mark.skipif(
    not os.environ.get("INDICO_API_TOKEN"),
    reason="Live Indico integration test requires INDICO_API_TOKEN environment variable",
)
def test_live_indico_e2e():
    config = IndicoConfig.get_default()
    print("=" * 70)
    print("CatScan <-> Indico Live End-to-End Integration Test")
    print(f"Indico Base URL: {config.base_url}")
    print(f"CatScan Web Base URL: {config.catscan_base_url}")
    print("=" * 70)

    service = IndicoScanService(config=config)
    client = service.client

    # 1. List Papers
    print(f"\n[Step 1] Fetching Event {EVENT_ID} paper submissions from Indico...")
    papers = service.list_papers(EVENT_ID)
    print(f"Successfully retrieved {len(papers)} paper contributions:")
    for p in papers:
        print(f"  - Contrib ID {p['id']}: [{p.get('code')}] {p.get('title')}")

    assert len(papers) >= 2, f"Expected at least 2 papers, got {len(papers)}"

    # 2. Scan Word Paper
    print(f"\n[Step 2] Scanning Word Manuscript (Contribution {WORD_CONTRIB_ID})...")
    word_res = service.scan_contribution_paper(
        event_id=EVENT_ID,
        contribution_id=WORD_CONTRIB_ID,
        post_comment=True,
    )
    print(f"Word Scan Result:")
    print(f"  - Filename: {word_res['filename']}")
    print(f"  - Doc Type: {word_res['doc_type']}")
    print(f"  - Detected Template: {word_res['template']}")
    print(f"  - Report ID: {word_res['report_id']}")
    print(f"  - Report URL: {word_res['report_url']}")
    print(f"  - Comment Posted to Indico: {word_res['comment_posted']}")
    total_scores = word_res['result']['scores']['total']
    print(f"  - Total Scores: {total_scores[0]} Pass, {total_scores[1]} Warn, {total_scores[2]} Error")

    assert word_res["doc_type"] == "word"
    assert word_res["comment_posted"] is True
    assert total_scores[0] > 0

    # Verify report is in ReportStore
    saved_word_report = ReportStore.get_report(word_res["report_id"])
    assert saved_word_report is not None
    assert saved_word_report["filename"] == word_res["filename"]

    # 3. Scan LaTeX Paper
    print(f"\n[Step 3] Scanning LaTeX Manuscript (Contribution {LATEX_CONTRIB_ID})...")
    latex_res = service.scan_contribution_paper(
        event_id=EVENT_ID,
        contribution_id=LATEX_CONTRIB_ID,
        post_comment=True,
    )
    print(f"LaTeX Scan Result:")
    print(f"  - Filename: {latex_res['filename']}")
    print(f"  - Doc Type: {latex_res['doc_type']}")
    print(f"  - Detected Template: {latex_res['template']}")
    print(f"  - Report ID: {latex_res['report_id']}")
    print(f"  - Report URL: {latex_res['report_url']}")
    print(f"  - Comment Posted to Indico: {latex_res['comment_posted']}")
    print(f"  - References Inspected: {latex_res['result']['total_references']}")
    print(f"  - Issues Found: {latex_res['result']['issuesFound']}")

    assert latex_res["doc_type"] == "latex"
    assert latex_res["comment_posted"] is True
    assert latex_res["result"]["issuesFound"] >= 0

    # Verify report is in ReportStore
    saved_latex_report = ReportStore.get_report(latex_res["report_id"])
    assert saved_latex_report is not None
    assert saved_latex_report["report_type"] == "latex"

    # 4. Verify comments exist on Indico timeline
    print("\n[Step 4] Verifying review comments directly from Indico timeline...")
    p3_details = client.get_contribution_paper(EVENT_ID, WORD_CONTRIB_ID)
    p3_comments = p3_details["revisions"][-1]["comments"]
    has_word_comment = any("CatScan Automated Format Validation" in c.get("text", "") for c in p3_comments)
    print(f"  - Contribution {WORD_CONTRIB_ID} revision comments count: {len(p3_comments)} (Found CatScan comment: {has_word_comment})")
    assert has_word_comment, f"CatScan review comment not found on Contribution {WORD_CONTRIB_ID} timeline!"

    p4_details = client.get_contribution_paper(EVENT_ID, LATEX_CONTRIB_ID)
    p4_comments = p4_details["revisions"][-1]["comments"]
    has_latex_comment = any("CatScan Automated Reference & Style Validation" in c.get("text", "") for c in p4_comments)
    print(f"  - Contribution {LATEX_CONTRIB_ID} revision comments count: {len(p4_comments)} (Found CatScan comment: {has_latex_comment})")
    assert has_latex_comment, f"CatScan review comment not found on Contribution {LATEX_CONTRIB_ID} timeline!"

    print("\n" + "=" * 70)
    print("🎉 ALL LIVE INTEGRATION CHECKS PASSED SUCCESSFULLY! 🎉")
    print("=" * 70)


if __name__ == "__main__":
    test_live_indico_e2e()
