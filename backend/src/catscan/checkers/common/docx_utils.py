import io
import operator
import re
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Twips
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
    if section.page_width is None or section.page_height is None:
        return "Page dimensions unavailable"
    width, height = section.page_width.mm, section.page_height.mm
    # Word templates round these dimensions when storing them in twips.
    for name, expected_width, expected_height in (
        ("A4", 210, 297), ("JACoW", 210, 279.5), ("Letter", 215.9, 279.4)
    ):
        if abs(width - expected_width) <= 0.15 and abs(height - expected_height) <= 0.15:
            return name
    return f"{round(width, 2):g} × {round(height, 2):g} mm"


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
    alignment = paragraph.alignment
    for style in _style_chain(paragraph.style):
        if alignment is not None:
            break
        alignment = style.paragraph_format.alignment
    return alignment.name if alignment is not None else None


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


_EAST_ASIAN = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uff00-\uffef]")


def _style_chain(style):
    seen = set()
    while style is not None and style.style_id not in seen:
        seen.add(style.style_id)
        yield style
        style = style.base_style


def _style_run_properties(style):
    return [base.element.rPr for base in _style_chain(style) if base.element.rPr is not None]


def get_effective_runs(paragraph: Paragraph):
    """Yield the effective typography of each visible run and script."""
    defaults = paragraph.part.styles.element.xpath("./w:docDefaults/w:rPrDefault/w:rPr")
    paragraph_properties = [*_style_run_properties(paragraph.style), *defaults]
    for run in paragraph.iter_inner_content():
        runs = run.runs if hasattr(run, "runs") else [run]
        for text_run in runs:
            text = text_run.text.strip()
            if not text:
                continue
            properties = [
                text_run.element.rPr,
                *_style_run_properties(text_run.style),
                *paragraph_properties,
            ]
            properties = [prop for prop in properties if prop is not None]

            def first_value(tag, attr="val", default=None):
                for prop in properties:
                    child = prop.find(qn(f"w:{tag}"))
                    if child is not None and (value := child.get(qn(f"w:{attr}"), default)) is not None:
                        return value
                return None

            latin = _EAST_ASIAN.sub("", text).strip()
            east_asian = _EAST_ASIAN.search(text)
            latin_font = first_value("rFonts", "ascii") or first_value("rFonts", "hAnsi")
            east_asian_font = first_value("rFonts", "eastAsia") or latin_font
            names = [font for present, font in ((latin, latin_font), (east_asian, east_asian_font)) if present]
            yield text, {
                "font_names": list(dict.fromkeys(names)),
                "font_size": float(first_value("sz") or 20) / 2,
                "bold": first_value("b", default="1") in {"1", "true", "on"},
                "italic": first_value("i", default="1") in {"1", "true", "on"},
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


def check_style(
    p: Paragraph, compare: Dict[str, Any], url: Optional[Dict[str, Any]] = None,
    *, each_run_size: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    detail = get_style_details(p, url)
    style_ok = True
    if each_run_size and "font_size" in compare:
        sizes = {font["font_size"] for _, font in get_effective_runs(p)}
        wrong_sizes = sizes - {compare["font_size"]}
        if wrong_sizes:
            detail["font_size"] = ", ".join(f"{size:g} pt" for size in sorted(wrong_sizes))
        elif sizes:
            detail["font_size"] = compare["font_size"]

    for key, actual in detail.items():
        if key not in compare:
            if key != "all_caps":
                detail[key] = "NA"
            continue
        expected = compare[key]
        if key in {"space_before", "space_after"} and isinstance(expected, list):
            relation, bound = expected
            matches = actual is not None and get_compare(actual, relation, bound)
            expected = f"{relation} {bound}"
        elif isinstance(expected, list):
            matches = actual in expected
        else:
            matches = actual == expected or (
                key in {"space_before", "space_after"} and actual is None and expected == 0
            )
        if not matches:
            style_ok = False
            detail[key] = f"{actual} should be {expected}"

    return style_ok, detail


def check_style_detail(p: Paragraph, compare: Dict[str, Any], *, each_run_size: bool = False) -> Dict[str, Any]:
    style_ok, detail = check_style(p, compare, each_run_size=each_run_size)
    return {"style_ok": style_ok, **detail}


def to_element(p: Paragraph) -> "ElementContext":
    from ..engine.primitives import ElementContext
    return ElementContext(
        text=p.text.strip(),
        style_name=p.style.name if p.style else "",
        style_details=get_style_details(p),
        paragraph=p,
    )
