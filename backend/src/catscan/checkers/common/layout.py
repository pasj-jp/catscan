from typing import Any, Dict, List, Tuple
from docx.document import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from .docx_utils import get_page_size, convert_twips_to_cm


def check_margins_A4(section) -> bool:
    return get_margins_A4(section) == [37, 19, 20, 20]


def check_margins_JACoW(section) -> bool:
    return get_margins_JACoW(section) == [19, 19, 20, 20]


def check_margins_letter(section) -> bool:
    return get_margins_letter(section) == [0.75, 0.75, 0.79, 1.02]


def get_margins_A4(section) -> List[int]:
    return [
        round(section.top_margin.mm),
        round(section.bottom_margin.mm),
        round(section.left_margin.mm),
        round(section.right_margin.mm),
    ]


def get_margins_JACoW(section) -> List[int]:
    return [
        round(section.top_margin.mm),
        round(section.bottom_margin.mm),
        round(section.left_margin.mm),
        round(section.right_margin.mm),
    ]


def get_margins_letter(section) -> List[float]:
    return [
        round(section.top_margin.inches, 2),
        round(section.bottom_margin.inches, 2),
        round(section.left_margin.inches, 2),
        round(section.right_margin.inches, 2),
    ]


def get_margins(section) -> Any:
    page_size = get_page_size(section)
    if page_size == "A4":
        return get_margins_A4(section)
    elif page_size == "Letter":
        return get_margins_letter(section)
    elif page_size == "JACoW":
        return get_margins_JACoW(section)
    return None


def check_margins(section, require_a4: bool = False) -> bool:
    page_size = get_page_size(section)
    if require_a4:
        return page_size == "A4" and check_margins_A4(section)
    if page_size == "A4":
        return check_margins_A4(section)
    elif page_size == "Letter":
        return check_margins_letter(section)
    elif page_size == "JACoW":
        return check_margins_JACoW(section)
    return False


def get_columns(section, *, require_two_columns: bool = False, require_a4: bool = False) -> Tuple[int, float, bool]:
    cols = section._sectPr.find(qn("w:cols"))
    if cols is None:
        return 1, 0.0, not require_two_columns
    custom = cols.findall(qn("w:col")) if cols.get(qn("w:equalWidth")) in {"0", "false", "off"} else []
    num = len(custom) if custom else int(cols.get(qn("w:num"), "1"))
    space_twips = (custom[0] if custom else cols).get(qn("w:space"), "0")
    space = convert_twips_to_cm(space_twips)
    maximum_gutter = 0.52 if require_a4 else 0.54
    gutter_ok = 0.48 <= space <= maximum_gutter
    width_ok = not (require_a4 and require_two_columns and custom) or all(
        col.get(qn("w:w")) is not None and 8.23 <= convert_twips_to_cm(col.get(qn("w:w"))) <= 8.27
        for col in custom
    )
    ok = (num == 1 and not require_two_columns) or (num == 2 and gutter_ok and width_ok)
    return num, space, ok


def paragraph_sections(doc: Document, paragraphs: list[Paragraph]) -> set[int]:
    elements = {paragraph._p for paragraph in paragraphs}
    sections = set()
    index = 0
    for paragraph in doc.paragraphs:
        if paragraph._p in elements:
            sections.add(index)
        if paragraph._p.xpath("./w:pPr/w:sectPr"):
            index += 1
    return sections


def check_sections(
    doc, require_a4: bool = False, *, body_sections: set[int] | None = None
) -> List[Dict[str, Any]]:
    sections = []
    for index, section in enumerate(doc.sections):
        require_two_columns = body_sections is not None and index in body_sections
        cols = get_columns(section, require_two_columns=require_two_columns, require_a4=require_a4)
        sections.append({
            "page_size": get_page_size(section),
            "margins_ok": check_margins(section, require_a4=require_a4),
            "margins": get_margins(section),
            "col_number": cols[0],
            "col_gutter": cols[1],
            "col_ok": cols[2],
            **({"expected_columns": 2 if require_two_columns else None} if body_sections is not None else {}),
        })
    return sections
