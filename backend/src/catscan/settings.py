import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


def _parse_cors_origins(raw: str | None, catscan_base_url: str) -> tuple[str, ...]:
    if raw is not None and raw.strip():
        return tuple(origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip())
    defaults = [catscan_base_url, "http://localhost:3000", "http://127.0.0.1:3000"]
    return tuple(dict.fromkeys(o for o in defaults if o))


@dataclass(frozen=True)
class Settings:
    indico_base_url: str
    indico_api_token: str
    indico_timeout: float
    catscan_base_url: str
    internal_api_token: str
    require_indico_auth: bool
    cors_origins: tuple[str, ...]
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
    doi_env = _parse_bool(os.environ.get("CATSCAN_CHECK_DOI"), default=False)
    catscan_base_url = os.environ.get("CATSCAN_BASE_URL", "http://localhost:3000").rstrip("/")

    return Settings(
        indico_base_url=os.environ.get("INDICO_BASE_URL", "http://localhost:8080").rstrip("/"),
        indico_api_token=os.environ.get("INDICO_API_TOKEN", ""),
        indico_timeout=float(os.environ.get("INDICO_TIMEOUT", "30.0")),
        catscan_base_url=catscan_base_url,
        internal_api_token=os.environ.get("CATSCAN_INTERNAL_TOKEN", ""),
        require_indico_auth=_parse_bool(os.environ.get("CATSCAN_REQUIRE_INDICO_AUTH"), default=True),
        cors_origins=_parse_cors_origins(os.environ.get("CATSCAN_CORS_ORIGINS"), catscan_base_url),
        reports_dir=Path(reports_env) if reports_env else default_reports_dir,
        rules_dir=Path(rules_env) if rules_env else default_rules_dir,
        check_online_dois=doi_env,
    )
