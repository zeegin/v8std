#!/usr/bin/env python3
"""Reproducible local snippet gates; never sends requests to a public server."""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
import types
from pathlib import Path
from unittest.mock import patch

from dev.checks.search_benchmark import percentile, read_case_payloads
from runtime.v8std_mcp_index import V8StdIndex

ROOT = Path(__file__).resolve().parents[2]


def summarize_series(series: list[list[float]]) -> dict:
    p95s = [percentile(samples, 95) for samples in series]
    return {"series_p95_ms": p95s, "p95_ms": statistics.median(p95s)}


def within_budget(baseline: float, current: float, relative: float, absolute: float) -> bool:
    return current <= baseline + max(baseline * relative, absolute)


def historical_module(ref: str, path: str, name: str) -> types.ModuleType:
    source = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT, text=True)
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / path)
    sys.modules[name] = module  # dataclasses resolves its defining module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def load_baseline(ref: str):
    rules = historical_module(ref, "scripts/v8std_retrieval_rules.py", "_snippet_baseline_rules")
    features = historical_module(ref, "scripts/v8std_search_features.py", "_snippet_baseline_features")
    with patch.dict(sys.modules, {"v8std_retrieval_rules": rules, "v8std_search_features": features}):
        return historical_module(ref, "scripts/v8std_mcp_index.py", "_snippet_baseline_index").V8StdIndex


def fixture(size: int, kind: str) -> str:
    tail = "\nУстановитьПривилегированныйРежим(Истина);"
    if kind == "procedure":
        filler = "ВычислитьЗначение(Объект);\n"
        return (filler * size)[:size - len(tail)] + tail
    if kind == "word":
        return "я" * (size - len(tail)) + tail
    if kind == "quotes":
        prefix = 'Запрос = "ВЫБРАТЬ РАЗРЕШЕННЫЕ '
        return prefix + '"' * (size - len(prefix) - len(tail)) + tail
    raise ValueError(kind)


def run(args) -> dict:
    baseline_type = load_baseline(args.baseline_ref)
    indexes = []
    for cls, extra in ((baseline_type, {}), (V8StdIndex, {"max_snippet_chars": 32000})):
        index = cls(pages_path=ROOT / "docs/ai/pages.jsonl",
                    vectors_path=ROOT / "docs/ai/search-vectors.jsonl", **extra)
        index.load()
        if args.without_vectors:
            index._vectors = []
        indexes.append(index)
    baseline, current = indexes
    cases, _ = read_case_payloads(ROOT / "tests/search_benchmark_cases.yml")
    compared = 0
    for case in cases:
        if case.get("tool", "search") != "search":
            continue
        kwargs = {"limit": int(case.get("limit", 10)), "types": case.get("types"), "mode": case.get("mode", "hybrid")}
        before = baseline.search(case["query"], **kwargs)["results"]
        after = current.search(case["query"], **kwargs)["results"]
        if before != after:
            raise AssertionError(f"ordinary search changed: {case['scenario']}")
        compared += 1
    short = "УстановитьПривилегированныйРежим(Истина);"
    scenarios = {"short_baseline": (baseline, short), "short_current": (current, short)}
    for kind in ("procedure", "word", "quotes"):
        for size in (4000, 32000):
            scenarios[f"{kind}_{size}"] = (current, fixture(size, kind))
    measurements = {name: [] for name in scenarios}
    for series in range(3):
        for name, (index, source) in scenarios.items():
            for _ in range(20):
                index.explain_snippet(source)
            samples = []
            for _ in range(200):
                start = time.perf_counter()
                result = index.explain_snippet(source)
                samples.append((time.perf_counter() - start) * 1000)
                if not any(entry["id"] == "std485" for entry in result["standards"]):
                    raise AssertionError(f"lost primary target: {name}")
            measurements[name].append(samples)
            print(json.dumps({"series": series + 1, "scenario": name, "p95_ms": percentile(samples, 95)}), flush=True)
    summary = {name: summarize_series(series) for name, series in measurements.items()}
    gates = {"short": within_budget(summary["short_baseline"]["p95_ms"], summary["short_current"]["p95_ms"], .2, 10)}
    for kind in ("procedure", "word", "quotes"):
        gates[kind] = within_budget(summary[f"{kind}_4000"]["p95_ms"], summary[f"{kind}_32000"]["p95_ms"], .25, 20)
    return {"baseline_ref": args.baseline_ref, "python": platform.python_version(), "platform": platform.platform(),
            "index": current.status(), "search_cases_identical": compared, "warmups": 20, "samples": 200,
            "series": 3, "summary": summary, "gates": gates, "passed": all(gates.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True, help="Trusted local Git ref to compare without changing checkout.")
    parser.add_argument("--report", type=Path, default=ROOT / ".cache/snippet-benchmark.json")
    parser.add_argument("--without-vectors", action="store_true")
    args = parser.parse_args()
    report = run(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report), "gates": report["gates"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
