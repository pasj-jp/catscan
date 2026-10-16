"""
Pydantic schemas for the YAML rule files.

The schemas serve two purposes:
  * catch typos / wrong types in editor-maintained YAML at load time, with a
    clear error message pointing at the offending key;
  * give the checker code typed access to the configuration.
"""
import re
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_regex(value: Optional[str]) -> Optional[str]:
    if value is not None:
        try:
            re.compile(value)
        except re.error as e:
            raise ValueError(f"invalid regular expression {value!r}: {e}") from e
    return value


# --------------------------------------------------------------------------
# Shared: report table definition (rendered by the frontend)
# --------------------------------------------------------------------------

class HeaderCell(Strict):
    label: str
    width: Optional[str] = None
    center: bool = False
    colspan: Optional[int] = None

    def to_html(self) -> str:
        attrs = ""
        if self.width:
            attrs += f' style="width: {self.width};"'
        if self.center:
            attrs += ' class="text-center"'
        if self.colspan:
            attrs += f' colspan="{self.colspan}"'
        return f"<th{attrs}>{self.label}</th>"


class ExtraInfo(Strict):
    """Breakdown table shown under a section of the Word report."""
    title: str
    headers: List[HeaderCell] = Field(default_factory=list)
    columns: List[str]
    multi: Optional[bool] = None

    def to_output(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "title": self.title,
            "headers": "<thead><tr>" + "".join(h.to_html() for h in self.headers) + "</tr></thead>",
            "columns": list(self.columns),
        }
        if self.multi is not None:
            out["multi"] = self.multi
        return out


# --------------------------------------------------------------------------
# Shared: page size / margins / columns (Word)
# --------------------------------------------------------------------------

class PageSize(Strict):
    name: str
    width_mm: Optional[float] = None
    width_in: Optional[float] = None
    height_mm: Optional[float] = None
    margin_unit: Literal["mm", "in"] = "mm"
    margins: List[float] = Field(description="[top, bottom, left, right]")

    @model_validator(mode="after")
    def _one_width(self):
        if (self.width_mm is None) == (self.width_in is None):
            raise ValueError(f"page size {self.name!r}: give exactly one of width_mm / width_in")
        if len(self.margins) != 4:
            raise ValueError(f"page size {self.name!r}: margins must be [top, bottom, left, right]")
        return self


class PageLayout(Strict):
    sizes: List[PageSize]
    column_gutter_cm: float = 0.51


# --------------------------------------------------------------------------
# LaTeX rule files (jacow_latex.yaml / pasj_latex.yaml)
# --------------------------------------------------------------------------

class LatexReport(Strict):
    issue_format: str = "Issue found in {name}: {message}"
    extra_output: Dict[str, Any] = Field(default_factory=dict)


class LatexTarget(Strict):
    """How to extract one piece of text from the .tex source."""
    macro: Optional[Union[str, List[str]]] = None
    env: Optional[str] = None
    regex: Optional[str] = None
    builtin: Optional[Literal["body"]] = None
    start: Optional[str] = None
    end: Optional[str] = None
    ignore_comments: bool = True
    strip_comments: bool = False

    _v_regex = field_validator("regex", "start", "end")(_check_regex)

    @model_validator(mode="after")
    def _one_kind(self):
        kinds = [k for k in ("macro", "regex", "builtin") if getattr(self, k) is not None]
        if len(kinds) != 1:
            raise ValueError("a target needs exactly one of: macro, regex, builtin")
        return self

    @property
    def macros(self) -> List[str]:
        if self.macro is None:
            return []
        return [self.macro] if isinstance(self.macro, str) else list(self.macro)


class LatexCaption(Strict):
    envs: List[str]
    name: str


