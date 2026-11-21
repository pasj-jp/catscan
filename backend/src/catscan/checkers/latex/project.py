import posixpath
import re
from bisect import bisect_right
from dataclasses import dataclass, field


IGNORED_TEX = re.compile(
    r"\\begin\{(?P<env>verbatim\*?|lstlisting|minted)\}.*?\\end\{(?P=env)\}"
    r"|\\verb\*?(?P<delimiter>[^\s])[^\r\n]*?(?P=delimiter)"
    r"|(?<!\\)(?:\\\\)*(?P<comment>%[^\r\n]*)",
    re.DOTALL,
)
DOCUMENT_CLASS = r"(?<!\\)\\documentclass\b\s*(?:\[(?P<options>[^]]*)\]\s*)?\{(?P<class_name>[^{}]+)\}"
JACOW_BIB_CHOICE = re.compile(r"\\ifboolexpr\s*\{\s*bool\s*\{\s*jacowbiblatex\s*\}\s*\}\s*")
UNESCAPED_BRACE = re.compile(r"(?<!\\)[{}]")
WHITESPACE = re.compile(r"\s*")
INCLUDE = re.compile(r"(?<!\\)\\(input|include)\b\s*(?:\{([^{}]*)\}|([^\s\\{}]+))?")
INCLUDE_ONLY = re.compile(r"(?<!\\)\\includeonly\s*\{([^{}]*)\}")
UNSUPPORTED_INCLUDE = re.compile(r"(?<!\\)\\(subfile(?:include)?|(?:sub)?(?:import|includefrom|inputfrom))\b")
BIBLIOGRAPHY = re.compile(r"(?<!\\)\\(?:addbibresource|bibliography)\b\s*(?:\[[^]]*\]\s*)?\{([^{}]*)\}")
BIB_ENTRY = re.compile(r"(?mi)^\s*@(?!(?:comment|string|preamble)\b)[a-z]+\s*[{(]\s*([^,\s{}()]+)\s*,")
CITATION = re.compile(
    r"(?<!\\)\\(?:cite|citep|citet|parencite|textcite|autocite|nocite)\*?"
    r"\s*(?:\[[^]]*\]\s*){0,2}\{([^{}]+)\}"
)
MAX_EXPANDED_LENGTH = 16 * 1024 * 1024
MAX_INCLUDE_DEPTH = 32
MAX_INCLUDES = 2_000


def blank_out(text: str) -> str:
    return re.sub(r"[^\r\n]", " ", text)


def active_tex(text: str) -> str:
    """Hide comments and literal examples while retaining source offsets."""
    def hide(match: re.Match) -> str:
        if match["comment"]:
            return match[0][:-len(match["comment"])] + " " * len(match["comment"])
        return blank_out(match[0])

    visible = IGNORED_TEX.sub(hide, text)
    document_class = re.search(DOCUMENT_CLASS, visible)
    if document_class and document_class["class_name"].strip().casefold() == "jacow":
        options = {option.strip() for option in (document_class["options"] or "").split(",")}
        return _mask_jacow_bibliography_branch(visible, "biblatex" in options)
    return visible


def _group_end(text: str, start: int) -> int | None:
    if text[start:start + 1] != "{":
        return None
    depth = 0
    for match in UNESCAPED_BRACE.finditer(text, start):
        depth += 1 if match[0] == "{" else -1
        if depth == 0:
            return match.end()
    return None


def _mask_jacow_bibliography_branch(text: str, biblatex_enabled: bool) -> str:
    """Recognize the bibliography switch in the JACoW template."""
    chunks = []
    offset = 0
    for match in JACOW_BIB_CHOICE.finditer(text):
        if match.start() < offset or (first_end := _group_end(text, match.end())) is None:
            continue
        second_start = WHITESPACE.match(text, first_end).end()
        second_end = _group_end(text, second_start)
        if second_end is None:
            continue
        start, end = (second_start, second_end) if biblatex_enabled else (match.end(), first_end)
        chunks.extend((text[offset:start], blank_out(text[start:end])))
        offset = end
    chunks.append(text[offset:])
    return "".join(chunks)


@dataclass(frozen=True)
class SourcePosition:
    file: str
    line: int


@dataclass(frozen=True)
class CoverageNotice:
    message: str
    message_ja: str
    file: str | None = None
    line: int | None = None


