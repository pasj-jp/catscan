from typing import Any

from ..checkers.registry import get_checker, detect_template, TEMPLATE_NAMES
from . import reports


def scan_document(
    data: bytes,
    filename: str,
    template: str = "auto",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc_type = "latex" if filename.lower().endswith(".tex") else "word"
    template = detect_template(data, doc_type) if template == "auto" else template
    result = get_checker(template, doc_type).check(data, filename)
    result.update({
        "report_type": doc_type,
        "detected_template": template,
        "template_name": TEMPLATE_NAMES.get(template, template),
        "filename": filename,
        **(extra or {}),
    })
    result["report_id"] = reports.save(result)
    return result
