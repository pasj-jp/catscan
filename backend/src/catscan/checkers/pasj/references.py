import re
from typing import Any

from docx.text.paragraph import Paragraph

from ..common.citations import CITATION, ENTRY_NUMBER, citation_ranges, missing_labels, numbers_in_range
from ..common.docx_utils import to_element
from ..engine import evaluate_section
from ..rules.schema import WordSectionRule


def _location(paragraph_number: int) -> str:
    return f"第 {paragraph_number} 段落 (Paragraph {paragraph_number})"


def _citation_detail(
    paragraph: Paragraph, paragraph_number: int, match: re.Match[str], code: str, message: str
) -> dict[str, Any]:
    text = paragraph.text
    start, end = max(0, match.start() - 42), min(len(text), match.end() + 42)
    excerpt = f"{'…' if start else ''}{text[start:end]}{'…' if end < len(text) else ''}"
    return {
        "text": excerpt,
        "type": f"本文引用 {match[0]}",
        "location": _location(paragraph_number),
        "paragraph_number": paragraph_number,
        "notes": message,
        "citation_issue": code,
        "citation_ok": False,
        "ok": False,
    }


def _check_citations(
    paragraphs: list[tuple[int, Paragraph]], numbers: list[int], *, complete: bool
) -> tuple[list[dict[str, Any]], set[int]]:
    details = []
    cited: set[int] = set()
    next_number_index = 0
    for paragraph_number, paragraph in paragraphs:
        for match in CITATION.finditer(paragraph.text):
            missing, out_of_order = [], []
            for first, last in citation_ranges(match[1]):
                present = numbers_in_range(numbers, first, last)
                if complete:
                    missing.extend(missing_labels(first, last, present))
                for number in present:
                    if number in cited:
                        continue
                    expected = numbers[next_number_index]
                    if complete and number != expected:
                        out_of_order.append((number, expected))
                    cited.add(number)
                    while next_number_index < len(numbers) and numbers[next_number_index] in cited:
                        next_number_index += 1
            if missing:
                details.append(_citation_detail(
                    paragraph, paragraph_number, match, "missing_reference",
                    f"参考文献リストに {', '.join(dict.fromkeys(missing))} がありません。該当する文献を追加するか、引用番号を修正してください。",
                ))
            if out_of_order:
                number, expected = out_of_order[0]
                details.append(_citation_detail(
                    paragraph, paragraph_number, match, "citation_order",
                    f"[{number}] が [{expected}] より先に初出しています。本文で最初に引用した順に番号を振り直してください。",
                ))
    return details, cited


def _annotate_reference(detail: dict[str, Any], code: str, verdict: bool | int, message: str) -> None:
    detail["notes"] = f"{detail['notes']} / {message}" if detail["ok"] is False else message
    detail["citation_issue"] = code
    detail["citation_ok"] = verdict
    if detail["ok"] is not False:
        detail["ok"] = verdict


def build_references_section(
    rule: WordSectionRule,
    citations: list[tuple[int, Paragraph]],
    bibliography: list[tuple[int, Paragraph]],
) -> dict[str, Any]:
    section = evaluate_section(rule, {"reference": [to_element(p) for _, p in bibliography]})
    details = section["details"]
    reference_details: dict[int, dict[str, Any]] = {}
    complete = True
    for (paragraph_number, paragraph), detail in zip(bibliography, details, strict=True):
        detail["location"] = _location(paragraph_number)
        detail["paragraph_number"] = paragraph_number
        match = ENTRY_NUMBER.match(paragraph.text.lstrip())
        number = int(match[1]) if match else 0
        if not number:
            complete = False
            _annotate_reference(
                detail, "unknown_reference_number", 2,
                "参考文献番号を確認できません。自動番号の場合は Word 上で照合し、番号のない文献には角括弧付きの番号を付けてください。",
            )
            continue
        if number in reference_details:
            original = reference_details[number]["location"]
            _annotate_reference(
                detail, "duplicate_reference", False,
                f"参考文献番号 [{number}] は {original} と重複しています。文献と本文の引用番号を確認してください。",
            )
            continue
        reference_details[number] = detail

    findings, cited = _check_citations(citations, sorted(reference_details), complete=complete)
    for number, detail in reference_details.items():
        if number in cited:
            detail["citation_ok"] = True
        elif complete:
            _annotate_reference(
                detail, "uncited_reference", 2,
                f"本文で [{number}] の引用を確認できません。必要な文献なら本文で引用し、不要な文献ならリストから削除してください。",
            )

    details[:0] = findings
    if any(detail["ok"] is False for detail in details):
        section["ok"] = False
    elif any(detail["ok"] == 2 for detail in details):
        section["ok"] = 2
    return section
