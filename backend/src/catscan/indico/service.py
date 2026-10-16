import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..checkers.factory import get_checker
from ..storage.report_store import ReportStore
from .client import IndicoClient, IndicoAPIError
from .config import IndicoConfig

logger = logging.getLogger("catscan.indico.service")

PASJ_CATEGORY_LABELS = {
    "Title": "Title (題名)",
    "Authors": "Authors (著者・所属)",
    "Abstract": "Abstract (英文要旨)",
    "Headings": "Headings (見出し)",
    "Paragraphs": "Paragraphs (本文・句読点)",
    "Figures": "Figures (図キャプション)",
    "Tables": "Tables (表タイトル)",
    "References": "References (参考文献)",
    "Margins": "Margins (余白・段組)",
    "Styles": "Styles (スタイル定義)",
    "List": "List (全段落一覧)",
}


class IndicoScanService:
    """
    Coordinates fetching papers from Indico, running Word/LaTeX validation,
    storing reports, and posting feedback comments to the Indico revision timeline.
    """

    def __init__(self, client: Optional[IndicoClient] = None, config: Optional[IndicoConfig] = None):
        self.config = config or IndicoConfig.get_default()
        self.client = client or IndicoClient(config=self.config)

    def list_papers(self, event_id: int) -> List[Dict[str, Any]]:
        """List all paper contributions for an event."""
        return self.client.get_papers(event_id)

    def scan_contribution_paper(
        self,
        event_id: int,
        contribution_id: int,
        post_comment: bool = True,
        template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate the latest revision of a paper submission and optionally post results back.
        """
        paper_data = self.client.get_contribution_paper(event_id, contribution_id)
        revisions = paper_data.get("revisions", [])
        if not revisions:
            raise ValueError(f"No revisions found for event {event_id}, contribution {contribution_id}.")

        latest_rev = revisions[-1]
        rev_id = latest_rev["id"]
        files = latest_rev.get("files", [])

        # Locate Word (.docx) or LaTeX (.tex) file
        target_file = None
        doc_type = None

        for f in files:
            fname = f.get("filename", "").lower()
            if fname.endswith(".docx"):
                target_file = f
                doc_type = "word"
                break
            elif fname.endswith(".tex"):
                target_file = f
                doc_type = "latex"
                break

        if not target_file:
            raise ValueError(
                f"No editable Word (.docx) or LaTeX (.tex) source file found in revision {rev_id}."
            )

        filename = target_file["filename"]
        download_url = target_file.get("download_url") or target_file.get("external_download_url")
        if not download_url:
            raise ValueError(f"File {filename} has no download URL in revision {rev_id}.")

        file_bytes = self.client.download_file(download_url)

        # Run validation
        selected_template = template or "auto"
        if doc_type == "word":
            checker, effective_template = get_checker(
                doc_type="word",
                template=selected_template,
                file_source=file_bytes,
            )
            result = checker.validate(
                file_source=file_bytes,
                filename=filename,
                conference_id=event_id,
            )
            result["detected_template"] = effective_template
            result["template_name"] = "JACoW 英文原稿" if effective_template == "jacow" else "PASJ 和文原稿"
        else:
            checker, effective_template = get_checker(
                doc_type="latex",
                template=selected_template,
                file_source=file_bytes,
            )
            result = checker.validate(file_source=file_bytes, filename=filename)
            result["report_type"] = "latex"
            result["detected_template"] = effective_template
            result["template_name"] = "JACoW 英文原稿" if effective_template == "jacow" else "PASJ 和文原稿"

        # Persist report for web UI viewing
        report_id = ReportStore.generate_report_id(result)
        result["report_id"] = report_id
        result["filename"] = filename
        result["event_id"] = event_id
        result["contribution_id"] = contribution_id
        result["revision_id"] = rev_id
        ReportStore.save_report(result, report_id=report_id)

        report_url = f"{self.config.catscan_base_url}/?results={report_id}"

        # Generate and post comment
        comment_text = self._format_markdown_comment(result, report_url, doc_type)
        comment_posted = False

        if post_comment:
            try:
                self.client.create_comment(
                    event_id=event_id,
                    contribution_id=contribution_id,
                    revision_id=rev_id,
                    text=comment_text,
                    internal=False,
                )
                comment_posted = True
            except Exception as e:
                logger.error(f"Failed to post comment to Indico: {e}")

        return {
            "event_id": event_id,
            "contribution_id": contribution_id,
            "revision_id": rev_id,
            "filename": filename,
            "doc_type": doc_type,
            "template": effective_template,
            "report_id": report_id,
            "report_url": report_url,
            "comment_posted": comment_posted,
            "comment_text": comment_text,
            "result": result,
        }

    def _extract_word_diagnostic_notes(self, result: Dict[str, Any], is_pasj: bool) -> List[str]:
        """Extract concise, human-readable error/warning bullets from a Word validation summary."""
        notes_list: List[str] = []
        summary = result.get("summary", {})
        if not isinstance(summary, dict):
            return notes_list

        for cat, sec in summary.items():
            if not isinstance(sec, dict) or cat == "List":
                continue
            sec_ok = sec.get("ok")
            if sec_ok is True:
                continue

            cat_label = PASJ_CATEGORY_LABELS.get(cat, cat) if is_pasj else cat
            details = sec.get("details", [])
            if not isinstance(details, list):
                continue

            if is_pasj:
                if cat == "Paragraphs":
                    for d in details:
                        if isinstance(d, dict) and d.get("punct_ok") is False:
                            notes_list.append(f"❌ **{cat_label}**: {d.get('item')} — {d.get('status')}")
                else:
                    for d in details:
                        if isinstance(d, dict) and (d.get("ok") is False or d.get("style_ok") is False):
                            item_type = d.get("type") or d.get("text", "")[:30]
                            note_msg = d.get("notes") or "書式またはスタイル違反"
                            notes_list.append(f"❌ **{cat_label}** (`{item_type}`): {note_msg}")
            else:
                # JACoW Word diagnostic extraction
                icon = "❌" if sec_ok is False else "⚠️"
                cat_issues: List[str] = []
                flat_details: List[Dict[str, Any]] = []
                for d in details:
                    if isinstance(d, list):
                        flat_details.extend(x for x in d if isinstance(x, dict))
                    elif isinstance(d, dict):
                        flat_details.append(d)

                for d in flat_details:
                    if d.get("case_ok") is False:
                        cat_issues.append("Title capitalization check failed (requires >=70% UPPERCASE)")
                    if d.get("text_error"):
                        cat_issues.append(str(d["text_error"]))
                    if d.get("text_format_message") and isinstance(d["text_format_message"], list):
                        cat_issues.extend(str(m) for m in d["text_format_message"])
                    if d.get("used_ok") is False:
                        item_id = d.get("id", "?")
                        cat_issues.append(f"Item #{item_id} is not cited in the main text")
                    if d.get("order_ok") is False:
                        item_id = d.get("id", "?")
                        cat_issues.append(f"Item #{item_id} citation order mismatch")
                    for k, v in d.items():
                        if k != "text" and isinstance(v, str) and "should be" in v:
                            cat_issues.append(f"`{k}` ({v})")

                # Deduplicate preserving order
                unique_issues = list(dict.fromkeys(cat_issues))
                if unique_issues:
                    preview = "; ".join(unique_issues[:3])
                    if len(unique_issues) > 3:
                        preview += f" (+{len(unique_issues) - 3} more)"
                    notes_list.append(f"{icon} **{cat_label}**: {preview}")
                else:
                    sc = result.get("scores", {}).get(cat, (0, 0, 0))
                    notes_list.append(f"{icon} **{cat_label}**: {sc[2]} errors, {sc[1]} warnings detected")

        return notes_list

    def _format_markdown_comment(self, result: Dict[str, Any], report_url: str, doc_type: str) -> str:
        """Format an informative, structured Markdown review comment for the Indico timeline."""
        filename = result.get("filename", "manuscript")
        template_name = result.get("template_name", "JACoW Style")
        is_pasj = result.get("detected_template") == "pasj" or "PASJ" in template_name

        if doc_type == "word":
            scores = result.get("scores", {})
            total = scores.get("total", (0, 0, 0))
            ok_count, warn_count, err_count = total[0], total[1], total[2]

            if err_count == 0 and warn_count == 0:
                status_str = "✅ **PASSED (適合 — 全項目合格)**" if is_pasj else "✅ **PASSED (All Checks Passed)**"
            elif err_count == 0:
                status_str = f"⚠️ **PASSED WITH WARNINGS ({warn_count} Warnings)**"
            else:
                status_str = (
                    f"❌ **REVISION REQUIRED / 要修正 ({err_count} Errors, {warn_count} Warnings)**"
                    if is_pasj
                    else f"❌ **REVISION REQUIRED ({err_count} Errors, {warn_count} Warnings)**"
                )

            lines = [
                "### 🐱 CatScan Automated Format Validation",
                f"- **Document**: `{filename}` ({template_name})",
                f"- **Validation Status**: {status_str}",
                f"- **Overall Score**: **{ok_count}** Pass / **{warn_count}** Warnings / **{err_count}** Errors",
                "",
                "#### Category Summary / 検査項目別サマリー" if is_pasj else "#### Category Summary",
                "| Category | Status | Pass | Warning | Error |",
                "| :--- | :---: | :---: | :---: | :---: |",
            ]

            categories = ["Title", "Authors", "Abstract", "Headings", "Paragraphs", "Figures", "Tables", "References", "Margins", "Styles"]
            for cat in categories:
                if cat in scores:
                    sc = scores[cat]
                    p_cnt, w_cnt, e_cnt = sc[0], sc[1], sc[2]
                    if e_cnt > 0:
                        cat_status = "❌ Error"
                    elif w_cnt > 0:
                        cat_status = "⚠️ Warn"
                    else:
                        cat_status = "✅ OK"
                    cat_label = PASJ_CATEGORY_LABELS.get(cat, cat) if is_pasj else cat
                    lines.append(f"| **{cat_label}** | {cat_status} | {p_cnt} | {w_cnt} | {e_cnt} |")

            diag_notes = self._extract_word_diagnostic_notes(result, is_pasj=is_pasj)
            if diag_notes:
                lines.append("")
                lines.append("#### Key Issues Detected / 要修正・確認事項" if is_pasj else "#### Key Issues Detected")
                for note in diag_notes[:8]:
                    lines.append(f"- {note}")
                if len(diag_notes) > 8:
                    lines.append(f"- *...and {len(diag_notes) - 8} additional items in the interactive report.*")

            lines.append("")
            link_label = (
                "View Full Interactive Validation Report / 詳細検証レポートを開く"
                if is_pasj
                else "View Full Interactive Validation Report"
            )
            lines.append(f"👉 [**{link_label}**]({report_url})")
            return "\n".join(lines)

        else:
            # LaTeX report
            issues_found = result.get("issuesFound", 0)
            total_refs = result.get("total_references", 0)
            body = result.get("unabbreviated") or result.get("body", "No issues found")

            if issues_found == 0:
                status_str = "✅ **PASSED (適合 — 全項目合格)**" if is_pasj else "✅ **PASSED (All Checks Passed)**"
            else:
                status_str = (
                    f"❌ **REVISION REQUIRED / 要修正 ({issues_found} Issues Found)**"
                    if is_pasj
                    else f"❌ **REVISION REQUIRED ({issues_found} Issues Found)**"
                )

            lines = [
                "### 🐱 CatScan Automated Reference & Style Validation",
                f"- **Document**: `{filename}` ({template_name})",
                f"- **Validation Status**: {status_str}",
                f"- **References Inspected**: {total_refs} | **Formatting Issues Found**: **{issues_found}**",
                "",
            ]

            if issues_found == 0:
                if is_pasj:
                    lines.append(f"✅ **すべての書式、句読点、英文要旨および参考文献が {template_name} 執筆規定を満たしています。**")
                else:
                    lines.append(f"✅ **All references and formatting comply with {template_name} rules.**")
            else:
                lines.append("#### Detected Issues / 検出された要修正項目" if is_pasj else "#### Detected Issues")
                lines.append("| # | Category / Target | Violation Details & Suggestion |")
                lines.append("| :---: | :--- | :--- |")

                issue_blocks = [b.strip() for b in body.split("\n\n") if b.strip()]
                for idx, block in enumerate(issue_blocks[:10], 1):
                    m = re.match(r'^Issue found in\s+([^:]+):\s*([\s\S]*)$', block)
                    if m:
                        target = m.group(1).strip()
                        desc = m.group(2).strip()
                        # If bilingual "JA / EN", prefer concise JA for PASJ or EN for JACoW in table
                        if " / " in desc:
                            ja_part, en_part = desc.split(" / ", 1)
                            desc_display = ja_part.strip() if is_pasj else en_part.strip()
                        else:
                            desc_display = desc
                        desc_display = desc_display.replace("|", "\\|").replace("\n", " ")
                        lines.append(f"| {idx} | `{target}` | {desc_display} |")
                    else:
                        clean_b = block.replace("|", "\\|").replace("\n", " ")
                        lines.append(f"| {idx} | `issue` | {clean_b} |")

                if len(issue_blocks) > 10:
                    lines.append("")
                    lines.append(f"*...and {len(issue_blocks) - 10} more issues in the full interactive report.*")

            lines.append("")
            link_label = (
                "View Full Interactive Validation Report / 詳細検証レポートを開く"
                if is_pasj
                else "View Full Interactive Validation Report"
            )
            lines.append(f"👉 [**{link_label}**]({report_url})")
            return "\n".join(lines)
