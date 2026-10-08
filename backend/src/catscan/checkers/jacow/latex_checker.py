import re
import io
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
import httpx

from ..base import BasePaperChecker

logger = logging.getLogger("catscan.latex")


@dataclass
class Location:
    start: int
    end: int


@dataclass
class BibItem:
    name: str
    ref_text: str
    original_text: str
    location: Location
    label_location: Location
    doi: Optional[str] = None


@dataclass
class Issue:
    name: str
    issue_type: str
    location: Location
    suggestion: Optional[str] = None


ISSUE_DESCRIPTIONS = {
    "INCORRECT_STYLE_REFERENCE": (
        "Reference does not appear to be in the JACoW style, please adjust your reference style "
        "to be consistent with the JACoW style reference, please see https://www.jacow.org/Authors/FormattingCitations"
    ),
    "ET_AL_WITH_COMMA": (
        "et al. is preceded by a comma, which is incorrect. Please remove the comma before the et al."
    ),
    "ET_AL_NOT_WRAPPED": (
        "et al. is not wrapped in a command to make it italic. Please use \\emph{et al.} instead of et al."
    ),
    "DOI_CONTAINS_SPACE": (
        "DOI contains a space after the colon. Please remove the space."
    ),
    "DOI_NOT_WRAPPED": (
        "DOI not wrapped in \\url{} command. Please use \\url{doi:10.18429/JACoW-IPAC2023-XXXX} "
        "instead of doi:10.18429/JACoW-IPAC2023-XXXX"
    ),
    "NO_DOI_PREFIX": (
        'DOI does not contain "doi:" prefix. It should appear like this \\url{doi:10.18429/JACoW-IPAC2023-XXXX}'
    ),
    "DOI_IS_URL": (
        "DOI is written as a web URL (including https://doi.org/) which is incorrect. "
        "Remove the https://doi.org/, and write it as per this example. \\url{doi:10.18429/JACoW-IPAC2023-XXXX}"
    ),
    "VOLUME_ISSUE": (
        "JACoW references use vol. X and no. X. You have used not Vol. X, Issue X, which is incorrect. "
        "Please correct your reference style. You can generate correctly formatted references at "
        "https://refs.jacow.org/ or you can refer to the JACoW reference style guide at "
        "https://www.jacow.org/Authors/FormattingCitations"
    ),
    "DOI_ENDS_IN_PERIOD": (
        "This DOI ends in a period, which is incorrect for this specific DOI. Please remove the period."
    ),
    "DOI_ENDS_IN_PARENTHESIS": (
        "DOI is wrapped in parenthesis, please remove these."
    ),
    "DOI_NOT_FOUND": (
        "DOI was checked, and does not appear to be valid. Please check if the DOI is correct."
    ),
}


