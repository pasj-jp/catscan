import re
from typing import Any, Dict, List

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
        "latex_passed": "✅ **すべての書式、句読点、英文要旨および参考文献が {template_name} 執筆規定を満たしています。**",
        "latex_detected_issues": "#### Detected Issues / 検出された要修正項目",
    },
    "jacow": {
        "status_passed": "✅ **PASSED (All Checks Passed)**",
        "category_summary": "#### Category Summary",
        "key_issues": "#### Key Issues Detected",
        "report_link": "View Full Interactive Validation Report",
        "latex_passed": "✅ **All references and formatting comply with {template_name} rules.**",
        "latex_detected_issues": "#### Detected Issues",
    },
}


def _extract_word_diagnostic_notes(result: Dict[str, Any], is_pasj: bool) -> List[str]:
    notes: List[str] = []
    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        return notes

    for cat, sec in summary.items():
        if not isinstance(sec, dict) or cat == "List" or sec.get("ok") is True:
            continue

        cat_label = PASJ_CATEGORY_LABELS.get(cat, cat) if is_pasj else cat
        details = sec.get("details", [])
        if not isinstance(details, list):
            continue

        if is_pasj:
            if cat == "Paragraphs":
                for d in details:
                    if isinstance(d, dict) and d.get("punct_ok") is False:
                        notes.append(f"❌ **{cat_label}**: {d.get('item')} — {d.get('status')}")
            else:
                for d in details:
                    if isinstance(d, dict) and (d.get("ok") is False or d.get("style_ok") is False):
                        item_type = d.get("type") or d.get("text", "")[:30]
                        note_msg = d.get("notes") or "書式またはスタイル違反"
                        notes.append(f"❌ **{cat_label}** (`{item_type}`): {note_msg}")
        else:
            sec_ok = sec.get("ok")
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
                if d.get("text_format_message"):
                    tfm = d["text_format_message"]
                    if isinstance(tfm, list):
                        cat_issues.extend(str(m) for m in tfm)
                    else:
                        cat_issues.append(str(tfm))
                if d.get("used_ok") is False:
                    cat_issues.append(f"Item #{d.get('id', '?')} is not cited in the main text")
                if d.get("order_ok") is False:
                    cat_issues.append(f"Item #{d.get('id', '?')} citation order mismatch")
                for k, v in d.items():
                    if k != "text" and isinstance(v, str) and "should be" in v:
                        cat_issues.append(f"`{k}` ({v})")

            unique_issues = list(dict.fromkeys(cat_issues))
            if unique_issues:
                preview = "; ".join(unique_issues[:3])
                if len(unique_issues) > 3:
                    preview += f" (+{len(unique_issues) - 3} more)"
                notes.append(f"{icon} **{cat_label}**: {preview}")
            else:
                sc = result.get("scores", {}).get(cat, (0, 0, 0))
                notes.append(f"{icon} **{cat_label}**: {sc[2]} errors, {sc[1]} warnings detected")

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

    diag_notes = _extract_word_diagnostic_notes(result, is_pasj=is_pasj)
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


def _render_latex(result: Dict[str, Any], report_url: str, is_pasj: bool, labels: Dict[str, str]) -> str:
    filename = result.get("filename", "manuscript")
    template_name = result.get("template_name", "JACoW Style")
    issues_found = result.get("issuesFound", 0)
    total_refs = result.get("total_references", 0)

    if issues_found == 0:
        status_str = labels["status_passed"]
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
        lines.append(labels["latex_passed"].format(template_name=template_name))
    else:
        lines.append(labels["latex_detected_issues"])
        lines.append("| # | Category / Target | Violation Details & Suggestion |")
        lines.append("| :---: | :--- | :--- |")

        # Prefer structured issues if present
        structured_issues = result.get("issues")
        if structured_issues is not None:
            for idx, item in enumerate(structured_issues[:10], 1):
                target = item.get("name", "issue").strip()
                desc = item.get("message", "").strip()
                if " / " in desc:
                    ja_part, en_part = desc.split(" / ", 1)
                    desc_display = ja_part.strip() if is_pasj else en_part.strip()
                else:
                    desc_display = desc
                desc_display = desc_display.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {idx} | `{target}` | {desc_display} |")
            if len(structured_issues) > 10:
                lines.append("")
                lines.append(f"*...and {len(structured_issues) - 10} more issues in the full interactive report.*")
        else:
            body = result.get("unabbreviated") or result.get("body", "No issues found")
            issue_blocks = [b.strip() for b in body.split("\n\n") if b.strip()]
            for idx, block in enumerate(issue_blocks[:10], 1):
                m = re.match(r'^Issue found in\s+([^:]+):\s*([\s\S]*)$', block)
                if m:
                    target = m.group(1).strip()
                    desc = m.group(2).strip()
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
    lines.append(f"👉 [**{labels['report_link']}**]({report_url})")
    return "\n".join(lines)


def render_comment(result: Dict[str, Any], report_url: str, doc_type: str = "word") -> str:
    """Format an informative, structured Markdown review comment for the Indico timeline."""
    template_name = result.get("template_name", "JACoW Style")
    is_pasj = result.get("detected_template") == "pasj" or "PASJ" in template_name
    labels = LABELS["pasj"] if is_pasj else LABELS["jacow"]

    if doc_type == "word":
        return _render_word(result, report_url, is_pasj, labels)
    return _render_latex(result, report_url, is_pasj, labels)
