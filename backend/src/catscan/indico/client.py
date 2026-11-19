import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from ..settings import get_settings
from ..errors import IndicoAPIError

logger = logging.getLogger("catscan.indico.client")


class IndicoClient:
    """HTTP client for interacting with Indico paper editing and timeline APIs."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.indico_base_url).rstrip("/")
        self.api_token = api_token if api_token is not None else settings.indico_api_token
        self.timeout = timeout if timeout is not None else settings.indico_timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            },
            timeout=self.timeout,
            follow_redirects=True,
        )

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }
        parsed = urlparse(self.base_url)
        if parsed.netloc:
            headers["Host"] = parsed.netloc
        return headers

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as e:
            raise IndicoAPIError(f"HTTP request failed for {method} {path}: {e}") from e
        if not resp.is_success:
            raise IndicoAPIError(
                f"Indico API error for {method} {path}: HTTP {resp.status_code}",
                status_code=resp.status_code,
            )
        return resp

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_papers(self, event_id: int) -> List[Dict[str, Any]]:
        return self._request("GET", f"/event/{event_id}/editing/api/paper/list").json()

    def get_contribution_paper(self, event_id: int, contribution_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/event/{event_id}/api/contributions/{contribution_id}/editing/paper").json()

    def download_file(self, download_url: str) -> bytes:
        return self._request("GET", download_url).content

    def create_comment(
        self,
        event_id: int,
        contribution_id: int,
        revision_id: int,
        text: str,
        internal: bool = False,
    ) -> bool:
        self._request(
            "POST",
            f"/event/{event_id}/api/contributions/{contribution_id}/editing/paper/{revision_id}/comments/",
            json={"text": text, "internal": internal},
        )
        return True
