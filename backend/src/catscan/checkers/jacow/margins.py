from ..common.layout import (
    check_sections,
    check_margins,
    check_margins_A4,
    check_margins_JACoW,
    check_margins_letter,
    get_margins,
    get_margins_A4,
    get_margins_JACoW,
    get_margins_letter,
    get_columns,
)

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
    "headers": "<thead><tr><th>Section</th><th>Page Size</th><th colspan=\"2\">Margins</th><th>Columns</th><th colspan=\"2\">Column Gutter (cm)</th></tr> </thead>",
    "columns": ["loop.index", "page_size", "margins", "margins_ok", "col_number", "col_gutter", "col_ok"],
}


def get_margin_summary(doc):
    sections = check_sections(doc)
    ok = all([tick["margins_ok"] for tick in sections]) and all([tick["col_ok"] for tick in sections])
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
