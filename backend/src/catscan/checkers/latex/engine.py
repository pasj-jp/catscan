import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple

from ..common.diagnostics import localized_message
from ..rules import load_rules
from ..rules.schema import LatexRule, LatexRules, LatexTarget
from .doi import check_doi_online
from .project import (
    BIB_ENTRY, BIBLIOGRAPHY, CITATION, CoverageNotice, LatexProject, active_tex,
    blank_out, expand_project, resolve_project_file,
)

BIBITEM_RE = re.compile(
    r'(\\bibitem(?:\[.*?\])?\{([^}]+)\})(.*?)(?=(\\bibitem|\\end\{thebibliography\}|\Z))',
    re.DOTALL,
)
DOI_RE = re.compile(r'10\.\d{4,9}/[-._\\;()/:a-zA-Z0-9]+')
MACRO_ARG = r'\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
CAPTION_RE = re.compile(r'\\caption\b\s*(?:\[[^]]*\]\s*)?' + MACRO_ARG, re.DOTALL)
LABEL_RE = re.compile(r'(?<!\\)\\label\s*\{([^{}]+)\}')
REFERENCE_RE = re.compile(r'(?<!\\)\\(?:ref|eqref|pageref|autoref|cref|Cref)\*?\s*\{([^{}]+)\}')
VISIBLE_TEXT_COMMAND = re.compile(r'\\(?:text(?:bf|it|sl|sc|sf|tt|rm|up|md|normal)|emph|underline)\b')



def decode_tex_bytes(data: bytes) -> str:
    """Decode LaTeX source supporting UTF-8 as well as common Japanese TeX encodings."""
    if b"\x1b$" in data:
        try:
            return data.decode("iso2022_jp")
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8-sig", "utf-8", "cp932", "euc_jp"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


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
    category: str = 'reference'


@dataclass(frozen=True)
class SourceText:
    text: str
    start: int


class LatexSource:
    """Look up text in the source while keeping offsets into the submitted files."""

    def __init__(self, content: str):
        self.content = content
        self.visible = active_tex(content)

    def search(self, pattern: str, flags: int = 0, ignore_comments: bool = True):
        return re.search(pattern, self.visible if ignore_comments else self.content, flags)

    def document_bounds(self) -> Tuple[int, int]:
        start = self.search(r'\\begin\s*\{document\}')
        first = start.end() if start else 0
        end = re.compile(r'\\end\s*\{document\}').search(self.visible, first)
        return first, end.start() if end else len(self.content)

    def extract(self, target: LatexTarget) -> Optional[SourceText]:
        if target.builtin == "body":
            return self._body(target)
        if target.regex:
            match = self.search(target.regex, ignore_comments=target.ignore_comments)
        else:
            names = "|".join(re.escape(n) for n in target.macros)
            match = self.search(r'\\(?:' + names + r')' + MACRO_ARG, ignore_comments=target.ignore_comments)
            if not match and target.env:
                env = re.escape(target.env)
                match = self.search(r'\\begin\{' + env + r'\}(.*?)\\end\{' + env + r'\}', re.DOTALL,
                                    ignore_comments=target.ignore_comments)
        if match is None:
            return None
        start, end = match.span(1)
        text = self.visible[start:end] if target.strip_comments else match[1]
        return SourceText(text, start)

    def _body(self, target: LatexTarget) -> SourceText:
        start, end = self.document_bounds()
        if target.start and (marker := re.compile(target.start).search(self.visible, start, end)):
            start = marker.end()
        if target.end and (marker := re.compile(target.end).search(self.visible, start, end)):
            end = marker.start()
        clean = self.visible[start:end]
        clean = VISIBLE_TEXT_COMMAND.sub(lambda match: blank_out(match[0]), clean)
        for pattern in (r'\$\$.*?\$\$|\$[^$]*?\$', r'\\\[.*?\\\]|\\\(.*?\\\)',
                        r'\\begin\{(equation\*?|align\*?)\}.*?\\end\{\1\}',
                        r'\\[a-zA-Z]+(?:\*|\b)(?:\[[^\]]*\])?(?:\{[^{}]*\})?'):
            clean = re.sub(pattern, lambda match: blank_out(match[0]), clean, flags=re.DOTALL)
        return SourceText(clean, start)

    def captions(self, envs: List[str]) -> Iterator[tuple[Location, Optional[SourceText]]]:
        names = "|".join(re.escape(e) for e in envs)
        pattern = re.compile(r'\\begin\s*\{(' + names + r')\}(.*?)\\end\s*\{\1\}', re.DOTALL)
        for match in pattern.finditer(self.visible, *self.document_bounds()):
            location = Location(match.start(), match.start(2))
            caption = CAPTION_RE.search(match[2])
            if caption is None or not caption[1].strip():
                yield location, None
            else:
                text = caption[1].lstrip()
                start = match.start(2) + caption.start(1) + len(caption[1]) - len(text)
                yield location, SourceText(text.rstrip(), start)

    def bib_items(self) -> List[BibItem]:
        doc_start, doc_end = self.document_bounds()
        items: List[BibItem] = []
        for match in BIBITEM_RE.finditer(self.visible, doc_start, doc_end):
            label_start = match.start(1)
            raw_text = match.group(3)
            clean_text = re.sub(r'\s+', ' ', raw_text).strip()
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


