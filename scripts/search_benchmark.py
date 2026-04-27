#!/usr/bin/env python3

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

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
    return parser.parse_args()


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((percent / 100) * (len(ordered) - 1))))
    return ordered[index]


def main() -> int:
    args = parse_args()
    payload = yaml.safe_load(args.cases.read_text(encoding="utf-8"))
    cases = payload["cases"]
    thresholds = payload.get("thresholds", {})

    index = V8StdIndex(
        pages_path=args.pages,
        vectors_path=args.vectors if args.vectors.exists() else None,
    )
    index.load()

    reciprocal_ranks = []
    latencies_ms = []
    failures = []

    for case in cases:
        start = time.perf_counter()
        result = index.search(case["query"], limit=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed_ms)
        ids = [item["id"] for item in result["results"]]
        expected = case["expected"]
        required_top = int(case.get("required_top", 3))
        try:
            rank = ids.index(expected) + 1
            reciprocal_ranks.append(1 / rank)
        except ValueError:
            rank = None
            reciprocal_ranks.append(0.0)

        print(f"{case['query']!r}: rank={rank} expected={expected} top={ids[:5]} latency_ms={elapsed_ms:.1f}")
        if rank is None or rank > required_top:
            failures.append(f"{case['query']!r}: expected {expected} in top-{required_top}, got {ids[:5]}")

    mrr = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    p95_latency = percentile(latencies_ms, 95)
    print(f"MRR={mrr:.3f} p95_latency_ms={p95_latency:.1f}")

    if mrr < float(thresholds.get("mrr", 0.0)):
        failures.append(f"MRR {mrr:.3f} below threshold {thresholds['mrr']}")
    if p95_latency > float(thresholds.get("p95_latency_ms", 10**9)):
        failures.append(
            f"p95 latency {p95_latency:.1f}ms above threshold {thresholds['p95_latency_ms']}ms"
        )

    if failures:
        print("benchmark failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
