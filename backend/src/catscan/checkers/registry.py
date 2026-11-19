import io
import re
from docx import Document

from .base import Checker
from .latex.engine import RuleBasedLatexChecker, decode_tex_bytes
from ..settings import get_settings

TEMPLATE_NAMES: dict[str, str] = {
    "jacow": "JACoW 英文原稿",
    "pasj": "PASJ 和文原稿",
}

CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9faf]")


def detect_template(data: bytes, doc_type: str = "word") -> str:
    if doc_type == "latex":
        text = decode_tex_bytes(data)
        if re.search(r"\\documentclass(?:\s*\[[^\]]*\])?\s*\{[^}]*pasj", text, re.IGNORECASE):
            return "pasj"
        if "\\jtitle" in text or "\\jauthor" in text:
            return "pasj"
        if CJK_RE.search(text[:2000]):
            return "pasj"
        return "jacow"

    doc = Document(io.BytesIO(data))
    styles = [s.name.lower() for s in doc.styles if s.name]
    has_pasj = any("pasj" in s for s in styles)
    has_jacow = any("jacow" in s for s in styles)

    if has_pasj and not has_jacow:
        return "pasj"
    if has_jacow and not has_pasj:
        return "jacow"

    sample_text = " ".join(p.text for p in doc.paragraphs[:15])
    if CJK_RE.search(sample_text):
        return "pasj"
    return "jacow"


def detect_latex_template(data: bytes | str) -> str:
    raw_bytes = data if isinstance(data, bytes) else data.encode("utf-8")
    return detect_template(raw_bytes, "latex")


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


def get_checker(template: str, doc_type: str = "word") -> Checker:
    global _CHECKERS
    if _CHECKERS is None:
        _CHECKERS = _build_checkers()
    key = (template.lower(), doc_type.lower())
    if key not in _CHECKERS:
        raise ValueError(f"No checker registered for template '{template}' and doc_type '{doc_type}'")
    return _CHECKERS[key]