class LatexRule(Strict):
    issue: Optional[str] = None
    scope: Literal["document", "figure", "table", "bibitem"] = "document"
    target: Optional[str] = None
    name: Optional[str] = None
    missing: bool = False
    match: Optional[str] = None
    not_match: Optional[str] = None
    when: Optional[str] = None
    ignore_case: bool = False
    check: Optional[Literal["doi_online"]] = None
    note: Optional[str] = None  # free-form comment for editors, ignored by the checker

    _v_regex = field_validator("match", "not_match", "when")(_check_regex)

    @model_validator(mode="after")
    def _consistent(self):
        if self.check is None:
            if not self.issue:
                raise ValueError("rule needs 'issue' (or a builtin 'check')")
            if not (self.missing or self.match or self.not_match):
                raise ValueError(f"rule {self.issue}: needs at least one of missing / match / not_match")
        if self.scope == "document" and self.check is None and not self.target:
            raise ValueError(f"rule {self.issue}: document rules need a 'target'")
        if self.scope == "bibitem" and self.check is None and self.target not in ("text", "original"):
            raise ValueError(f"rule {self.issue}: bibitem target must be 'text' or 'original'")
        return self


DOI_ONLINE_ISSUES = ("DOI_ENDS_IN_PERIOD", "DOI_ENDS_IN_PARENTHESIS", "DOI_NOT_FOUND")


class LatexRules(Strict):
    report: LatexReport = Field(default_factory=LatexReport)
    targets: Dict[str, LatexTarget] = Field(default_factory=dict)
    captions: Dict[Literal["figure", "table"], LatexCaption] = Field(default_factory=dict)
    rules: List[LatexRule]
    messages: Dict[str, str]

    @model_validator(mode="after")
    def _references(self):
        for r in self.rules:
            if r.scope == "document" and r.target and r.target not in self.targets:
                raise ValueError(f"rule {r.issue}: unknown target {r.target!r} (define it under 'targets')")
            if r.scope in ("figure", "table") and r.scope not in self.captions:
                raise ValueError(f"rule {r.issue}: scope {r.scope!r} needs captions.{r.scope}")
            issues = DOI_ONLINE_ISSUES if r.check == "doi_online" else (r.issue,)
            for issue in issues:
                if issue not in self.messages:
                    raise ValueError(f"no message defined for issue {issue!r} (add it under 'messages')")
        return self


# --------------------------------------------------------------------------
# Word rule files (pasj_word.yaml / jacow_word.yaml)
# --------------------------------------------------------------------------

class WordCheckRule(Strict):
    check: str
    key: Optional[str] = None
    fail_message: Optional[str] = None
    contains: Optional[List[str]] = None
    styles: Optional[List[str]] = None
    chars: Optional[List[str]] = None
    pattern: Optional[str] = None
    text: Optional[str] = None
    flags: Optional[int] = None
    threshold: Optional[float] = None
    allow_all_caps_style: Optional[bool] = None
    name: Optional[Union[str, List[str]]] = None
    size: Optional[float] = None
    size_tolerance: Optional[float] = None
    alignment: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    space_before: Optional[float] = None
    space_after: Optional[float] = None


class WordElementRule(Strict):
    role: str
    type: str
    required: bool = True
    match: Optional[Dict[str, Any]] = None
    checks: List[WordCheckRule] = Field(default_factory=list)
    pass_message: Optional[str] = None
    missing_message: Optional[str] = None
    missing_text: Optional[str] = "未検出 (Missing)"
    scoring_keys: List[str] = Field(default_factory=list)
    truncate: Optional[int] = None
    strip_text: bool = True


class WordSectionRule(Strict):
    title: str
    anchor: str
    extra_info: ExtraInfo
    elements: List[WordElementRule] = Field(default_factory=list)
    rules: Dict[str, Any] = Field(default_factory=dict)
    extra_rules: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    empty_is_ok: bool = False


class WordRules(Strict):
    sections: Dict[str, WordSectionRule] = Field(default_factory=dict)
    required_styles: List[str] = Field(default_factory=list)
    messages: Dict[str, str] = Field(default_factory=dict)


