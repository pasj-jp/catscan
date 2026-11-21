"""
Atomic check primitives for document style and content verification.

Each primitive performs a single focused verification on an Element.
Primitives return a CheckResult (or boolean) indicating whether the check passed.
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from ..common.docx_utils import check_title_case, get_effective_runs

# Default regex for Japanese characters (Hiragana, Katakana, Kanji)
DEFAULT_CJK_PATTERN = re.compile(r'[\u3040-\u30ff\u4e00-\u9faf]')

PRIMITIVES: Dict[str, Callable] = {}


def register_primitive(name: str):
    """Decorator to register a check primitive."""
    def decorator(fn: Callable):
        PRIMITIVES[name] = fn
        return fn
    return decorator


@dataclass
class ElementContext:
    text: str
    style_name: str
    style_details: Dict[str, Any]
    paragraph: Optional[Any] = None


@register_primitive("style_contains")
def check_style_contains(element: ElementContext, contains: List[str], **kwargs) -> bool:
    """Check if the element's style name contains any of the specified substrings."""
    style_name = element.style_name or ""
    return any(sub in style_name for sub in contains)


@register_primitive("style_in")
def check_style_in(element: ElementContext, styles: List[str], **kwargs) -> bool:
    """Check if the element's style name matches any in the list exactly."""
    return (element.style_name or "") in styles


@register_primitive("has_cjk")
def check_has_cjk(element: ElementContext, pattern: Optional[str] = None, **kwargs) -> bool:
    """Check if the element text contains Japanese/CJK characters."""
    pat = re.compile(pattern) if pattern else DEFAULT_CJK_PATTERN
    return bool(pat.search(element.text))


@register_primitive("no_cjk")
def check_no_cjk(element: ElementContext, pattern: Optional[str] = None, **kwargs) -> bool:
    """Check that the element text contains NO Japanese/CJK characters."""
    pat = re.compile(pattern) if pattern else DEFAULT_CJK_PATTERN
    return not bool(pat.search(element.text))


@register_primitive("forbid_chars")
def check_forbid_chars(element: ElementContext, chars: List[str], **kwargs) -> bool:
    """Check that none of the forbidden characters are present in the text."""
    text = element.text or ""
    return not any(char in text for char in chars)


@register_primitive("uppercase")
def check_uppercase(
    element: ElementContext,
    threshold: float = 0.7,
    allow_all_caps_style: bool = True,
    **kwargs
) -> bool:
    """Check if the text is uppercase (either via all_caps style format or character ratio)."""
    if allow_all_caps_style and bool(element.style_details.get("all_caps")):
        return True
    return check_title_case(element.text, threshold)


@register_primitive("font")
def check_font(element: ElementContext, **kwargs) -> bool:
    return not font_problems(element, **kwargs)


def _font_family(name: str) -> str:
    return "".join(unicodedata.normalize("NFKC", name).casefold().split())


def font_problems(
    element: ElementContext,
    name: Optional[Union[str, List[str]]] = None,
    size: Optional[float] = None,
    size_tolerance: float = 0.5,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    alignment: Optional[str] = None,
    space_before: Optional[float] = None,
    space_after: Optional[float] = None,
    **kwargs
) -> List[str]:
    """Report mismatches in visible text runs and paragraph formatting."""
    st = element.style_details or {}
    problems: List[str] = []
    names = [name] if isinstance(name, str) else name or []
    expected_names = {_font_family(font) for font in names}
    runs = list(get_effective_runs(element.paragraph)) if element.paragraph is not None else []
    if not runs:
        runs = [(element.text, {**st, "font_names": [st.get("font_name")]})]
    for text, formatting in runs:
        actual_fonts = formatting["font_names"]
        actual_size = formatting.get("font_size")
        mismatches = []
        if expected_names and any(not font or _font_family(font) not in expected_names for font in actual_fonts):
            mismatches.append(f"{', '.join(font or '?' for font in actual_fonts)} → {' / '.join(names)}")
        if size is not None and (actual_size is None or abs(float(actual_size) - size) > size_tolerance):
            actual = f"{actual_size:g} pt" if actual_size is not None else "?"
            mismatches.append(f"{actual} → {size:g} pt")
        if bold is not None and bool(formatting.get("bold")) != bold:
            mismatches.append("太字にしてください" if bold else "太字を解除してください")
        if italic is not None and bool(formatting.get("italic")) != italic:
            mismatches.append("斜体にしてください" if italic else "斜体を解除してください")
        if mismatches:
            snippet = text[:32] + ("…" if len(text) > 32 else "")
            problem = f"「{snippet}」 {'、'.join(mismatches)}"
            if problem not in problems:
                problems.append(problem)
            if len(problems) == 3:
                break
    if alignment is not None:
        actual_align = str(st.get("alignment") or "").upper()
        if actual_align != alignment.upper():
            problems.append(f"配置 {actual_align or '?'} → {alignment}")

    if space_before is not None:
        actual_sb = st.get("space_before")
        if actual_sb is not None and abs(float(actual_sb) - space_before) > 1.0:
            problems.append(f"段落前 {actual_sb:g} pt → {space_before:g} pt")

    if space_after is not None:
        actual_sa = st.get("space_after")
        if actual_sa is not None and abs(float(actual_sa) - space_after) > 1.0:
            problems.append(f"段落後 {actual_sa:g} pt → {space_after:g} pt")

    return problems


@register_primitive("regex_match")
def check_regex_match(element: ElementContext, pattern: str, flags: int = 0, **kwargs) -> bool:
    """Check if element text matches the regular expression pattern."""
    return bool(re.search(pattern, element.text.strip(), flags))


@register_primitive("regex_not_match")
def check_regex_not_match(element: ElementContext, pattern: str, flags: int = re.IGNORECASE, **kwargs) -> bool:
    """Check that element text does NOT match the regular expression pattern."""
    return not bool(re.search(pattern, element.text.strip(), flags))


@register_primitive("exact_text")
def check_exact_text(element: ElementContext, text: str, **kwargs) -> bool:
    """Check if element text strictly matches expected text."""
    return element.text.strip() == text.strip()


@register_primitive("ends_with_period_or_note")
def check_ends_with_period_or_note(element: ElementContext, **kwargs) -> bool:
    """Check if figure caption ends with a period, or a period with parenthesized note."""
    t = element.text.strip()
    if t.endswith("."):
        return True
    if re.search(r'\.\s*\([^)]+\)\s*$', t):
        return True
    return False


def get_primitive(name: str) -> Optional[Callable]:
    return PRIMITIVES.get(name)

