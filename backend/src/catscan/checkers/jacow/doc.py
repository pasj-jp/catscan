from ...errors import DocumentError
from .styles import get_style_summary
from .margins import get_margin_summary
from .title import get_title_summary
from .authors import get_author_summary
from .abstract import get_abstract_summary
from .heading import get_heading_summary
from .paragraph import get_paragraph_summary, get_all_paragraph_summary
from .references import get_reference_summary
from .figures import get_figure_summary
from .tables import get_table_summary


def build_summary(doc):
    paragraphs = doc.paragraphs
    title_start = author_start = abstract = None
    title_style = None
    for index, paragraph in enumerate(paragraphs):
        text = paragraph.text.strip().casefold()
        if not text:
            continue
        if title_start is None:
            title_start = index
            title_style = paragraph.style.name
        elif author_start is None and paragraph.style.name != title_style:
            author_start = index
        if text == "abstract":
            abstract = index
        elif text == "references":
            break
    if abstract is None:
        raise DocumentError("Abstract not found")

    author_start = author_start if author_start is not None else -1
    return {
        "Title": get_title_summary(paragraphs[title_start:author_start]),
        "Authors": get_author_summary(paragraphs[author_start:abstract]),
        "Abstract": get_abstract_summary(paragraphs, abstract),
        "Headings": get_heading_summary(doc),
        "Paragraphs": get_paragraph_summary(doc),
        "Figures": get_figure_summary(doc),
        "Tables": get_table_summary(doc),
        "References": get_reference_summary(doc),
        "Styles": get_style_summary(doc),
        "Margins": get_margin_summary(doc),
        "List": get_all_paragraph_summary(doc),
    }
