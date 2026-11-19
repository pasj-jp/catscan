import io
import os
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from ..checkers.registry import get_checker, detect_template, TEMPLATE_NAMES
from ..errors import DocumentError
from . import reports

MAX_ARCHIVE_ENTRIES = 500
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 25 * 1024 * 1024


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


def _score_tex_candidate(rel_path: str, content: bytes) -> tuple[int, int, int]:
    text = content[:8192].decode("utf-8", errors="ignore")
    has_docclass = 1 if "\\documentclass" in text else 0
    has_begindoc = 1 if "\\begin{document}" in text else 0
    depth = len(PurePosixPath(rel_path).parts)
    return (has_docclass + has_begindoc, -depth, len(content))


def _extract_archive_candidates(data: bytes, filename: str) -> tuple[list[tuple[str, bytes]], list[tuple[str, bytes]]]:
    lower = filename.lower()
    tex_candidates: list[tuple[str, bytes]] = []
    docx_candidates: list[tuple[str, bytes]] = []
    total_read = 0

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
                    if ext in (".tex", ".docx"):
                        content = zf.read(info.filename)
                        if len(content) > MAX_ARCHIVE_MEMBER_BYTES:
                            raise DocumentError(f"Archive entry exceeds size limit: {info.filename}")
                        if ext == ".tex":
                            tex_candidates.append((info.filename, content))
                        else:
                            docx_candidates.append((info.filename, content))
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
                    if ext in (".tex", ".docx"):
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        content = f.read(MAX_ARCHIVE_MEMBER_BYTES + 1)
                        if len(content) > MAX_ARCHIVE_MEMBER_BYTES:
                            raise DocumentError(f"Archive entry exceeds size limit: {member.name}")
                        if ext == ".tex":
                            tex_candidates.append((member.name, content))
                        else:
                            docx_candidates.append((member.name, content))
        except tarfile.TarError as e:
            raise DocumentError(f"Invalid .tar.gz archive: {e}") from e

    return tex_candidates, docx_candidates


def unwrap_document_payload(data: bytes, filename: str) -> tuple[bytes, str, str]:
    """Return `(payload_bytes, effective_filename, doc_type)` for raw or archived manuscripts."""
    lower = filename.lower()
    if lower.endswith(".tex"):
        return data, filename, "latex"
    if lower.endswith(".docx"):
        return data, filename, "word"
    if lower.endswith((".zip", ".tar.gz", ".tgz")):
        tex_candidates, docx_candidates = _extract_archive_candidates(data, filename)
        if tex_candidates:
            best_name, best_bytes = max(tex_candidates, key=lambda item: _score_tex_candidate(item[0], item[1]))
            return best_bytes, Path(best_name).name, "latex"
        if docx_candidates:
            best_name, best_bytes = docx_candidates[0]
            return best_bytes, Path(best_name).name, "word"
        raise DocumentError("Archive does not contain a supported .tex or .docx manuscript.")

    raise DocumentError(f"Unsupported manuscript file format: {filename}")


def scan_document(
    data: bytes,
    filename: str,
    template: str = "auto",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload_bytes, effective_filename, doc_type = unwrap_document_payload(data, filename)
    template = detect_template(payload_bytes, doc_type) if template == "auto" else template
    result = get_checker(template, doc_type).check(payload_bytes, effective_filename)
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
