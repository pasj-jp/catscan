from collections.abc import Iterator
from typing import Any


def detail_rows(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, list):
        for item in node:
            yield from detail_rows(item)
    elif isinstance(node, dict):
        if any(key == "ok" or "_ok" in key for key in node):
            yield node
        else:
            for item in node.values():
                yield from detail_rows(item)


def row_checks(row: dict[str, Any]) -> Iterator[tuple[str, bool | int]]:
    for key, value in row.items():
        if key == "text":
            continue
        if "_ok" in key and (isinstance(value, bool) or value == 2):
            yield key, value
        elif isinstance(value, str) and "should be" in value:
            yield key, False


def score(summary):
    scores = {}
    for name, section in summary.items():
        if name == "Languages":
            continue
        passed = warnings = errors = 0
        for row in detail_rows(section.get("details")):
            for _, verdict in row_checks(row):
                if verdict is True:
                    passed += 1
                elif verdict is False:
                    errors += 1
                else:
                    warnings += 1
        scores[name] = (passed, warnings, errors)
    scores["total"] = tuple(map(sum, zip(*scores.values()))) if scores else (0, 0, 0)
    return scores
