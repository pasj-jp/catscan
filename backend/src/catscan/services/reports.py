import json
import hashlib
from pathlib import Path
from typing import Any

from ..settings import get_settings
from ..errors import ReportNotFoundError


def generate_report_id(content: dict[str, Any]) -> str:
    serialized = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def save(report: dict[str, Any], report_id: str | None = None) -> str:
    settings = get_settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    if not report_id:
        report_id = generate_report_id(report)
    report["report_id"] = report_id
    file_path = settings.reports_dir / f"{report_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    return report_id


def load(report_id: str) -> dict[str, Any]:
    settings = get_settings()
    clean_id = Path(report_id).name.replace(".json", "")
    file_path = settings.reports_dir / f"{clean_id}.json"
    if not file_path.is_file():
        raise ReportNotFoundError(f"Report {report_id} not found")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
