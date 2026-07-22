#!/usr/bin/env python3

from __future__ import annotations

import argparse
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from v8std_mcp_index import V8StdIndex  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v8std MCP retrieval benchmark.")
    parser.add_argument("--pages", type=Path, default=Path("docs/ai/pages.jsonl"))
    parser.add_argument("--vectors", type=Path, default=Path("docs/ai/search-vectors.jsonl"))
    parser.add_argument("--cases", type=Path, default=Path("tests/search_benchmark_cases.yml"))
    parser.add_argument(
        "--cases-extra",
        type=Path,
        default=None,
        help="Optional additional benchmark cases, for example local log-derived feedback cases.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".cache/search-benchmark.md"),
        help="Write a Markdown report (default: ignored local cache).",
    )
    return parser.parse_args()


def read_case_payloads(cases_path: Path, extra_cases_path: Path | None = None) -> tuple[list[dict], dict[str, Any]]:
    payload = yaml.safe_load(cases_path.read_text(encoding="utf-8")) or {}
    cases = [dict(case, _case_source="static") for case in payload.get("cases", [])]
    thresholds = payload.get("thresholds", {})

    if extra_cases_path is not None and extra_cases_path.exists():
        extra_payload = yaml.safe_load(extra_cases_path.read_text(encoding="utf-8")) or {}
        cases.extend(
            dict(case, _case_source=case.get("_case_source", "feedback"))
            for case in extra_payload.get("cases", [])
        )

    return cases, thresholds


def ranked_summary(records: list[dict[str, Any]], source: str | None = None) -> dict[str, Any]:
    ranked_records = [
        record
        for record in records
        if record.get("tool") != "diagnostics"
        and not record.get("negative")
        and (source is None or record.get("_case_source") == source)
    ]
    reciprocal_ranks = [
        0.0 if record.get("rank") is None else 1 / int(record["rank"])
        for record in ranked_records
    ]
    top3_hits = sum(
        1
        for record in ranked_records
        if record.get("rank") is not None and int(record["rank"]) <= 3
    )
    return {
        "ranked_cases": len(ranked_records),
        "top3_hits": top3_hits,
        "mrr": statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0,
    }


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((percent / 100) * (len(ordered) - 1))))
    return ordered[index]


def rank_expected(ids: list[str], expected: str) -> int | None:
    try:
        return ids.index(expected) + 1
    except ValueError:
        return None


def collect_case_ids(index: V8StdIndex, case: dict) -> list[str]:
    tool = case.get("tool", "search")
    limit = int(case.get("limit", 10))

    if tool == "search":
        result = index.search(
            case["query"],
            limit=limit,
            types=case.get("types"),
            mode=case.get("mode", "hybrid"),
        )
        return [item["id"] for item in result["results"]]

    if tool == "snippet":
        result = index.explain_snippet(
            case["snippet"],
            language=case.get("language", "auto"),
            limit=limit,
        )
        field = case.get("expected_field", "standards")
        return [item["id"] for item in result[field]]

    raise ValueError(f"unsupported ranked benchmark tool: {tool}")


def run_ranked_case(index: V8StdIndex, case: dict) -> tuple[int | None, list[str]]:
    ids = collect_case_ids(index, case)
    return rank_expected(ids, case["expected"]), ids


def run_diagnostics_case(index: V8StdIndex, case: dict) -> tuple[list[str], list[str]]:
    result = index.explain_diagnostics(case["codes"])
    diagnostics = [item["id"] for item in result["diagnostics"]]
    standards = [item["id"] for item in result["standards"]]
    unknown = [item["code"] for item in result["unknown_codes"]]
    failures = []

    for expected in case.get("expected_diagnostics", []):
        if expected not in diagnostics:
            failures.append(f"expected diagnostic {expected}, got {diagnostics}")
    for expected in case.get("expected_standards", []):
        if expected not in standards:
            failures.append(f"expected standard {expected}, got {standards}")
    for expected in case.get("expected_unknown", []):
        if expected not in unknown:
            failures.append(f"expected unknown code {expected}, got {unknown}")

    return failures, diagnostics


