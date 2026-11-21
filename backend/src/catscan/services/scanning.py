import io
import os
import re
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from ..checkers.common.docx_utils import open_docx
from ..checkers.latex.engine import decode_tex_bytes
from ..checkers.latex.project import DOCUMENT_CLASS, active_tex, expand_project
from ..checkers.registry import TEMPLATE_NAMES, detect_latex_source, detect_word_template, get_checker
from ..errors import DocumentError, TemplateMismatchError
from . import reports

MAX_ARCHIVE_ENTRIES = 500
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 25 * 1024 * 1024
SOURCE_SUFFIXES = (".tex", ".bib", ".bbl", ".docx")


def _is_ignored_member(member_name: str) -> bool:
    parts = PurePosixPath(member_name.replace("\\", "/")).parts
    if not parts:
        return True
    if any(p == "__MACOSX" or p.startswith("._") for p in parts):
        return True
    return False


def _is_safe_member_path(member_name: str) -> bool:
    normalized = member_name.replace("\\", "/")
    if normalized.startswith("/") or (len(normalized) >= 2 and normalized[1] == ":"):
        return False
    parts = PurePosixPath(normalized).parts
    return ".." not in parts


def _score_tex_candidate(rel_path: str, content: str) -> tuple[int, int]:
    text = active_tex(content)
    has_docclass = bool(re.search(DOCUMENT_CLASS, text))
    has_begindoc = bool(re.search(r"\\begin\s*\{document\}", text))
    depth = len(PurePosixPath(rel_path).parts)
    return has_docclass + has_begindoc, -depth


def _extract_archive_sources(data: bytes, filename: str) -> dict[str, bytes]:
    lower = filename.lower()
    sources: dict[str, bytes] = {}
    total_read = 0

    def store_source(name: str, content: bytes) -> None:
        path = PurePosixPath(name.replace("\\", "/")).as_posix()
        if path in sources:
            raise DocumentError(f"Duplicate source path in archive: {path}")
        if len(content) > MAX_ARCHIVE_MEMBER_BYTES:
            raise DocumentError(f"Archive entry exceeds size limit: {name}")
        sources[path] = content

    if lower.endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                infos = zf.infolist()
                if len(infos) > MAX_ARCHIVE_ENTRIES:
                    raise DocumentError("Archive contains too many entries.")
                for info in infos:
                    if info.is_dir() or _is_ignored_member(info.filename):
                        continue
                    if not _is_safe_member_path(info.filename):
                        raise DocumentError(f"Unsafe archive entry path: {info.filename}")
                    if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                        raise DocumentError(f"Archive entry exceeds size limit: {info.filename}")
                    total_read += info.file_size
                    if total_read > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise DocumentError("Archive uncompressed content exceeds size limit.")
                    ext = os.path.splitext(info.filename.lower())[1]
                    if ext in SOURCE_SUFFIXES:
                        store_source(info.filename, zf.read(info))
        except zipfile.BadZipFile as e:
            raise DocumentError(f"Invalid .zip archive: {e}") from e
    elif lower.endswith((".tar.gz", ".tgz")):
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                members = tf.getmembers()
                if len(members) > MAX_ARCHIVE_ENTRIES:
                    raise DocumentError("Archive contains too many entries.")
                for member in members:
                    if not member.isfile() or _is_ignored_member(member.name):
                        continue
                    if member.issym() or member.islnk():
                        continue
                    if not _is_safe_member_path(member.name):
                        raise DocumentError(f"Unsafe archive entry path: {member.name}")
                    if member.size > MAX_ARCHIVE_MEMBER_BYTES:
                        raise DocumentError(f"Archive entry exceeds size limit: {member.name}")
                    total_read += member.size
                    if total_read > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise DocumentError("Archive uncompressed content exceeds size limit.")
                    ext = os.path.splitext(member.name.lower())[1]
                    if ext in SOURCE_SUFFIXES:
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        store_source(member.name, f.read(MAX_ARCHIVE_MEMBER_BYTES + 1))
        except tarfile.TarError as e:
            raise DocumentError(f"Invalid .tar.gz archive: {e}") from e

    return sources


def _manuscript_sources(data: bytes, filename: str) -> dict[str, bytes]:
    lower = filename.lower()
    if lower.endswith((".tex", ".docx")):
        return {filename: data}
    if lower.endswith((".zip", ".tar.gz", ".tgz")):
        return _extract_archive_sources(data, filename)
    raise DocumentError(f"Unsupported manuscript file format: {filename}")


def _select_template(selected: str, detected: str | None) -> str:
    if selected == "auto":
        return detected or "jacow"
    if detected is not None and selected.casefold() != detected:
        raise TemplateMismatchError(selected, detected)
    return selected


def scan_document(
    data: bytes,
    filename: str,
    template: str = "auto",
    extra: dict[str, Any] | None = None,
    *,
    verify_template: bool = False,
) -> dict[str, Any]:
    auto_template = template == "auto"
    sources = _manuscript_sources(data, filename)
    tex_sources = {
        name: decode_tex_bytes(content)
        for name, content in sources.items()
        if name.lower().endswith((".tex", ".bib", ".bbl"))
    }
    candidates = [name for name in tex_sources if name.lower().endswith(".tex")]
    if candidates:
        root = candidates[0]
        if len(candidates) > 1:
            scores = {name: _score_tex_candidate(name, tex_sources[name]) for name in candidates}
            candidates.sort(key=scores.__getitem__, reverse=True)
            root, second = candidates[:2]
            if scores[root] == scores[second]:
                raise DocumentError(
                    "Multiple possible TeX main files. Submit an archive with a single identifiable main file."
                )
        effective_filename = Path(root).name
        doc_type = "latex"
        project = expand_project(root, tex_sources)
        if auto_template or verify_template:
            detected = detect_latex_source(project.content, allow_language_fallback=auto_template)
            template = _select_template(template, detected)
        result = get_checker(template, doc_type).check_project(project, effective_filename)
    else:
        root = next((name for name in sources if name.lower().endswith(".docx")), None)
        if root is None:
            raise DocumentError("Archive does not contain a supported .tex or .docx manuscript.")
        effective_filename = Path(root).name
        doc_type = "word"
        doc = open_docx(sources[root])
        if auto_template or verify_template:
            detected = detect_word_template(doc, allow_language_fallback=auto_template)
            template = _select_template(template, detected)
        result = get_checker(template, doc_type).check_document(doc, effective_filename)
    result.update({
        "report_type": doc_type,
        "detected_template": template,
        "template_name": TEMPLATE_NAMES.get(template, template),
        "filename": effective_filename,
        **(extra or {}),
    })
    if effective_filename != filename:
        result.setdefault("archive_filename", filename)
    result["report_id"] = reports.save(result)
    return result
