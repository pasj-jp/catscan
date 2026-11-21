from typing import Any, Dict, List

from ..checkers.common.score import detail_rows, row_checks

PASJ_CATEGORY_LABELS: Dict[str, str] = {
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

LABELS = {
    "pasj": {
        "status_passed": "✅ **PASSED (適合 — 全項目合格)**",
        "category_summary": "#### Category Summary / 検査項目別サマリー",
        "key_issues": "#### Key Issues Detected / 要修正・確認事項",
        "report_link": "View Full Interactive Validation Report / 詳細検証レポートを開く",
        "latex_passed": "✅ **{template_name} の LaTeX ソース検査で問題は検出されませんでした。**",
        "latex_detected_issues": "#### Detected Issues / 検出された要修正項目",
    },
    "jacow": {
        "status_passed": "✅ **PASSED (All Checks Passed)**",
        "category_summary": "#### Category Summary",
        "key_issues": "#### Key Issues Detected",
        "report_link": "View Full Interactive Validation Report",
        "latex_passed": "✅ **The {template_name} LaTeX source checks found no issues.**",
        "latex_detected_issues": "#### Detected Issues",
    },
}


def _word_notes(result: Dict[str, Any], is_pasj: bool) -> List[str]:
    notes = []
    for category, section in result.get("summary", {}).items():
        if category == "List" or section.get("ok") is True:
            continue
        label = PASJ_CATEGORY_LABELS.get(category, category) if is_pasj else category
        section_notes = []
        for row in detail_rows(section.get("details")):
            checks = dict(row_checks(row))
            if all(verdict is True for verdict in checks.values()) and row.get("ok") is not False:
                continue
            location = f"{row['location']} — " if row.get("location") else ""
            message = row.get("notes") or row.get("text_error") or row.get("status")
            if message:
                section_notes.append(location + message)
                continue
            if checks.get("case_ok") is False:
                section_notes.append("Check the title capitalization.")
            if checks.get("used_ok") is False and category == "References":
                section_notes.append(f"Reference [{row.get('id', '?')}] is not cited in the manuscript.")
            section_notes.extend(str(row[key]) for key in checks if isinstance(row[key], str))

        unique_notes = list(dict.fromkeys(section_notes))
        if unique_notes:
            message = " · ".join(unique_notes[:3])
            if len(unique_notes) > 3:
                message += f" (+{len(unique_notes) - 3} more)"
        else:
            _, warnings, errors = result["scores"].get(category, (0, 0, 0))
            message = f"{errors} errors, {warnings} warnings detected"
        icon = "⚠️" if section.get("ok") == 2 else "❌"
        notes.append(f"{icon} **{label}**: {message}")
    return notes


def _render_word(result: Dict[str, Any], report_url: str, is_pasj: bool, labels: Dict[str, str]) -> str:
    filename = result.get("filename", "manuscript")
    template_name = result.get("template_name", "JACoW Style")
    scores = result.get("scores", {})
    total = scores.get("total", (0, 0, 0))
    ok_count, warn_count, err_count = total[0], total[1], total[2]

    if err_count == 0 and warn_count == 0:
        status_str = labels["status_passed"]
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
        labels["category_summary"],
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

    diag_notes = _word_notes(result, is_pasj=is_pasj)
    if diag_notes:
        lines.append("")
        lines.append(labels["key_issues"])
        for note in diag_notes[:8]:
            lines.append(f"- {note}")
        if len(diag_notes) > 8:
            lines.append(f"- *...and {len(diag_notes) - 8} additional items in the interactive report.*")

    lines.append("")
    lines.append(f"👉 [**{labels['report_link']}**]({report_url})")
    return "\n".join(lines)


def _table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _render_latex(result: Dict[str, Any], report_url: str, is_pasj: bool, labels: Dict[str, str]) -> str:
    filename = result.get("filename", "manuscript")
    template_name = result.get("template_name", "JACoW Style")
    issues = result["issues"]
    issues_found = len(issues)
    total_refs = result.get("total_references", 0)
    notices = result.get("coverage_notices", [])

    if issues_found == 0 and notices:
        status_str = "⚠️ **CHECKS INCOMPLETE / 未検査あり**" if is_pasj else "⚠️ **CHECKS INCOMPLETE**"
    elif issues_found == 0:
        status_str = labels["status_passed"]
    else:
        status_str = (
            f"❌ **REVISION REQUIRED / 要修正 ({issues_found} Issues Found)**"
            if is_pasj
            else f"❌ **REVISION REQUIRED ({issues_found} Issues Found)**"
        )

    lines = [
        "### 🐱 CatScan Automated Format Validation",
        f"- **Document**: `{filename}` ({template_name})",
        f"- **Validation Status**: {status_str}",
        f"- **References Inspected**: {total_refs} | **Formatting Issues Found**: **{issues_found}**",
        "",
    ]

    if notices:
        lines.append("**未検査の項目 / Incomplete checks**" if is_pasj else "**Incomplete checks**")
        for notice in notices[:10]:
            message = notice.get("message_ja") if is_pasj else notice.get("message")
            path = notice.get("file")
            prefix = f"{path}:{notice['line']} " if path and notice.get("line") else ""
            lines.append(f"- {prefix}{message or notice.get('message', '')}")
        if len(notices) > 10:
            lines.append(f"*...and {len(notices) - 10} more notices in the full interactive report.*")
        lines.append("")

    if issues_found == 0 and not notices:
        lines.append(labels["latex_passed"].format(template_name=template_name))
    elif issues_found:
        lines.append(labels["latex_detected_issues"])
        lines.append("| # | Category / Target | Violation Details & Suggestion |")
        lines.append("| :---: | :--- | :--- |")

        for index, issue in enumerate(issues[:10], 1):
            target = _table_cell(issue["name"])
            message = issue["message"]
            if is_pasj:
                message = issue.get("message_ja", message)
            if issue.get("file") and issue.get("line"):
                message = f"{issue['file']}:{issue['line']} — {message}"
            lines.append(f"| {index} | {target} | {_table_cell(message)} |")
        if issues_found > 10:
            lines.append(f"\n*...and {issues_found - 10} more issues in the full interactive report.*")

    lines.append("")
    lines.append(f"👉 [**{labels['report_link']}**]({report_url})")
    return "\n".join(lines)


def render_comment(result: Dict[str, Any], report_url: str) -> str:
    """Format an informative, structured Markdown review comment for the Indico timeline."""
    template_name = result.get("template_name", "JACoW Style")
    is_pasj = result.get("detected_template") == "pasj" or "PASJ" in template_name
    labels = LABELS["pasj"] if is_pasj else LABELS["jacow"]

    if result["report_type"] == "word":
        return _render_word(result, report_url, is_pasj, labels)
    return _render_latex(result, report_url, is_pasj, labels)
