import re
import unicodedata
from bisect import bisect_left, bisect_right


_NUMBER = r"[0-9０-９]{1,9}"
_DASH = r"[-‐‑‒–—−－]"
_RANGE = rf"{_NUMBER}(?:\s*{_DASH}\s*{_NUMBER})?"
CITATION = re.compile(rf"[\[［]\s*({_RANGE}(?:\s*[,，]\s*{_RANGE})*)\s*[\]］]")
ENTRY_NUMBER = re.compile(rf"^[\[［]\s*({_NUMBER})\s*[\]］]")
_RANGE_SEPARATOR = re.compile(_DASH)


def citation_ranges(value: str) -> list[tuple[int, int]]:
    ranges = []
    for part in unicodedata.normalize("NFKC", value).split(","):
        bounds = _RANGE_SEPARATOR.split(part)
        first = int(bounds[0])
        last = int(bounds[-1])
        if not 0 < first <= last:
            return []
        ranges.append((first, last))
    return ranges


def _number_label(first: int, last: int) -> str:
    return f"[{first}]" if first == last else f"[{first}–{last}]"


def numbers_in_range(numbers: list[int], first: int, last: int) -> list[int]:
    return numbers[bisect_left(numbers, first):bisect_right(numbers, last)]


def missing_labels(first: int, last: int, present: list[int]) -> list[str]:
    labels = []
    for number in present:
        if first < number:
            labels.append(_number_label(first, number - 1))
        first = number + 1
    if first <= last:
        labels.append(_number_label(first, last))
    return labels
