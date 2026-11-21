"""Generate manuscript mutations and exercise the normal CatScan upload API."""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
from shutil import copyfile
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

from catscan.checkers.common.score import detail_rows, row_checks

from cases import BASELINES, CASES, Case, generate_samples


@dataclass(frozen=True)
class Observation:
    key: str
    severity: str
    evidence: str = ""


def scan(client, case: Case, sample: Path) -> tuple[int, dict, list[Observation]]:
    template = case.template or case.group.split("-", 1)[0]
    with sample.open("rb") as data:
        response = client.post("/api/scan/file", files={"file": (sample.name, data)}, data={
            "template": template,
            "verify_template": str(case.verify_template).lower(),
        })
    try:
        report = response.json()
    except ValueError:
        report = {"error": response.text[:300]}
    if response.status_code != 200:
        error = str(report.get("error") or report.get("detail") or response.reason_phrase)
        observations = [Observation(f"request.{response.status_code}", "error", error)]
        if code := report.get("code"):
            observations.append(Observation(f"request.{code}", "review", error))
        return response.status_code, report, observations

    observations = []
    if report.get("report_type") == "latex":
        for issue in report.get("issues", []):
            evidence = " ".join(str(issue[field]) for field in ("file", "line", "name", "message") if issue.get(field))
            observations.append(Observation(issue["type"], "error", evidence))
        for notice in report.get("coverage_notices", []):
            observations.append(Observation("coverage", "review", notice["message"]))
    else:
        for section, summary in report.get("summary", {}).items():
            if section in {"List", "Languages"}:
                continue
            for row in detail_rows(summary["details"]):
                evidence = " · ".join(
                    str(row[field])[:240] for field in ("location", "text", "notes", "text_error", "status")
                    if row.get(field)
                )
                citation = row.get("citation_issue")
                for key, value in row_checks(row):
                    if value is True:
                        continue
                    name = citation if key == "citation_ok" and citation else key
                    message = f"{evidence} · {row[key]}" if isinstance(row[key], str) else evidence
                    observations.append(Observation(f"{section}.{name}", "error" if value is False else "review", message))
    return response.status_code, report, observations


def matches(probe: str, finding: Observation) -> bool:
    key, _, text = probe.partition("@")
    return finding.key == key and text.casefold() in finding.evidence.casefold()


def verdict(case: Case, status: int, report: dict, observed: list[Observation], baseline: list[Observation]) -> str:
    if status != 200 and not case.expected.startswith("request."):
        return "scan-error"
    if case.expected == "baseline":
        return "baseline"
    if case.expected == "no-new":
        new_keys = Counter(item.key for item in observed) - Counter(item.key for item in baseline)
        return "false-positive" if new_keys else "control-pass"
    if case.expected.startswith("template."):
        return "control-pass" if case.expected == f"template.{report.get('detected_template')}" else "false-positive"
    for probe in case.expected.split("|"):
        count = sum(matches(probe, item) for item in observed)
        before = sum(matches(probe, item) for item in baseline)
        if count > before:
            return "detected"
    return "missed"


def audit(output: Path) -> list[dict]:
    from fastapi.testclient import TestClient

    results = []
    with TemporaryDirectory(prefix="catscan-format-audit-") as reports_dir:
        os.environ["REPORTS_DIR"] = reports_dir
        os.environ["CATSCAN_CHECK_DOI"] = "false"
        from catscan.main import app

        baselines = {}
        with TestClient(app, raise_server_exceptions=False) as client:
            for case in CASES:
                sample = output / "samples" / case.filename
                status, report, observed = scan(client, case, sample)
                if case.name == "baseline":
                    if status != 200:
                        raise RuntimeError(f"Cannot scan baseline {sample}: {report}")
                    baselines[case.group] = observed
                baseline = baselines[case.group]
                outcome = verdict(case, status, report, observed, baseline)
                observed_counts = Counter(item.key for item in observed)
                new_counts = observed_counts - Counter(item.key for item in baseline)
                probes = case.expected.split("|")
                evidence = [
                    asdict(item) for item in observed
                    if item.key in new_counts or any(matches(probe, item) for probe in probes)
                ][:12]
                results.append({
                    "path": (Path("samples") / case.filename).as_posix(),
                    "group": case.group,
                    "description": case.description,
                    "expected": case.expected,
                    "verdict": outcome,
                    "http_status": status,
                    "template": report.get("detected_template"),
                    "errors": sum(item.severity == "error" for item in observed),
                    "reviews": sum(item.severity == "review" for item in observed),
                    "new_findings": dict(sorted(new_counts.items())),
                    "observed_findings": dict(sorted(observed_counts.items())),
                    "evidence": evidence,
                })
                print(f"{outcome:14} {case.filename.as_posix()}", flush=True)
    return results


