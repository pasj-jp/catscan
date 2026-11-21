import re
from ..common.citations import CITATION, ENTRY_NUMBER, citation_ranges, missing_labels, numbers_in_range
from ..common.docx_utils import check_style, get_style_font_run
from .constants import (
    REFERENCE_STYLES as STYLES,
    REFERENCE_EXTRA_RULES as EXTRA_RULES,
    REFERENCE_HELP_INFO as HELP_INFO,
    REFERENCE_EXTRA_INFO as EXTRA_INFO,
)

RE_REFS_LIST_TAB = re.compile(r'^\[\d+\]\t')


def extract_references(doc):
    references = []
    citations = []
    in_manuscript = in_bibliography = False
    complete = True
    for index, paragraph in enumerate(doc.paragraphs, 1):
        text = paragraph.text.strip()
        if not in_manuscript:
            in_manuscript = text.casefold() == "abstract"
            continue
        if text.casefold() == "references" and "subsection" not in paragraph.style.name.casefold():
            in_bibliography = True
            continue
        if in_bibliography and (match := ENTRY_NUMBER.match(text)):
            references.append(dict(id=int(match[1]), text=text, style=paragraph.style.name, p=paragraph))
        elif in_bibliography and text and paragraph.style.name.startswith("JACoW_Reference"):
            complete = False
        else:
            citations.extend((index, text, match) for match in CITATION.finditer(text))

    numbers = sorted({reference["id"] for reference in references})
    used_references = set()
    out_of_order = set()
    findings = []
    next_number = 1
    for index, text, match in citations:
        missing = []
        cited_here = set()
        for first, last in citation_ranges(match[1]):
            present = numbers_in_range(numbers, first, last)
            if complete:
                missing.extend(missing_labels(first, last, present))
            cited_here.update(present)
        newly_cited = cited_here - used_references
        used_references.update(newly_cited)
        while next_number in used_references:
            next_number += 1
        out_of_order.update(number for number in newly_cited if number > next_number)
        if missing:
            findings.append({
                "id": "",
                "text": text,
                "paragraph_number": index,
                "location": f"Paragraph {index}",
                "citation_issue": "missing_reference",
                "citation_ok": False,
                "notes": f"No bibliography entry for {', '.join(dict.fromkeys(missing))}.",
            })

    # check reference styles, order etc
    ref_count = len(references)
    seen = set()
    for i, ref in enumerate(references, 1):
        if ref['id'] in seen:
            ref['duplicate'] = True
            ref['unique_ok'] = False
        else:
            ref['unique_ok'] = True
        seen.add(ref['id'])
        ref['order_ok'] = i == ref['id'] and i not in out_of_order
        ref['used_ok'] = ref['id'] in used_references
        ref['text_ok'] = True
        ref['text_error'] = ''

        if not RE_REFS_LIST_TAB.search(ref['text']):
            ref['text_error'] = f"Number format error should be [{i}] followed by a tab"
            ref['text_ok'] = False

        # check for doi or urls
        starts = ['doi:', 'http://www.', 'http://', 'https://', 'www.']
        url_font = {'name': 'Liberation Mono', 'size': 8}
        has_url = has_url_error = False
        for r in ref['p'].runs:
            if r.style is not None:
                text = r.text.strip()
                for s in starts:
                    if text.startswith(s):
                        has_url = True
                        bold, italic, font_size, font_name, all_caps = \
                            get_style_font_run(r)

                        if not font_size or not font_name == url_font['name'] \
                                or not font_size == url_font['size']:
                            has_url_error = True
                            ref['text_ok'] = False
                        break
                    elif s in text:
                        # means that the font name and size did not change at start.
                        # may be an issue if two DOIs or URLs after one another
                        has_url = True
                        has_url_error = True
                        ref['text_ok'] = False

        if has_url_error:
            ref['text_error'] = ref['text_error'] + \
                                f"URLs and DOIs should be {url_font['name']} and size {url_font['size']}pt"

        if ref_count <= 9:
            style_compare = STYLES['LessThanNineTotal']
        else:
            if i <= 9:
                style_compare = STYLES['LessThanNine']
            else:
                style_compare = STYLES['MoreThanNine']

        style_ok, detail = check_style(
            ref['p'],
            style_compare,
            url={'has_url': has_url, 'url_font': url_font, 'starts': starts}
        )
        ref['style_ok'] = style_ok
        ref.update(detail)
        # delete p from dictionary since it is un unserialisable Paragragh
        del ref['p']

    return references, findings


def get_reference_summary(doc):
    references, findings = extract_references(doc)
    ok = not findings and all(
        row[key] for row in references
        for key in ("text_ok", "used_ok", "order_ok", "unique_ok", "style_ok")
    )

    return {
        'title': 'References',
        'rules': STYLES,
        'extra_rules': EXTRA_RULES,
        'help_info': HELP_INFO,
        'extra_info': EXTRA_INFO,
        'ok': ok,
        'message': 'Reference issues',
        'details': findings + references,
        'anchor': 'references',
        'show_total': True,
    }
