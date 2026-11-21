from ..common.layout import check_sections, paragraph_sections

EXTRA_RULES = [
    """
    <h3 class="subtitle is-6">Documents MUST be based on A4 or US Letter</h3>
    <table class="table is-bordered">
        <thead><tr><th colspan="2">A4</th></tr></thead>
        <tbody>
        <tr><td>Page Width</td><td>210mm</td></tr>
        <tr><td>Top</td><td>37mm</td></tr>
        <tr><td>Bottom</td><td>19mm</td></tr>
        <tr><td>Left</td><td>20mm</td></tr>
        <tr><td>Right</td><td>20mm</td></tr>
        </tbody>
    </table>
    <table class="table is-bordered">
        <thead><tr><th colspan="2">US Letter</th></tr></thead>
        <tbody>
        <tr><td>Page Width</td><td>8.5in</td></tr>
        <tr><td>Top</td><td>0.75in</td></tr>
        <tr><td>Bottom</td><td>0.75in</td></tr>
        <tr><td>Left</td><td>0.79in</td></tr>
        <tr><td>Right</td><td>1.02in</td></tr>
        </tbody>
    </table>
    Check gutter setting (Space between columns), for all section with more than 1 column, should be 0.51cm.
    """
]
HELP_INFO = "CSEPageSizeandMargins"
EXTRA_INFO = {
    "title": "Style Breakdown",
    "headers": "<thead><tr><th>Section</th><th>Page Size</th><th colspan=\"2\">Margins</th><th>Columns</th><th colspan=\"2\">Column Gutter (cm)</th><th>Notes</th></tr> </thead>",
    "columns": ["loop.index", "page_size", "margins", "margins_ok", "col_number", "col_gutter", "col_ok", "notes"],
}


def get_margin_summary(doc):
    sections = check_sections(doc)
    body = [p for p in doc.paragraphs if p.text.strip() and p.style.name in {
        "JACoW_Body Text Indent", "Body Text Indent",
    }]
    body_sections = paragraph_sections(doc, body)
    # Full-width figures and example blocks can interrupt a two-column body.
    if body_sections and all(sections[i]["col_number"] == 1 for i in body_sections):
        for index in body_sections:
            sections[index]["col_ok"] = False
            sections[index]["notes"] = "Set the manuscript body to two columns."
    ok = all(section["margins_ok"] and section["col_ok"] for section in sections)
    return {
        "title": "Page Size and Margins",
        "extra_rules": EXTRA_RULES,
        "help_info": HELP_INFO,
        "extra_info": EXTRA_INFO,
        "ok": ok,
        "message": "Margins",
        "details": sections,
        "anchor": "margins",
    }
