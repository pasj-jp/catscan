from typing import Optional, TYPE_CHECKING
import httpx

if TYPE_CHECKING:
    from .engine import BibItem, Issue


def check_doi_online(item: "BibItem") -> Optional["Issue"]:
    """
    Check if DOI resolves via https://doi.org/.
    Only flags 404 Not Found (ignoring proxy restrictions, rate limits, or network timeouts).
    """
    from .engine import Issue

    doi = item.doi
    if not doi:
        return None
    try:
        with httpx.Client(timeout=3.0, follow_redirects=False) as client:
            res = client.head(f"https://doi.org/{doi}")
            if 200 <= res.status_code < 400:
                return None
            if res.status_code != 404:
                return None
            for char, issue_type in ((".", "DOI_ENDS_IN_PERIOD"), (")", "DOI_ENDS_IN_PARENTHESIS")):
                if doi.endswith(char):
                    trimmed = doi.rstrip(char)
                    trim_res = client.head(f"https://doi.org/{trimmed}")
                    if 200 <= trim_res.status_code < 400:
                        return Issue(name=item.name, issue_type=issue_type, location=item.location, suggestion=trimmed)
            return Issue(name=item.name, issue_type="DOI_NOT_FOUND", location=item.location)
    except httpx.HTTPError:
        return None
