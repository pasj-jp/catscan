import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    indico_base_url: str
    indico_api_token: str
    indico_timeout: float
    catscan_base_url: str
    reports_dir: Path
    rules_dir: Path
    check_online_dois: bool


@cache
def get_settings() -> Settings:
    backend_root = Path(__file__).resolve().parent.parent.parent
    default_reports_dir = backend_root / "data" / "reports"
    default_rules_dir = Path(__file__).resolve().parent / "checkers" / "rules"

    reports_env = os.environ.get("REPORTS_DIR")
    rules_env = os.environ.get("CATSCAN_RULES_DIR")
    doi_env = os.environ.get("CATSCAN_CHECK_DOI", "false").lower() in ("true", "1")

    return Settings(
        indico_base_url=os.environ.get("INDICO_BASE_URL", "http://localhost:8080").rstrip("/"),
        indico_api_token=os.environ.get("INDICO_API_TOKEN", ""),
        indico_timeout=float(os.environ.get("INDICO_TIMEOUT", "30.0")),
        catscan_base_url=os.environ.get("CATSCAN_BASE_URL", "http://localhost:3000").rstrip("/"),
        reports_dir=Path(reports_env) if reports_env else default_reports_dir,
        rules_dir=Path(rules_env) if rules_env else default_rules_dir,
        check_online_dois=doi_env,
    )
