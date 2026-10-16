"""
Generic, YAML-driven LaTeX source checker.

The rules (what to extract, which regex must / must not match, the messages)
live in ``rules/<name>.yaml``; this module only knows *how* to extract text
from a .tex file and evaluate those rules.
"""
import io
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import httpx

from .base import BasePaperChecker
from .rules import load_rules
from .rules.schema import LatexRule, LatexRules, LatexTarget

COMMENT_RE = re.compile(r'(?<!\\)%.*?(?:\n|$)')
BIBITEM_RE = re.compile(
    r'(\\bibitem(?:\[.*?\])?\{([^}]+)\})(.*?)(?=(\\bibitem|\\end\{thebibliography\}|\Z))',
    re.DOTALL,
)
DOI_RE = re.compile(r'10\.\d{4,9}/[-._\\;()/:a-zA-Z0-9]+')
# one level of nested braces inside the macro argument
MACRO_ARG = r'\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
CAPTION_RE = re.compile(r'\\caption' + MACRO_ARG, re.DOTALL)


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
    location: Optional[Location] = None
    suggestion: Optional[str] = None


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub(' ', text)


class LatexSource:
    """A .tex file plus the comment ranges needed for comment-aware searching."""

    def __init__(self, content: str):
        self.content = content
        self.comments: List[Tuple[int, int]] = [(m.start(), m.end()) for m in COMMENT_RE.finditer(content)]

    def in_comment(self, pos: int) -> bool:
        return any(start <= pos < end for start, end in self.comments)

    def search(self, pattern: str, flags: int = 0, ignore_comments: bool = True):
        for m in re.finditer(pattern, self.content, flags):
            if not ignore_comments or not self.in_comment(m.start()):
                return m
        return None

    def document_bounds(self) -> Tuple[int, int]:
        start = self.search(r'\\begin\{document\}')
        end = self.search(r'\\end\{document\}')
        return (start.start() if start else 0, end.start() if end else len(self.content))

    # ---- extraction ----

    def extract(self, target: LatexTarget) -> Optional[str]:
        if target.builtin == "body":
            text = self._body(target)
        elif target.regex:
            m = self.search(target.regex, ignore_comments=target.ignore_comments)
            text = m.group(1) if m else None
        else:
            names = "|".join(re.escape(n) for n in target.macros)
            m = self.search(r'\\(?:' + names + r')' + MACRO_ARG, ignore_comments=target.ignore_comments)
            if m:
                text = m.group(1)
            elif target.env:
                env = re.escape(target.env)
                m = self.search(r'\\begin\{' + env + r'\}(.*?)\\end\{' + env + r'\}', re.DOTALL,
                                ignore_comments=target.ignore_comments)
                text = m.group(1) if m else None
            else:
                text = None
        if text is not None and target.strip_comments:
            text = strip_comments(text)
        return text

    def _body(self, target: LatexTarget) -> str:
        """Body text without comments, math, or commands (between start/end markers)."""
        content = self.content
        m_start = re.search(target.start, content) if target.start else None
        m_end = re.search(target.end, content) if target.end else None
        raw = content[m_start.end() if m_start else 0: m_end.start() if m_end else len(content)]
        clean = strip_comments(raw)
        clean = re.sub(r'\$.*?\$', ' ', clean)
        clean = re.sub(r'\\\[.*?\\\]', ' ', clean, flags=re.DOTALL)
        clean = re.sub(r'\\begin\{equation\}.*?\\end\{equation\}', ' ', clean, flags=re.DOTALL)
        clean = re.sub(r'\\[a-zA-Z]+(?:\*|\b)(?:\[[^\]]*\])?(?:\{[^{}]*\})?', ' ', clean)
        return clean

    def captions(self, envs: List[str]) -> Iterator[str]:
        """First \\caption{...} of each listed environment, comments removed."""
        names = "|".join(re.escape(e) for e in envs)
        pattern = re.compile(r'\\begin\{(?:' + names + r')\}(.*?)\\end\{(?:' + names + r')\}', re.DOTALL)
        for m in pattern.finditer(self.content):
            if self.in_comment(m.start()):
                continue
            cap = CAPTION_RE.search(m.group(1))
            if cap:
                yield strip_comments(cap.group(1).strip()).strip()

    def bib_items(self) -> List[BibItem]:
        doc_start, doc_end = self.document_bounds()
        items: List[BibItem] = []
        for match in BIBITEM_RE.finditer(self.content):
            label_start = match.start(1)
            if self.in_comment(label_start) or not (doc_start <= label_start <= doc_end):
                continue
            raw_text = match.group(3)
            clean_text = re.sub(r'\s+', ' ', strip_comments(raw_text)).strip()
            dois = DOI_RE.findall(clean_text)
            items.append(BibItem(
                name=match.group(2).strip(),
                ref_text=clean_text,
                original_text=raw_text,
                location=Location(match.start(3), match.end(3)),
                label_location=Location(match.start(1), match.end(1)),
                doi=dois[-1] if dois else None,
            ))
        return items


