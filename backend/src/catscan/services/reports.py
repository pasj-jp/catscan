import json
import hashlib
import re
from pathlib import Path
from typing import Any

from ..checkers.common.diagnostics import localized_message
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
        return normalize_report(json.load(f))


def normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    """Adapt saved reports created before structured issues were required."""
    if "report_type" not in report:
        report["report_type"] = "word" if "summary" in report else "latex"
    if report["report_type"] != "latex":
        return report

    body = report.pop("unabbreviated", "") or report.get("body", "")
    report.pop("body", None)
    issue_count = report.pop("issuesFound", 0)
    report.pop("statusCode", None)
    report.pop("isabbreviated", None)

    if "issues" not in report:
        issues = []
        if issue_count:
            for block in body.strip().split("\n\n"):
                match = re.fullmatch(r"Issue found in\s+([^:]+):\s*(.*)", block.strip(), re.DOTALL)
                name, message = match.groups() if match else ("Issue", block)
                if message.strip():
                    issues.append({"name": name.strip(), "message": message})
        report["issues"] = issues

    for issue in report["issues"]:
        if "message_ja" not in issue:
            issue.update(localized_message(issue.get("message", "")))
    if "detected_template" not in report:
        source = f"{report.get('template_name', '')} {body}"
        report["detected_template"] = "pasj" if "PASJ" in source else "jacow"
    report.setdefault("coverage_notices", [])
    return report
