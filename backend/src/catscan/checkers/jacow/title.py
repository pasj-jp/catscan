from .page import get_text, check_title_case
from .styles import check_style_detail
from .constants import TITLE_STYLES as STYLES, TITLE_EXTRA_RULES as EXTRA_RULES, TITLE_HELP_INFO as HELP_INFO


def get_title_details(p):
    title = get_text(p)
    title_detail = {
        'text': title,
        'original_text': p.text,
        'case_ok': check_title_case(title, 0.7),
    }
    return title_detail


def get_title_summary(paragraphs):
    style_compare = STYLES['normal']
    title_details = []
    for p in paragraphs:
        if p.text.strip():
            detail = get_title_details(p)
            detail.update(check_style_detail(p, style_compare))
            title_style_ok = p.style.name == style_compare['styles']['jacow']
            detail.update({'title_style_ok': title_style_ok, 'style': p.style.name})
            title_details.append(detail)
    return {
        'details': title_details,
        'rules': STYLES,
        'extra_rules': EXTRA_RULES,
        'help_info': HELP_INFO,
        'title': 'Title',
        'ok': all([tick['style_ok'] and tick['case_ok'] for tick in title_details]),
        'message': 'Title issues',
        'anchor': 'title'
    }

