import os
from dataclasses import dataclass


@dataclass
class IndicoConfig:
    """Configuration for Indico API connection and CatScan callback links."""
    base_url: str = os.environ.get("INDICO_BASE_URL", "http://localhost:8080").rstrip("/")
    api_token: str = os.environ.get("INDICO_API_TOKEN", "")
    catscan_base_url: str = os.environ.get("CATSCAN_BASE_URL", "http://localhost:3000").rstrip("/")
    timeout: float = float(os.environ.get("INDICO_TIMEOUT", "30.0"))

    @classmethod
    def get_default(cls) -> "IndicoConfig":
        return cls()
