import io
import operator
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING
from docx import Document
from docx.shared import Inches, Mm, Twips
from docx.oxml.text.parfmt import CT_PPr, CT_Ind
from docx.text.paragraph import Paragraph

from ...errors import DocumentError

if TYPE_CHECKING:
    from ..engine.primitives import ElementContext


def open_docx(data: bytes) -> Document:
    try:
        doc = Document(docx=io.BytesIO(data))
    except KeyError:
        raise DocumentError(
            "Document may not be in a supported format.\n"
            "Try re-saving the file as a 'Word Document' (.docx) and try again."
        )
    except Exception as e:
        raise DocumentError(f"Failed to open Word document: {str(e)}")

    if check_tracking_on(doc):
        raise DocumentError(
            "Cannot process file: Track Changes (revision tracking) is turned on.\n"
            "Please accept/reject all changes and turn tracking off before submitting."
        )
    return doc


def doc_metadata(doc: Document) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    metadata = doc.core_properties
    if metadata:
        meta = {
            "author": metadata.author,
            "revision": metadata.revision,
            "version": metadata.version,
            "language": metadata.language,
        }
        if metadata.created:
            meta["created"] = metadata.created.strftime("%d/%m/%Y %H:%M")
        if metadata.modified:
            meta["modified"] = metadata.modified.strftime("%d/%m/%Y %H:%M")
    return meta


def check_tracking_on(doc: Document) -> bool:
    for p in doc.paragraphs:
        element = p._element
        for child in element.iterchildren():
            tag = child.tag
            if tag.endswith("}ins") or tag.endswith("}del"):
                return True
    return False


def check_title_case(text: str, ratio: float = 0.7) -> bool:
    if text:
        alphas = list(filter(str.isalpha, text))
        dividend = len(alphas)
        if dividend == 0:
            return False
        return (sum(map(str.isupper, text)) / dividend) > ratio
    return False


def get_page_size(section) -> str:
    width = round(section.page_width, -4)
    if width == round(Mm(210), -4):
        height = round(section.page_height, -4)
        if height == round(Mm(279.5), -4):
            return "JACoW"
        return "A4"
    elif width == round(Inches(8.5), -4):
        return "Letter"
    else:
        mm = round(round(width, -4) / 36000, 2)
        return f"Unknown page size with width {mm} mm"


def convert_twips_to_cm(twips: Any) -> float:
    width = Twips(int(twips))
    return round(width.mm / 10, 2)


def get_text(p: Paragraph) -> str:
    text = "".join([
        r.text.upper() if r.style and (r.style.font.all_caps or r.font.all_caps) else r.text
        for r in p.runs
    ])
    if p.style.font.all_caps or (p.style.base_style and p.style.base_style.font.all_caps):
        text = text.upper()
    return text


def get_paragraph_alignment(paragraph: Paragraph) -> Optional[str]:
    alignment = paragraph.style.paragraph_format.alignment
    if alignment is None and paragraph.style.base_style is not None and \
            paragraph.style.base_style.paragraph_format.alignment is not None:
        alignment = paragraph.style.base_style.paragraph_format.alignment

    if paragraph.alignment is not None:
        alignment = paragraph.alignment
    elif paragraph.paragraph_format.alignment is not None:
        alignment = paragraph.paragraph_format.alignment

    if alignment:
        return getattr(alignment, "name", getattr(alignment, "_member_name", str(alignment)))
    return None


def get_indents(style_format):
    first_line_indent, hanging_indent, left_indent = None, None, None
    for i in style_format.element.iterchildren():
        if isinstance(i, CT_PPr):
            for j in i.iterchildren():
                if isinstance(j, CT_Ind):
                    first_line_indent, hanging_indent, left_indent = j.firstLine, j.hanging, j.left
    return first_line_indent, hanging_indent, left_indent


def get_paragraph_space(paragraph: Paragraph):
    before = paragraph.style.paragraph_format.space_before
    after = paragraph.style.paragraph_format.space_after
    first_line_indent, hanging_indent, left_indent = get_indents(paragraph.style.paragraph_format)

    if paragraph.style.base_style is not None:
        first_line, hanging, left = get_indents(paragraph.style.base_style.paragraph_format)
        if before is None:
            before = paragraph.style.base_style.paragraph_format.space_before
        if after is None:
            after = paragraph.style.base_style.paragraph_format.space_after
        if first_line_indent is None:
            first_line_indent = first_line
        if hanging_indent is None:
            hanging_indent = hanging
        if left_indent is None:
            left_indent = left

    if paragraph.paragraph_format.space_before is not None:
        before = paragraph.paragraph_format.space_before
    if paragraph.paragraph_format.space_after is not None:
        after = paragraph.paragraph_format.space_after

    first_line, hanging, left = get_indents(paragraph.paragraph_format)
    if first_line is not None:
        first_line_indent = first_line
    if hanging is not None:
        hanging_indent = hanging
    if left is not None:
        left_indent = left

    if before:
        before = before.pt
    if after:
        after = after.pt
    if first_line_indent:
        first_line_indent = first_line_indent.pt
    elif hanging_indent:
        first_line_indent = -hanging_indent.pt
    if hanging_indent:
        hanging_indent = hanging_indent.pt
    if left_indent:
        left_indent = left_indent.pt

    return before, after, first_line_indent, hanging_indent, left_indent