def case_label(case: dict) -> str:
    scenario = case.get("scenario", case.get("tool", "search"))
    if "query" in case:
        return f"{scenario}: {case['query']!r}"
    if "snippet" in case:
        return f"{scenario}: snippet"
    return f"{scenario}: diagnostics"


def case_input(case: dict) -> str:
    if "query" in case:
        return str(case["query"])
    if "snippet" in case:
        return str(case["snippet"]).strip()
    if "codes" in case:
        return ", ".join(str(code) for code in case["codes"])
    return ""


def markdown_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\n", "<br>")
        .replace("\r", "")
    )


def format_bool(value: bool) -> str:
    return "yes" if value else "no"


def write_report(
    path: Path,
    *,
    records: list[dict[str, Any]],
    failures: list[str],
    status: dict[str, Any],
    thresholds: dict[str, Any],
    mrr: float,
    p95_latency: float,
    elapsed_total_ms: float,
    summaries: dict[str, dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    ranked_records = [record for record in records if record["tool"] != "diagnostics"]
    diagnostics_records = [record for record in records if record["tool"] == "diagnostics"]
    passed = len(failures) == 0
    slowest = sorted(records, key=lambda item: item["latency_ms"], reverse=True)[:10]

    lines = [
        "# v8std MCP Retrieval Benchmark",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`",
        f"- Result: **{'PASS' if passed else 'FAIL'}**",
        f"- Cases: `{len(records)}` total, `{len(ranked_records)}` ranked, `{len(diagnostics_records)}` diagnostics batch",
        f"- MRR: `{mrr:.3f}` / threshold `{float(thresholds.get('mrr', 0.0)):.3f}`",
        f"- p95 latency: `{p95_latency:.1f} ms` / threshold `{float(thresholds.get('p95_latency_ms', 0.0)):.1f} ms`",
        f"- Total benchmark time: `{elapsed_total_ms:.1f} ms`",
        f"- Static MRR/top-3: `{summaries['static']['mrr']:.3f}` / `{summaries['static']['top3_hits']}/{summaries['static']['ranked_cases']}`",
        f"- Feedback MRR/top-3: `{summaries['feedback']['mrr']:.3f}` / `{summaries['feedback']['top3_hits']}/{summaries['feedback']['ranked_cases']}`",
        "",
        "## Index",
        "",
        f"- Source: `{status.get('source', '')}`",
        f"- Pages: `{status.get('row_count', 0)}`",
        f"- SHA256: `{status.get('sha256', '')}`",
        f"- Semantic enabled: `{format_bool(bool(status.get('semantic_enabled')))}`",
    ]

    vectors = status.get("vectors")
    if isinstance(vectors, dict):
        lines.extend(
            [
                f"- Vectors source: `{vectors.get('source', '')}`",
                f"- Vectors: `{vectors.get('row_count', 0)}`",
                f"- Vector model: `{vectors.get('model', '')}`",
                f"- Vector dim: `{vectors.get('dim', '')}`",
                f"- Vectors SHA256: `{vectors.get('sha256', '')}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Results",
            "",
            "| # | Scenario | Input | Tool | Expected | Rank / OK | Latency | Top results |",
            "| ---: | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )

    for number, record in enumerate(records, start=1):
        if record["tool"] == "diagnostics" or record.get("negative"):
            rank_or_ok = "OK" if record["ok"] else "FAIL"
        else:
            rank_or_ok = f"#{record['rank']}" if record["rank"] is not None else "MISS"

        lines.append(
            "| "
            + " | ".join(
                [
                    str(number),
                    markdown_escape(record["scenario"]),
                    markdown_escape(record["input"]),
                    markdown_escape(record["tool"]),
                    markdown_escape(record["expected"]),
                    markdown_escape(rank_or_ok),
                    f"{record['latency_ms']:.1f} ms",
                    markdown_escape(", ".join(record["top_ids"][:5])),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Slowest Cases",
            "",
            "| Scenario | Latency | Top results |",
            "| --- | ---: | --- |",
        ]
    )

    for record in slowest:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(record["scenario"]),
                    f"{record['latency_ms']:.1f} ms",
                    markdown_escape(", ".join(record["top_ids"][:5])),
                ]
            )
            + " |"
        )

    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {markdown_escape(failure)}" for failure in failures)

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    started_at = time.perf_counter()
    cases, thresholds = read_case_payloads(args.cases, args.cases_extra)

    index = V8StdIndex(
        pages_path=args.pages,
        vectors_path=args.vectors if args.vectors.exists() else None,
    )
    index.load()

    reciprocal_ranks = []
    latencies_ms = []
    failures = []
    records: list[dict[str, Any]] = []

    for case in cases:
        label = case_label(case)
        scenario = case.get("scenario", label)
        start = time.perf_counter()
        if case.get("tool", "search") == "diagnostics":
            case_failures, ids = run_diagnostics_case(index, case)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)
            print(f"{label}: ok={not case_failures} diagnostics={ids[:5]} latency_ms={elapsed_ms:.1f}")
            failures.extend(f"{label}: {failure}" for failure in case_failures)
            records.append(
                {
                    "scenario": scenario,
                    "input": case_input(case),
                    "tool": "diagnostics",
                    "expected": ", ".join(
                        [
                            *case.get("expected_diagnostics", []),
                            *case.get("expected_standards", []),
                            *case.get("expected_unknown", []),
                        ]
                    ),
                    "rank": None,
                    "ok": not case_failures,
                    "latency_ms": elapsed_ms,
                    "top_ids": ids,
                    "_case_source": case.get("_case_source", "static"),
                }
            )
            continue

        if "expected_absent" in case:
            ids = collect_case_ids(index, case)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)
            expected_absent = case["expected_absent"]
            ok = expected_absent not in ids
            print(
                f"{label}: absent_ok={ok} expected_absent={expected_absent} "
                f"top={ids[:5]} latency_ms={elapsed_ms:.1f}"
            )
            if not ok:
                failures.append(f"{label}: expected {expected_absent} to be absent, got {ids[:5]}")
            records.append(
                {
                    "scenario": scenario,
                    "input": case_input(case),
                    "tool": case.get("tool", "search"),
                    "expected": f"absent: {expected_absent}",
                    "rank": None,
                    "ok": ok,
                    "negative": True,
                    "latency_ms": elapsed_ms,
                    "top_ids": ids,
                    "_case_source": case.get("_case_source", "static"),
                }
            )
            continue

        rank, ids = run_ranked_case(index, case)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed_ms)
        expected = case["expected"]
        required_top = int(case.get("required_top", 3))
        reciprocal_ranks.append(0.0 if rank is None else 1 / rank)

        print(f"{label}: rank={rank} expected={expected} top={ids[:5]} latency_ms={elapsed_ms:.1f}")
        if rank is None or rank > required_top:
            failures.append(f"{label}: expected {expected} in top-{required_top}, got {ids[:5]}")
        records.append(
            {
                "scenario": scenario,
                "input": case_input(case),
                "tool": case.get("tool", "search"),
                "expected": expected,
                "rank": rank,
                "ok": rank is not None and rank <= required_top,
                "latency_ms": elapsed_ms,
                "top_ids": ids,
                "_case_source": case.get("_case_source", "static"),
            }
        )

    summaries = {
        "static": ranked_summary(records, source="static"),
        "feedback": ranked_summary(records, source="feedback"),
        "all": ranked_summary(records),
    }
    mrr = summaries["all"]["mrr"]
    p95_latency = percentile(latencies_ms, 95)
    print(f"MRR={mrr:.3f} p95_latency_ms={p95_latency:.1f}")

    if mrr < float(thresholds.get("mrr", 0.0)):
        failures.append(f"MRR {mrr:.3f} below threshold {thresholds['mrr']}")
    if p95_latency > float(thresholds.get("p95_latency_ms", 10**9)):
        failures.append(
            f"p95 latency {p95_latency:.1f}ms above threshold {thresholds['p95_latency_ms']}ms"
        )

    if args.report:
        write_report(
            args.report,
            records=records,
            failures=failures,
            status=index.status(),
            thresholds=thresholds,
            mrr=mrr,
            p95_latency=p95_latency,
            elapsed_total_ms=(time.perf_counter() - started_at) * 1000,
            summaries=summaries,
        )
        print(f"report={args.report}")

    if failures:
        print("benchmark failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