def matched_location(rule: LatexRule, value: SourceText) -> Optional[Location]:
    text = value.text
    flags = re.IGNORECASE if rule.ignore_case else 0
    if rule.when and not re.search(rule.when, text, flags):
        return None
    if rule.match and (match := re.search(rule.match, text, flags)):
        return Location(value.start + match.start(), value.start + match.end())
    if rule.not_match and text.strip() and not re.search(rule.not_match, text, flags):
        return Location(value.start, value.start + len(text))
    return None


def rule_fires(rule: LatexRule, value: Optional[str]) -> bool:
    if value is None:
        return rule.missing
    return matched_location(rule, SourceText(value, 0)) is not None


def undefined_keys(matches: Iterator[re.Match], keys: set[str]) -> Iterator[tuple[re.Match, str]]:
    for match in matches:
        missing = [
            key for part in match[1].split(",")
            if (key := part.strip()) and key not in keys and not any(char in key for char in ("#", "\\"))
        ]
        if missing:
            yield match, ", ".join(missing)


def unresolved_references(src: LatexSource, bib_items: List[BibItem]) -> Iterator[Issue]:
    start, end = src.document_bounds()
    if not re.search(r"\\externaldocument\b", src.visible):
        labels = {label[1].strip() for label in LABEL_RE.finditer(src.visible)}
        for match, names in undefined_keys(REFERENCE_RE.finditer(src.visible, start, end), labels):
            yield Issue(names, "UNDEFINED_REFERENCE", Location(*match.span()), category="cross_reference")

    external_bibliography = BIBLIOGRAPHY.search(src.visible) or re.search(r"\\printbibliography\b", src.visible)
    if bib_items and not external_bibliography:
        keys = {item.name for item in bib_items} | {"*"}
        for match, names in undefined_keys(CITATION.finditer(src.visible, start, end), keys):
            yield Issue(names, "UNDEFINED_CITATION", Location(*match.span()))