@dataclass
class LatexProject:
    content: str
    files: dict[str, str]
    root: str
    offsets: list[int]
    origins: list[tuple[str, int]]
    notices: list[CoverageNotice] = field(default_factory=list)

    def locate(self, offset: int) -> SourcePosition:
        if not self.offsets:
            return SourcePosition(self.root, 1)
        index = bisect_right(self.offsets, offset) - 1
        filename, start = self.origins[index]
        return _source_position(filename, self.files[filename], start + offset - self.offsets[index])


def _source_position(filename: str, content: str, offset: int) -> SourcePosition:
    return SourcePosition(filename, content.count("\n", 0, offset) + 1)


def resolve_project_file(files: dict[str, str], root: str, current: str, path: str, extension: str) -> str | None:
    if not path or path.startswith("/") or re.search(r"[\\{}$#%:]", path):
        return None
    names = (path, path + extension) if not posixpath.splitext(path)[1] else (path,)
    for directory in dict.fromkeys((posixpath.dirname(current), posixpath.dirname(root))):
        for name in names:
            candidate = posixpath.normpath(posixpath.join(directory, name))
            if candidate in files:
                return candidate
    return None


def expand_project(root: str, files: dict[str, str]) -> LatexProject:
    """Expand literal local inputs from the submitted files without executing TeX."""
    project = LatexProject("", files, root, [], [])
    chunks: list[str] = []
    length = 0
    expansion_budget = MAX_EXPANDED_LENGTH
    includes = 0
    include_only = INCLUDE_ONLY.search(active_tex(files[root]))
    selected = (
        {posixpath.normpath(name.strip()).removesuffix(".tex") for name in include_only[1].split(",")}
        if include_only else None
    )
    inspected: set[str] = set()

    def append(text: str, filename: str, start: int) -> None:
        nonlocal length
        if text:
            project.offsets.append(length)
            project.origins.append((filename, start))
            chunks.append(text)
            length += len(text)

    def expand(filename: str, ancestors: tuple[str, ...]) -> None:
        nonlocal includes, expansion_budget
        content = files[filename]
        visible = active_tex(content)
        if filename not in inspected:
            inspected.add(filename)
            for event in UNSUPPORTED_INCLUDE.finditer(visible):
                pos = _source_position(filename, content, event.start())
                command = event[0]
                project.notices.append(CoverageNotice(
                    f"Files loaded by {command} could not be checked.",
                    f"{command} で読み込まれるファイルは未検査です。",
                    pos.file, pos.line,
                ))
        start = 0
        for match in INCLUDE.finditer(visible):
            if includes >= MAX_INCLUDES:
                pos = _source_position(filename, content, match.start())
                project.notices.append(CoverageNotice(
                    "Further TeX inputs were skipped after reaching the expansion limit.",
                    "展開上限に達したため、残りの TeX 入力を省略しました。",
                    pos.file, pos.line,
                ))
                break
            includes += 1
            append(content[start:match.start()], filename, start)
            path = (match[2] or match[3] or "").strip()
            if match[1] == "include" and selected is not None and posixpath.normpath(path).removesuffix(".tex") not in selected:
                append("\n", filename, match.end() - 1)
                start = match.end()
                continue
            target = resolve_project_file(files, root, filename, path, ".tex")
            if target is None or not target.lower().endswith((".tex", ".bbl")):
                message = (f"Could not read TeX input {path!r}. Attach all source files in one archive.",
                           f"TeX 入力ファイル {path!r} を読み込めません。ソース一式を圧縮して添付してください。")
            elif target == filename or target in ancestors:
                message = (f"Circular TeX input {path!r} was skipped.", f"循環する TeX 入力 {path!r} を省略しました。")
            elif len(ancestors) >= MAX_INCLUDE_DEPTH or len(files[target]) > expansion_budget:
                message = ("TeX input expansion limit reached.", "TeX 入力の展開上限に達しました。")
            else:
                expansion_budget -= len(files[target])
                expand(target, (*ancestors, filename))
                message = None
            if message:
                position = _source_position(filename, content, match.start())
                project.notices.append(CoverageNotice(*message, position.file, position.line))
            # TeX inputs separate tokens. Keep offsets for subsequent source text.
            append("\n", filename, match.end() - 1)
            start = match.end()
        append(content[start:], filename, start)

    expand(root, ())
    project.content = "".join(chunks)
    return project
