import io
import re
from typing import Optional, Union
from docx import Document

from .base import BasePaperChecker
from .jacow.word_checker import JacowWordChecker
from .jacow.latex_checker import JacowLatexChecker
from .pasj.word_checker import PasjWordChecker
from .pasj.latex_checker import PasjLatexChecker


def detect_template(file_source: Union[bytes, str, io.BytesIO]) -> str:
    """
    Auto-detect whether the document is based on PASJ or JACoW template.
    Checks styles, typography, and linguistic characteristics.
    """
    try:
        if isinstance(file_source, bytes):
            bio = io.BytesIO(file_source)
        elif isinstance(file_source, str):
            with open(file_source, "rb") as f:
                bio = io.BytesIO(f.read())
        else:
            bio = file_source

        # Read docx
        doc = Document(bio)
        styles = [s.name.lower() for s in doc.styles if s.name]
        has_pasj = any("pasj" in s for s in styles)
        has_jacow = any("jacow" in s for s in styles)

        if has_pasj and not has_jacow:
            return "pasj"
        elif has_jacow and not has_pasj:
            return "jacow"

        # Check paragraph text for Japanese characters (hiragana / katakana)
        sample_text = " ".join(p.text for p in doc.paragraphs[:15])
        if re.search(r'[\u3040-\u30ff]', sample_text):
            return "pasj"

        return "jacow"
    except Exception:
        return "jacow"


def get_checker(doc_type: str = "word", template: str = "auto", file_source: Optional[Union[bytes, str, io.BytesIO]] = None) -> tuple[BasePaperChecker, str]:
    """
    Factory method to retrieve the appropriate document checker.
    :param doc_type: 'word' or 'latex'
    :param template: 'auto', 'jacow', or 'pasj'
    :param file_source: Optional file source used for auto-detection
    :return: (checker_instance, effective_template)
    """
    doc_type = doc_type.lower()
    template = template.lower()

    if doc_type == "latex":
        if template == "pasj":
            return PasjLatexChecker(), "pasj"
        return JacowLatexChecker(), "jacow"

    if template == "auto" and file_source is not None:
        template = detect_template(file_source)
    elif template == "auto":
        template = "jacow"

    if doc_type == "word":
        if template == "pasj":
            return PasjWordChecker(), "pasj"
        return JacowWordChecker(), "jacow"

    raise ValueError(f"Unsupported document type: {doc_type}")
