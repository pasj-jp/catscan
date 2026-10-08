import os
import json
import hashlib
from typing import Optional, Dict, Any

REPORTS_DIR = os.environ.get("REPORTS_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/reports")))
os.makedirs(REPORTS_DIR, exist_ok=True)


class ReportStore:
    """
    Local filesystem storage for paper validation reports.
    """

    @staticmethod
    def generate_report_id(content: Dict[str, Any]) -> str:
        serialized = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def save_report(report_data: Dict[str, Any], report_id: Optional[str] = None) -> str:
        if not report_id:
            report_id = ReportStore.generate_report_id(report_data)
        
        file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        return report_id

    @staticmethod
    def get_report(report_id: str) -> Optional[Dict[str, Any]]:
        clean_id = os.path.basename(report_id).replace(".json", "")
        file_path = os.path.join(REPORTS_DIR, f"{clean_id}.json")
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