LABELS = {
    "baseline": "基线",
    "detected": "命中",
    "missed": "漏检",
    "control-pass": "对照通过",
    "false-positive": "对照异常",
    "scan-error": "扫描失败",
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(Path(__file__).resolve().parents[2]), *args], text=True).strip()


def write_results(output: Path, results: list[dict]) -> None:
    metadata = {
        "run_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
        "base_commit": _git("rev-parse", "--short", "HEAD"),
        "worktree_modified": bool(_git("status", "--porcelain")),
        "online_doi_check": False,
    }
    (output / "results.json").write_text(
        json.dumps({"run": metadata, "cases": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# CatScan 论文格式校验样例库",
        "",
        f"运行于 {metadata['run_at']}。基于提交 " + metadata["base_commit"] + (
            " 的当前工作区（含本地修改）。" if metadata["worktree_modified"] else "。"
        ),
        "",
        "每个变体通过 CatScan 的上传 API 校验。命中要求目标诊断比同组基线多出现至少一次。"
        "保留上游指南的原有诊断，以便区分样例原本就有的问题与人为植入的问题。"
        "压缩包内的 LaTeX 样例用于源文件扫描。",
        "",
        "| 组合 | 样例 | 命中 | 漏检 | 对照通过 | 对照异常 | 扫描失败 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in BASELINES:
        selected = [row for row in results if row["group"] == group]
        count = Counter(row["verdict"] for row in selected)
        lines.append(
            f"| {group} | {len(selected)} | {count['detected']} | {count['missed']} |"
            f" {count['control-pass']} | {count['false-positive']} | {count['scan-error']} |"
        )
    lines += [
        "", "命中包含预期的警告、未检查提示和上传确认。DOI 联网校验在本次运行中关闭。",
        "", "## 未命中及对照异常", "",
    ]
    for row in results:
        if row["verdict"] in {"missed", "false-positive", "scan-error"}:
            lines.append(
                f"- {row['group']} · [{Path(row['path']).name}]({row['path']}) ·"
                f" {LABELS[row['verdict']]} · {row['description']}"
            )

    for group in BASELINES:
        lines += [
            "", f"## {group}", "",
            "| 样例 | 改动 | 预期诊断 | 结果 | 实际新增诊断 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in (row for row in results if row["group"] == group):
            changes = ", ".join(f"{key} × {count}" for key, count in row["new_findings"].items()) or "—"
            if row["verdict"] == "baseline":
                changes = f"{row['errors']} 条错误诊断，{row['reviews']} 条警告或待确认"
            if row["expected"].startswith("template."):
                changes = f"识别为 {row['template']}"
            expected = row["expected"].replace("|", " 或 ")
            lines.append(
                f"| [{Path(row['path']).name}]({row['path']}) | {row['description']} |"
                f" {expected} | {LABELS[row['verdict']]} | {changes} |"
            )
    lines += [
        "",
        "## 规则来源",
        "",
        "- [PASJ 2026 Word 投稿要领](https://www.pasj.jp/templates/nenkai/Proc_Template2026_Word.pdf)",
        "- [PASJ 论文模板](https://pasj.jp/templates.html)",
        "- [JACoW 论文模板](https://jacow.org/Authors/Templates)",
        "- [JACoW 编辑检查流程](https://www.jacow.org/Organizers/ExamplesWorkFlows)",
        "- [JACoW 正文分栏与图题格式](https://indico.jacow.org/event/80/page/190-paper-preparation-guidelines)",
        "",
        "逐例的诊断摘录、HTTP 状态和基线差异见 [results.json](results.json)。",
    ]
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Directory for generated samples and results")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--generate-only", action="store_true", help="Generate samples without importing the backend")
    mode.add_argument("--reuse-samples", action="store_true", help="Scan previously generated samples")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.generate_only:
        generate_samples(output)
        return
    repository_samples = Path(__file__).resolve().parent / "samples"
    output_samples = output / "samples"
    if not args.reuse_samples and repository_samples != output_samples:
        for case in CASES:
            target = output_samples / case.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(repository_samples / case.filename, target)
    results = audit(output)
    write_results(output, results)
    archive = output / "catscan-format-audit.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for name in ["RESULTS.md", "results.json", *(row["path"] for row in results)]:
            bundle.write(output / name, arcname=name)
    print(f"\n{output / 'RESULTS.md'}\n{archive}")


if __name__ == "__main__":
    main()
