"""
Atomic check primitives for document style and content verification.

Each primitive performs a single focused verification on an Element.
Primitives return a CheckResult (or boolean) indicating whether the check passed.
"""
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from ..jacow.page import check_title_case

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


@dataclass
class CheckResult:
    passed: bool
    fail_message: Optional[str] = None
    key: Optional[str] = None


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
def check_font(
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
) -> bool:
    """Verify font family, size with tolerance, formatting and alignment."""
    st = element.style_details or {}

    if name is not None:
        expected_names = [name] if isinstance(name, str) else list(name)
        actual_name = st.get("font_name") or ""
        if not any(exp.lower() in actual_name.lower() or actual_name.lower() in exp.lower() for exp in expected_names):
            return False

    if size is not None:
        actual_size = st.get("font_size")
        if actual_size is None or abs(float(actual_size) - size) > size_tolerance:
            return False

    if bold is not None:
        if bool(st.get("bold")) != bold:
            return False

    if italic is not None:
        if bool(st.get("italic")) != italic:
            return False

    if alignment is not None:
        actual_align = str(st.get("alignment") or "").upper()
        if actual_align != alignment.upper():
            return False

    if space_before is not None:
        actual_sb = st.get("space_before")
        if actual_sb is not None and abs(float(actual_sb) - space_before) > 1.0:
            return False

    if space_after is not None:
        actual_sa = st.get("space_after")
        if actual_sa is not None and abs(float(actual_sa) - space_after) > 1.0:
            return False

    return True


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