def bibliography_notices(
    project: LatexProject, source: LatexSource, bib_items: List[BibItem], *, references_only: bool
) -> List[CoverageNotice]:
    notices: List[CoverageNotice] = []
    keys = {item.name for item in bib_items}
    declarations = list(BIBLIOGRAPHY.finditer(source.visible))
    if not declarations and not re.search(r"(?<!\\)\\printbibliography\b", source.visible):
        if references_only and not bib_items:
            notices.append(CoverageNotice("No inline references available to check.", "検査できる手入力の参考文献がありません。"))
        return notices

    notices.append(CoverageNotice(
        "The formatted output of BibTeX or BibLaTeX was not checked.",
        "BibTeX・BibLaTeX が出力する参考文献の書式は未検査です。",
    ))
    for declaration in declarations:
        pos = project.locate(declaration.start())
        for path in declaration[1].split(","):
            path = path.strip()
            target = resolve_project_file(project.files, project.root, pos.file, path, ".bib")
            if target and target.lower().endswith(".bib"):
                keys.update(entry[1] for entry in BIB_ENTRY.finditer(project.files[target]))
            else:
                notices.append(CoverageNotice(
                    f"Bibliography file {path!r} was not available in the submission.",
                    f"参考文献ファイル {path!r} が提出ファイルに含まれていません。",
                    pos.file, pos.line,
                ))
    if declarations and len(notices) == 1 and not project.notices:
        for citation, names in undefined_keys(CITATION.finditer(source.visible, *source.document_bounds()), keys | {"*"}):
            pos = project.locate(citation.start())
            notices.append(CoverageNotice(
                f"Citation keys not found in the submitted bibliography: {names}",
                f"提出された参考文献ファイルにない引用キー: {names}",
                pos.file, pos.line,
            ))
    return notices


class RuleBasedLatexChecker:
    """LaTeX checker whose rules come from ``rules/<rules_name>.yaml``."""

    def __init__(self, rules_name: str = "", check_online_dois: bool = False):
        self.rules_name = rules_name
        self.check_online_dois = check_online_dois

    @property
    def rules(self) -> LatexRules:
        return load_rules(self.rules_name, LatexRules)

    def find_issues(self, src: LatexSource, rules: LatexRules, bib_items: List[BibItem]) -> List[Issue]:
        issues: List[Issue] = []
        by_scope: Dict[str, List[LatexRule]] = defaultdict(list)
        for rule in rules.rules:
            by_scope[rule.scope].append(rule)

        # 1. document-level rules
        values: Dict[str, Optional[SourceText]] = {}
        for rule in by_scope["document"]:
            if rule.target not in values:
                values[rule.target] = src.extract(rules.targets[rule.target])
            value = values[rule.target]
            location = matched_location(rule, value) if value is not None else None
            if location is not None or (value is None and rule.missing):
                issues.append(Issue(name=rule.name or rule.target, issue_type=rule.issue,
                                    location=location, category=rule.target))

        # 2. captions
        for scope in ("figure", "table"):
            if not by_scope[scope]:
                continue
            cap_cfg = rules.captions[scope]
            for environment, caption in src.captions(cap_cfg.envs):
                for rule in by_scope[scope]:
                    location = matched_location(rule, caption) if caption is not None else None
                    if caption is None and rule.missing:
                        location = environment
                    if location is not None:
                        issues.append(Issue(name=rule.name or cap_cfg.name, issue_type=rule.issue,
                                            location=location, category=scope))

        # 3. bibliography
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

    def check(self, data: bytes, filename: str = "document.tex") -> Dict[str, Any]:
        return self.check_project(expand_project(filename, {filename: decode_tex_bytes(data)}), filename)

    def check_project(self, project: LatexProject, filename: str) -> Dict[str, Any]:
        rules = self.rules
        src = LatexSource(project.content)
        bib_items = src.bib_items()
        issues = self.find_issues(src, rules, bib_items)
        if not project.notices:
            issues.extend(unresolved_references(src, bib_items))
        notices = project.notices + bibliography_notices(
            project, src, bib_items, references_only=self.rules_name == "jacow_latex"
        )

        structured_issues = []
        for issue in issues:
            message = rules.messages.get(issue.issue_type, issue.issue_type)
            position = project.locate(issue.location.start) if issue.location else None
            structured_issues.append({
                "name": issue.name.strip(),
                "type": issue.issue_type,
                "category": issue.category,
                **localized_message(message),
                "start": issue.location.start if issue.location else None,
                "end": issue.location.end if issue.location else None,
                "file": position.file if position else None,
                "line": position.line if position else None,
            })

        return {
            "report_type": "latex",
            "detected_template": self.rules_name.removesuffix("_latex"),
            "filename": filename,
            "issues": structured_issues,
            "total_references": len(bib_items),
            "coverage_notices": [asdict(notice) for notice in notices],
        }
