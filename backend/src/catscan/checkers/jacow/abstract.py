from ..common.citations import CITATION
from ..common.docx_utils import check_style_detail
from .constants import ABSTRACT_STYLES as STYLES, ABSTRACT_EXTRA_RULES as EXTRA_RULES, ABSTRACT_HELP_INFO as HELP_INFO


def get_abstract_summary(paragraphs, abstract_index):
    heading = paragraphs[abstract_index]
    style_compare = STYLES["normal"]
    details = [{
        "text": heading.text,
        "original_text": heading.text,
        **check_style_detail(heading, style_compare),
        "title_style_ok": heading.style.name == style_compare["styles"]["jacow"],
        "style": heading.style.name,
    }]
    for index in range(abstract_index + 1, len(paragraphs)):
        paragraph = paragraphs[index]
        if "heading" in paragraph.style.name.casefold():
            break
        if CITATION.search(paragraph.text):
            details.append({
                "text": paragraph.text,
                "location": f"Paragraph {index + 1}",
                "citation_ok": False,
                "notes": "Move citations from the abstract to the main text.",
            })
        # JACoW uses one paragraph for the abstract.
        if paragraph.text.strip():
            break

    summary = {
        "details": details,
        "rules": STYLES,
        "extra_rules": EXTRA_RULES,
        "help_info": HELP_INFO,
        "title": "Abstract",
        "ok": details[0]["style_ok"] and len(details) == 1,
        "message": "Abstract issues",
        "anchor": "abstract submission",
    }
    if len(details) > 1:
        summary["extra_info"] = {
            "title": "Abstract citation",
            "columns": ["location", "text", "notes"],
            "headers": "<thead><tr><th>Location</th><th>Text</th><th>Notes</th></tr></thead>",
        }
    return summary