class JacowLatexChecker(BasePaperChecker):
    """
    Pure Python implementation of the JACoW LaTeX paper format and reference validator.
    Inspects .tex source code for JACoW bibliography conventions, DOI formatting,
    and italicization rules without requiring an external TeX compiler or Go binary.
    """

    def __init__(self, check_online_dois: Optional[bool] = None):
        if check_online_dois is None:
            import os
            self.check_online_dois = os.environ.get("CATSCAN_CHECK_DOI", "false").lower() in ("true", "1")
        else:
            self.check_online_dois = check_online_dois

    def validate(

        self,
        file_source: Union[str, bytes, io.BytesIO],
        filename: str = "document.tex",
        conference_id: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Validate LaTeX content and return a report matching CatScan's structure.
        """
        if isinstance(file_source, bytes):
            content = file_source.decode("utf-8", errors="replace")
        elif isinstance(file_source, io.BytesIO):
            content = file_source.getvalue().decode("utf-8", errors="replace")
        elif isinstance(file_source, str):
            if "\n" not in file_source and (file_source.endswith(".tex") or "/" in file_source or "\\" in file_source):
                try:
                    with open(file_source, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    content = file_source
            else:
                content = file_source
        else:
            content = str(file_source)

        comments = self._find_comments(content)
        doc_bounds = self._find_document(content, comments)
        bib_items = self._find_bib_items(content, comments, doc_bounds)

        issues: List[Issue] = []
        for item in bib_items:
            issues.extend(self._check_bib_item(item))

        # Format output
        unabbreviated = ""
        issue_count = 0

        for issue in issues:
            desc = ISSUE_DESCRIPTIONS.get(issue.issue_type, "")
            if desc:
                issue_count += 1
                name = issue.name.strip()
                unabbreviated += f"\nIssue found in reference {name}: {desc}\n\n"

        output_body = unabbreviated.strip() if issue_count > 0 else "No issues found"

        return {
            "statusCode": 200,
            "filename": filename,
            "body": output_body,
            "isabbreviated": False,
            "issuesFound": issue_count,
            "unabbreviated": unabbreviated,
            "total_references": len(bib_items),
        }

    # ----------------- Parsing Helpers -----------------

    @staticmethod
    def _find_comments(content: str) -> List[Tuple[int, int]]:
        """
        Find all LaTeX comments (% until end of line), taking care of escaped \\%
        """
        comments: List[Tuple[int, int]] = []
        pattern = re.compile(r'(?<!\\)%.*?(?:\n|$)')
        for match in pattern.finditer(content):
            comments.append((match.start(), match.end()))
        return comments

    @staticmethod
    def _is_in_comments(pos: int, comments: List[Tuple[int, int]]) -> bool:
        for start, end in comments:
            if start <= pos < end:
                return True
        return False

    def _find_document(self, content: str, comments: List[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Locate \\begin{document} and \\end{document} positions.
        """
        doc_start = 0
        for m in re.finditer(r'\\begin\{document\}', content):
            if not self._is_in_comments(m.start(), comments):
                doc_start = m.start()
                break

        doc_end = len(content)
        for m in re.finditer(r'\\end\{document\}', content):
            if not self._is_in_comments(m.start(), comments):
                doc_end = m.start()
                break

        return doc_start, doc_end

    def _find_bib_items(
        self,
        content: str,
        comments: List[Tuple[int, int]],
        doc_bounds: Tuple[int, int]
    ) -> List[BibItem]:
        """
        Parse valid \\bibitem entries inside document bounds and outside comments.
        """
        doc_start, doc_end = doc_bounds
        pattern = re.compile(
            r'(\\bibitem(?:\[.*?\])?\{([^}]+)\})(.*?)(?=(\\bibitem|\\end\{thebibliography\}|\Z))',
            re.DOTALL
        )
        doi_pattern = re.compile(r'10\.\d{4,9}/[-._\\;()/:a-zA-Z0-9]+')

        items: List[BibItem] = []
        for match in pattern.finditer(content):
            full_label = match.group(1)
            name = match.group(2).strip()
            raw_text = match.group(3)
            label_start = match.start(1)

            # Skip if inside comments or outside document bounds
            if self._is_in_comments(label_start, comments):
                continue
            if not (doc_start <= label_start <= doc_end):
                continue

            # Remove comments from reference text
            clean_text = re.sub(r'(?<!\\)%.*?(?:\n|$)', ' ', raw_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            # Find last DOI in reference
            dois = doi_pattern.findall(clean_text)
            last_doi = dois[-1] if dois else None

            item = BibItem(
                name=name,
                ref_text=clean_text,
                original_text=raw_text,
                location=Location(match.start(3), match.end(3)),
                label_location=Location(match.start(1), match.end(1)),
                doi=last_doi
            )
            items.append(item)

        return items

    # ----------------- Rule Checkers -----------------

    def _check_bib_item(self, item: BibItem) -> List[Issue]:
        issues: List[Issue] = []

        # 1. et al. must be wrapped in italics (\emph{et al.} or \textit{et al.})
        if re.search(r'et\s+al\.', item.original_text, re.IGNORECASE):
            italic_pattern = re.compile(
                r'(\\emph\s*\{|\\textit\s*\{|\\it\s*\{|\\em\s*\{|\\itshape\s*\{|{\\it\s+|{\\em\s+|{\\itshape\s+)\s*et\s+al\.',
                re.IGNORECASE
            )
            if not italic_pattern.search(item.original_text):
                issues.append(Issue(
                    name=item.name,
                    issue_type="ET_AL_NOT_WRAPPED",
                    location=item.location
                ))

        # 2. DOI contains space after colon (e.g., "doi: 10.")
        if re.search(r'doi:\s+10\.', item.ref_text, re.IGNORECASE):
            issues.append(Issue(
                name=item.name,
                issue_type="DOI_CONTAINS_SPACE",
                location=item.location
            ))

        # 3. Non-JACoW reference styles (APS style or broken web styles)
        # APS style: \d+[, -]+?\d+ \(\d{4}\)
        # Broken style: : N. p., \d{4}. Web.
        if re.search(r'\d+[, -]+?\d+\s+\(\d{4}\)', item.ref_text) or re.search(r':\s*N\.\s*p\.,\s*\d{4}\.\s*Web\.', item.ref_text):
            issues.append(Issue(
                name=item.name,
                issue_type="INCORRECT_STYLE_REFERENCE",
                location=item.location
            ))

        # 4. Missing "doi:" prefix inside \url{} (e.g., \url{10.18429/...})
        if re.search(r'\\url\s*\{\s*10\.', item.ref_text):
            issues.append(Issue(
                name=item.name,
                issue_type="NO_DOI_PREFIX",
                location=item.location
            ))

        # 5. DOI written as full web URL (e.g., \url{https://doi.org/10.18429/...})
        if re.search(r'https?://(?:dx\.)?doi\.org', item.ref_text, re.IGNORECASE):
            issues.append(Issue(
                name=item.name,
                issue_type="DOI_IS_URL",
                location=item.location
            ))

        # 6. Incorrect Volume / Issue syntax (e.g. "Vol. 58, Issue 1," instead of "vol. 58, no. 1,")
        if re.search(r'Vol\.\s*\d+,\s*Issue\s*\d+,', item.ref_text):
            issues.append(Issue(
                name=item.name,
                issue_type="VOLUME_ISSUE",
                location=item.location
            ))

        # 7. Online DOI validity check
        if item.doi and self.check_online_dois:
            doi_issue = self._check_doi_online(item)
            if doi_issue:
                issues.append(doi_issue)

        return issues

    def _check_doi_online(self, item: BibItem) -> Optional[Issue]:
        """
        Check if DOI resolves via https://doi.org/.
        Only flags 404 Not Found (ignoring proxy restrictions, rate limits, or network timeouts).
        """
        doi = item.doi
        if not doi:
            return None

        lookup_url = f"https://doi.org/{doi}"
        try:
            with httpx.Client(timeout=3.0, follow_redirects=False) as client:
                res = client.head(lookup_url)
                if 200 <= res.status_code < 400:
                    return None

                # Only 404 indicates non-existent DOI; other codes (400, 403, 500) mean proxy/network block
                if res.status_code != 404:
                    return None

                # If 404, check if trimming trailing period helps
                if doi.endswith("."):
                    trimmed = doi.rstrip(".")
                    trim_res = client.head(f"https://doi.org/{trimmed}")
                    if 200 <= trim_res.status_code < 400:
                        return Issue(name=item.name, issue_type="DOI_ENDS_IN_PERIOD", location=item.location, suggestion=trimmed)

                # Check trailing parenthesis
                if doi.endswith(")"):
                    trimmed = doi.rstrip(")")
                    trim_res = client.head(f"https://doi.org/{trimmed}")
                    if 200 <= trim_res.status_code < 400:
                        return Issue(name=item.name, issue_type="DOI_ENDS_IN_PARENTHESIS", location=item.location, suggestion=trimmed)

                return Issue(name=item.name, issue_type="DOI_NOT_FOUND", location=item.location)
        except Exception:
            return None

