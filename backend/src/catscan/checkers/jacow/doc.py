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


def parse_paragraphs(doc):
    title_index = author_index = abstract_index = reference_index = -1
    current_style = None

    summary = {}
    for i, p in enumerate(doc.paragraphs):
        # first paragraph is the title
        text = p.text.strip()
        if not text:
            continue

        # first non empty paragraph is the title
        # Assume all of title is same style so end of title is when the style changes
        if title_index == -1:
            title_index = i
        elif title_index != -1 and author_index == -1 and current_style != p.style.name:
            author_index = i

        # find abstract heading
        if text.lower() == 'abstract':
            abstract_index = i
            summary['Abstract'] = get_abstract_summary(p)

        current_style = p.style.name

        # find reference heading
        if text.lower() == 'references':
            reference_index = i
            break

    # if abstract not found
    if abstract_index == -1:
        return None, "Abstract not found"

    # authors is all the text between title and abstract heading
    summary['Title'] = get_title_summary(doc.paragraphs[title_index: author_index])
    summary['Authors'] = get_author_summary(doc.paragraphs[author_index: abstract_index])

    return summary, None


def create_upload_variables(doc):
    doc_summary, error = parse_paragraphs(doc)

    if doc_summary is None:
        return None, error

    # get style details
    summary = {
        'Title': doc_summary['Title'],
        'Authors': doc_summary['Authors'],
        'Abstract': doc_summary['Abstract'],
        'Headings': get_heading_summary(doc),
        'Paragraphs': get_paragraph_summary(doc),
        'Figures': get_figure_summary(doc),
        'Tables': get_table_summary(doc),
        'References': get_reference_summary(doc),
        'Styles': get_style_summary(doc),
        'Margins': get_margin_summary(doc),
        'List': get_all_paragraph_summary(doc)
    }

    # get title and author to use in SPMS check
    title = summary['Title']['details']
    authors = summary['Authors']['details']

    return (summary, authors, title), None

