from ..common.docx_utils import (
    get_style_details,
    check_style,
    check_style_detail,
    get_compare,
    get_paragraph_alignment,
    get_indents,
    get_paragraph_space,
    get_style_font_run,
    get_style_font,
)

VALID_STYLES = [
    'JACoW_Abstract_Heading',
    'JACoW_Author List',
    'JACoW_Body Text Indent',
    'JACoW_Bulleted List',
    'JACoW_Numbered list',
    'JACoW_Paper Title',
    'JACoW_Reference #10 onwards',
    'JACoW_Reference #1-9 when >= 10 Refs',
    'JACoW_Reference when <= 9 Refs',
    'JACoW_Reference Italics',
    'JACoW_Reference url_doi',
    'JACoW_Third-level Heading',
    'JACoW_Section Heading',
    'JACoW_Subsection Heading',
]

VALID_NON_JACOW_STYLES = [
    'Figure Caption',
    'Figure Caption Multi Line',
    'Table Caption',
    'Table Caption Multi Line',
    'Caption',
    'Caption Multi Line',
]

OTHER_VALID_STYLES = ['Body Text Indent', 'Normal', 'Caption', 'Heading 3']

EXTRA_RULES = [
    """
<p>The latest JACoW Template must be used.<br/>
Standard JACoW Style’s must embedded in the document.</p>   
    """
]
HELP_INFO = 'CSEJACoWStyles'
EXTRA_INFO = {
    'title': 'Style Breakdown',
    'headers': '<thead><tr><th>Style</th><th>Embedded in Document</th></tr></thead>',
    'columns': ['style', 'style_ok'],
}


def check_jacow_styles(doc):
    result = []
    jacow_styles = get_jacow_styles(doc)

    for valid_style in VALID_STYLES:
        result.append({'style': valid_style, 'style_ok': valid_style in jacow_styles})

    return result


def get_jacow_styles(doc):
    return [s.name for s in doc.styles if s.name is not None and s.name.startswith('JACoW')]


def get_style_summary(doc):
    jacow_styles = check_jacow_styles(doc)
    return {
        'title': 'JACoW Styles',
        'extra_rules': EXTRA_RULES,
        'help_info': HELP_INFO,
        'extra_info': EXTRA_INFO,
        'ok': all([tick['style_ok'] for tick in jacow_styles]),
        'message': 'Styles issues',
        'details': jacow_styles,
        'anchor': 'styles',
    }
