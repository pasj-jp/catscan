import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from .config import IndicoConfig

logger = logging.getLogger("catscan.indico.client")


class IndicoAPIError(Exception):
    """Raised when an API request to Indico fails."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class IndicoClient:
    """HTTP client for interacting with Indico paper editing and timeline APIs."""

    def __init__(self, config: Optional[IndicoConfig] = None):
        self.config = config or IndicoConfig.get_default()
        self.base_url = self.config.base_url.rstrip("/")
        self.api_token = self.config.api_token
        self.timeout = self.config.timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }
        # If accessing via IP or localhost, ensure Host header matches Indico BASE_URL if needed
        parsed = urlparse(self.base_url)
        if parsed.netloc:
            headers["Host"] = parsed.netloc
        return headers

    def get_papers(self, event_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all paper contributions for a conference event.
        GET /event/{event_id}/editing/api/paper/list
        """
        url = f"{self.base_url}/event/{event_id}/editing/api/paper/list"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._get_headers())
            if resp.status_code != 200:
                raise IndicoAPIError(
                    f"Failed to fetch papers for event {event_id}: HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    response_text=resp.text,
                )
            return resp.json()

    def get_contribution_paper(self, event_id: int, contribution_id: int) -> Dict[str, Any]:
        """
        Fetch editable details, revision history, and submitted files for a contribution.
        GET /event/{event_id}/api/contributions/{contribution_id}/editing/paper
        """
        url = f"{self.base_url}/event/{event_id}/api/contributions/{contribution_id}/editing/paper"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._get_headers())
            if resp.status_code != 200:
                raise IndicoAPIError(
                    f"Failed to fetch paper for event {event_id}, contribution {contribution_id}: HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    response_text=resp.text,
                )
            return resp.json()

    def download_file(self, download_url: str) -> bytes:
        """
        Download a file from Indico using the configured Bearer token.
        Supports both relative download paths and absolute URLs.
        """
        if download_url.startswith("http://") or download_url.startswith("https://"):
            url = download_url
        else:
            url = f"{self.base_url}{download_url}"

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._get_headers())
            if resp.status_code != 200:
                raise IndicoAPIError(
                    f"Failed to download file from {url}: HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    response_text=resp.text[:500],
                )
            return resp.content

    def create_comment(
        self,
        event_id: int,
        contribution_id: int,
        revision_id: int,
        text: str,
        internal: bool = False,
    ) -> bool:
        """
        Post a Markdown comment to an editing revision timeline.
        POST /event/{event_id}/api/contributions/{contribution_id}/editing/paper/{revision_id}/comments/
        """
        url = f"{self.base_url}/event/{event_id}/api/contributions/{contribution_id}/editing/paper/{revision_id}/comments/"
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        payload = {
            "text": text,
            "internal": internal,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                raise IndicoAPIError(
                    f"Failed to post comment to revision {revision_id}: HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    response_text=resp.text,
                )
            return True
