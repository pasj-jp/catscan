import re
from collections import Counter
from typing import TYPE_CHECKING, Literal, overload

from docx.document import Document

from .base import Checker
from .common.docx_utils import open_docx
from .latex.engine import RuleBasedLatexChecker, decode_tex_bytes
from .latex.project import DOCUMENT_CLASS, active_tex
from ..errors import DocumentError
from ..settings import get_settings

if TYPE_CHECKING:
    from .jacow.word_checker import JacowWordChecker
    from .pasj.word_checker import PasjWordChecker

TEMPLATE_NAMES: dict[str, str] = {
    "jacow": "JACoW 英文原稿",
    "pasj": "PASJ 和文原稿",
}

CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9faf]")


def detect_template(data: bytes, doc_type: str = "word", *, allow_language_fallback: bool = True) -> str | None:
    if doc_type == "latex":
        return detect_latex_source(decode_tex_bytes(data), allow_language_fallback=allow_language_fallback)

    return detect_word_template(open_docx(data), allow_language_fallback=allow_language_fallback)


def detect_word_template(doc: Document, *, allow_language_fallback: bool = True) -> str | None:
    paragraphs = [p for p in doc.paragraphs if p.text.strip()]
    style_counts: Counter[str] = Counter()
    title_templates: set[str] = set()
    for paragraph in paragraphs:
        style = paragraph.style.name.casefold()
        if re.match(r"^(?:\d+\)\s*)?pasj[-_ ]", style):
            style_counts["pasj"] += 1
            if "タイトル" in style and style.startswith(("011)", "012)")):
                title_templates.add("pasj")
        elif re.match(r"^jacow[-_ ]", style):
            style_counts["jacow"] += 1
            if "paper title" in style:
                title_templates.add("jacow")

    if len(title_templates) > 1 or (
        not title_templates and style_counts["pasj"] == style_counts["jacow"] > 0
    ):
        if allow_language_fallback:
            raise DocumentError("Both PASJ and JACoW paragraph styles are in use. Select the intended template and scan again.")
        return None
    if title_templates:
        return next(iter(title_templates))
    if style_counts:
        return style_counts.most_common(1)[0][0]

    if not allow_language_fallback:
        return None
    sample_text = " ".join(p.text for p in paragraphs[:15])
    return "pasj" if CJK_RE.search(sample_text) else "jacow"


def detect_latex_source(text: str, *, allow_language_fallback: bool = True) -> str | None:
    visible = active_tex(text)
    document_class = re.search(DOCUMENT_CLASS, visible)
    if document_class:
        class_name = document_class["class_name"].strip().casefold()
        if re.fullmatch(r"pasj(?:[-_]?\d{4})?", class_name):
            return "pasj"
        if re.fullmatch(r"jacow(?:[-_]?\d{4})?", class_name):
            return "jacow"
    if re.search(r"\\(?:jtitle|jauthor)\b", visible):
        return "pasj"
    if not allow_language_fallback:
        return None
    return "pasj" if CJK_RE.search(visible[:2000]) else "jacow"


def detect_latex_template(data: bytes | str) -> str:
    raw_bytes = data if isinstance(data, bytes) else data.encode("utf-8")
    return detect_template(raw_bytes, "latex") or "jacow"


def _build_checkers() -> dict[tuple[str, str], Checker]:
    from .jacow.word_checker import JacowWordChecker
    from .pasj.word_checker import PasjWordChecker

    settings = get_settings()
    return {
        ("jacow", "word"): JacowWordChecker(),
        ("pasj", "word"): PasjWordChecker(),
        ("jacow", "latex"): RuleBasedLatexChecker("jacow_latex", check_online_dois=settings.check_online_dois),
        ("pasj", "latex"): RuleBasedLatexChecker("pasj_latex", check_online_dois=settings.check_online_dois),
    }


_CHECKERS: dict[tuple[str, str], Checker] | None = None


@overload
def get_checker(template: str, doc_type: Literal["latex"]) -> RuleBasedLatexChecker: ...


@overload
def get_checker(template: str, doc_type: Literal["word"] = "word") -> "JacowWordChecker | PasjWordChecker": ...


@overload
def get_checker(template: str, doc_type: str) -> Checker: ...


def get_checker(template: str, doc_type: str = "word") -> Checker:
    global _CHECKERS
    if _CHECKERS is None:
        _CHECKERS = _build_checkers()
    key = (template.lower(), doc_type.lower())
    if key not in _CHECKERS:
        raise ValueError(f"No checker registered for template '{template}' and doc_type '{doc_type}'")
    return _CHECKERS[key]