def get_style_font_run(run):
    style = run.style
    bold, italic, font_size, font_name, all_caps = (
        style.font.bold,
        style.font.italic,
        style.font.size,
        style.font.name,
        style.font.all_caps,
    )
    if run.style.base_style is not None:
        style = run.style.base_style
        if font_size is None:
            font_size = style.font.size
        if font_name is None:
            font_name = style.font.name
        if bold is None:
            bold = style.font.bold
        if italic is None:
            italic = style.font.italic
        if all_caps is None:
            all_caps = style.font.all_caps

    if font_name is None:
        font_name = run.font.name
    if font_size is None:
        font_size = run.font.size
    if font_size is not None:
        font_size = font_size.pt

    return bold, italic, font_size, font_name, all_caps


def get_style_font(paragraph: Paragraph, url: Optional[Dict[str, Any]] = None):
    url = url or {}
    style = paragraph.style
    bold, italic, font_size, font_name, all_caps = (
        style.font.bold,
        style.font.italic,
        style.font.size,
        style.font.name,
        style.font.all_caps,
    )
    if paragraph.style.base_style is not None:
        style = paragraph.style.base_style
        if font_size is None:
            font_size = style.font.size
        if font_name is None:
            font_name = style.font.name
        if bold is None:
            bold = style.font.bold
        if italic is None:
            italic = style.font.italic
        if all_caps is None:
            all_caps = style.font.all_caps

    sections = paragraph.runs if isinstance(paragraph, Paragraph) else [paragraph]

    for r in sections:
        text = r.text.strip()
        if not text:
            continue

        if url.get("has_url"):
            found = any(text.startswith(s) for s in url.get("starts", []))
            if found:
                continue

        if r.font is not None:
            if r.font.size is not None:
                font_size = r.font.size
            if r.font.name is not None:
                font_name = r.font.name
            if r.font.bold is not None:
                bold = r.font.bold
            if r.font.italic is not None:
                italic = r.font.italic
            if r.font.all_caps is not None:
                all_caps = r.font.all_caps
        if r.bold is not None:
            bold = r.bold
        if r.italic is not None:
            italic = r.italic

    if not font_size:
        font_size = 10.0
    else:
        font_size = font_size.pt

    if not font_name:
        font_name = "Times new Roman"

    return bold, italic, font_size, font_name, all_caps


def get_style_details(p: Paragraph, url: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    space_before, space_after, first_line_indent, hanging_indent, left_indent = get_paragraph_space(p)
    bold, italic, font_size, font_name, all_caps = get_style_font(p, url or {})
    alignment = get_paragraph_alignment(p)
    return {
        "space_before": space_before,
        "space_after": space_after,
        "first_line_indent": first_line_indent,
        "hanging_indent": hanging_indent,
        "left_indent": left_indent,
        "bold": bold,
        "italic": italic,
        "font_size": font_size,
        "font_name": font_name,
        "all_caps": all_caps,
        "alignment": alignment,
    }


def get_compare(inp, relate, cut):
    ops = {
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "=": operator.eq,
    }
    return ops[relate](inp, cut)


def check_style(p: Paragraph, compare: Dict[str, Any], url: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
    detail = get_style_details(p, url)
    style_ok = True
    for key, value in compare.items():
        if key not in detail:
            continue
        elif key in ["space_before", "space_after"]:
            if isinstance(compare[key], list):
                result = detail[key] is not None and get_compare(detail[key], compare[key][0], compare[key][1])
                if not result:
                    detail[key] = f"{detail[key]} should be {' '.join(map(str, compare[key]))}"
            else:
                result = any([detail[key] == compare[key], detail[key] is None and compare[key] == 0.0])
                if not result:
                    detail[key] = f"{detail[key]} should be {compare[key]}"
        else:
            result = detail[key] == compare[key]
            if not result:
                detail[key] = f"{detail[key]} should be {compare[key]}"
        if not result:
            style_ok = False

    for key in list(detail.keys()):
        if key != "all_caps" and key not in compare:
            detail[key] = "NA"
    return style_ok, detail


def check_style_detail(p: Paragraph, compare: Dict[str, Any]) -> Dict[str, Any]:
    detail = get_style_details(p)
    style_ok = True
    for key, value in compare.items():
        if key not in detail:
            continue
        elif key in ["space_before", "space_after"]:
            if isinstance(compare[key], list):
                result = detail[key] is not None and get_compare(detail[key], compare[key][0], compare[key][1])
                if not result:
                    detail[key] = f"{detail[key]} should be {' '.join(map(str, compare[key]))}"
            else:
                result = any([detail[key] == compare[key], detail[key] is None and compare[key] == 0.0])
                if not result:
                    detail[key] = f"{detail[key]} should be {compare[key]}"
        else:
            if isinstance(compare[key], list):
                result = detail[key] in compare[key]
            else:
                result = detail[key] == compare[key]
            if not result:
                detail[key] = f"{detail[key]} should be {compare[key]}"
        if not result:
            style_ok = False
        detail["style_ok"] = style_ok

    for key in list(detail.keys()):
        if key not in ["all_caps", "style_ok"] and key not in compare:
            detail[key] = "NA"
    return detail


def to_element(p: Paragraph) -> "ElementContext":
    from ..engine.primitives import ElementContext
    return ElementContext(
        text=p.text.strip(),
        style_name=p.style.name if p.style else "",
        style_details=get_style_details(p),
        paragraph=p,
    )