def rule_fires(rule: LatexRule, value: Optional[str]) -> bool:
    """
    missing    -> fires when the target was not found
    when       -> precondition regex; the rule is skipped if it does not match
    match      -> fires when the regex is found
    not_match  -> fires when the regex is NOT found (empty text is skipped)
    """
    if value is None:
        return rule.missing
    flags = re.IGNORECASE if rule.ignore_case else 0
    if rule.when and not re.search(rule.when, value, flags):
        return False
    if rule.match and re.search(rule.match, value, flags):
        return True
    if rule.not_match and value.strip() and not re.search(rule.not_match, value, flags):
        return True
    return False


def read_tex(file_source: Union[str, bytes, io.BytesIO]) -> str:
    if isinstance(file_source, bytes):
        return file_source.decode("utf-8", errors="replace")
    if isinstance(file_source, io.BytesIO):
        return file_source.getvalue().decode("utf-8", errors="replace")
    if isinstance(file_source, str):
        if "\n" not in file_source and (file_source.endswith(".tex") or "/" in file_source or "\\" in file_source):
            try:
                with open(file_source, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception:
                return file_source
        return file_source
    return str(file_source)


class RuleBasedLatexChecker(BasePaperChecker):
    """LaTeX checker whose rules come from ``rules/<rules_name>.yaml``."""

    rules_name: str = ""

    def __init__(self, check_online_dois: bool = False):
        self.check_online_dois = check_online_dois

    @property
    def rules(self) -> LatexRules:
        return load_rules(self.rules_name, LatexRules)

    def find_issues(self, src: LatexSource, rules: LatexRules, bib_items: List[BibItem]) -> List[Issue]:
        issues: List[Issue] = []
        by_scope: Dict[str, List[LatexRule]] = {"document": [], "figure": [], "table": [], "bibitem": []}
        for rule in rules.rules:
            by_scope[rule.scope].append(rule)

        # 1. document-level rules, in file order
        values: Dict[str, Optional[str]] = {}
        for rule in by_scope["document"]:
            if rule.target not in values:
                values[rule.target] = src.extract(rules.targets[rule.target])
            if rule_fires(rule, values[rule.target]):
                issues.append(Issue(name=rule.name or rule.target, issue_type=rule.issue))

        # 2. captions (figures, then tables)
        for scope in ("figure", "table"):
            if not by_scope[scope]:
                continue
            cap_cfg = rules.captions[scope]
            for caption in src.captions(cap_cfg.envs):
                for rule in by_scope[scope]:
                    if rule_fires(rule, caption):
                        issues.append(Issue(name=rule.name or cap_cfg.name, issue_type=rule.issue))

        # 3. bibliography, item by item
        for item in bib_items:
            for rule in by_scope["bibitem"]:
                if rule.check == "doi_online":
                    if item.doi and self.check_online_dois:
                        issue = check_doi_online(item)
                        if issue:
                            issues.append(issue)
                    continue
                value = item.ref_text if rule.target == "text" else item.original_text
                if rule_fires(rule, value):
                    issues.append(Issue(name=rule.name or item.name, issue_type=rule.issue, location=item.location))
        return issues

    def validate(
        self,
        file_source: Union[str, bytes, io.BytesIO],
        filename: str = "document.tex",
        conference_id: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        rules = self.rules
        src = LatexSource(read_tex(file_source))
        bib_items = src.bib_items()
        issues = self.find_issues(src, rules, bib_items)

        unabbreviated = ""
        for issue in issues:
            message = rules.messages.get(issue.issue_type, issue.issue_type)
            line = rules.report.issue_format.format(name=issue.name.strip(), message=message)
            unabbreviated += f"\n{line}\n\n"

        result: Dict[str, Any] = {
            "statusCode": 200,
            "filename": filename,
            "body": unabbreviated.strip() if issues else "No issues found",
            "isabbreviated": False,
            "issuesFound": len(issues),
            "unabbreviated": unabbreviated,
            "total_references": len(bib_items),
        }
        result.update(rules.report.extra_output)
        return result


def check_doi_online(item: BibItem) -> Optional[Issue]:
    """
    Check if DOI resolves via https://doi.org/.
    Only flags 404 Not Found (ignoring proxy restrictions, rate limits, or network timeouts).
    """
    doi = item.doi
    if not doi:
        return None
    try:
        with httpx.Client(timeout=3.0, follow_redirects=False) as client:
            res = client.head(f"https://doi.org/{doi}")
            if 200 <= res.status_code < 400:
                return None
            # Only 404 indicates non-existent DOI; other codes (400, 403, 500) mean proxy/network block
            if res.status_code != 404:
                return None
            # If 404, check if trimming trailing period / parenthesis helps
            for char, issue_type in ((".", "DOI_ENDS_IN_PERIOD"), (")", "DOI_ENDS_IN_PARENTHESIS")):
                if doi.endswith(char):
                    trimmed = doi.rstrip(char)
                    trim_res = client.head(f"https://doi.org/{trimmed}")
                    if 200 <= trim_res.status_code < 400:
                        return Issue(name=item.name, issue_type=issue_type, location=item.location, suggestion=trimmed)
            return Issue(name=item.name, issue_type="DOI_NOT_FOUND", location=item.location)
    except Exception:
        return None
