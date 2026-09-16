#!/usr/bin/env python3

from __future__ import annotations

import argparse
import gzip
import glob
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

import yaml


DEFAULT_USAGE_LOG = Path("/var/lib/v8std-mcp/tool-usage.jsonl")
DEFAULT_WINDOW_SECONDS = 180
DEFAULT_MIN_FREQUENCY = 2
DEFAULT_DOMINANCE = 0.6
MAX_QUERY_CHARS = 240
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<name>пароль|password|secret|token)\s*=\s*(?P<value>\"[^\"]*\"|'[^']*'|[^\s;]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UsageEvent:
    ts: datetime
    system: str
    tool: str
    query: str = ""
    page_id: str = ""


def parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sanitize_query(value: str) -> str:
    value = value.replace("```", " ")
    value = value.replace("\r", " ").replace("\n", " ")
    value = SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group('name')} = <redacted>", value)
    value = " ".join(value.split())
    return value[:MAX_QUERY_CHARS]


def parse_usage_line(line: str) -> UsageEvent | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    ts = parse_iso_datetime(payload.get("ts"))
    tool = payload.get("tool")
    if ts is None or not isinstance(tool, str):
        return None

    system = str(payload.get("system") or "unknown").casefold()
    if tool == "v8std_search":
        query = payload.get("query") or payload.get("normalized_query")
        if not isinstance(query, str) or not query.strip():
            return None
        return UsageEvent(ts=ts, system=system, tool=tool, query=sanitize_query(query))

    if tool == "v8std_get_page":
        page_id = payload.get("page_id") or payload.get("requested_page")
        if not isinstance(page_id, str) or not page_id.strip():
            return None
        return UsageEvent(ts=ts, system=system, tool=tool, page_id=page_id.strip())

    return UsageEvent(ts=ts, system=system, tool=tool)


def build_feedback_cases(
    lines: Iterable[str],
    *,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    min_frequency: int = DEFAULT_MIN_FREQUENCY,
    dominance: float = DEFAULT_DOMINANCE,
) -> list[dict]:
    events = [event for line in lines if (event := parse_usage_line(line)) is not None]
    events.sort(key=lambda event: event.ts)
    page_events_by_system: dict[str, list[UsageEvent]] = defaultdict(list)
    for event in events:
        if event.tool == "v8std_get_page":
            page_events_by_system[event.system].append(event)

    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        if event.tool != "v8std_search" or not event.query:
            continue
        target = first_following_page(
            event,
            page_events_by_system.get(event.system, []),
            window_seconds=window_seconds,
        )
        if target is not None:
            transitions[event.query][target.page_id] += 1

    cases = []
    for query, targets in sorted(transitions.items()):
        total = sum(targets.values())
        if total < min_frequency:
            continue
        target_id, frequency = targets.most_common(1)[0]
        target_dominance = frequency / total
        if target_dominance < dominance:
            continue
        cases.append(
            {
                "scenario": f"feedback: {query}",
                "query": query,
                "expected": target_id,
                "required_top": 3,
                "_case_source": "feedback",
                "feedback": {
                    "frequency": frequency,
                    "total": total,
                    "dominance": round(target_dominance, 3),
                    "window_seconds": window_seconds,
                },
            }
        )
    return cases


def first_following_page(
    search_event: UsageEvent,
    page_events: list[UsageEvent],
    *,
    window_seconds: int,
) -> UsageEvent | None:
    for event in page_events:
        delta = (event.ts - search_event.ts).total_seconds()
        if delta < 0:
            continue
        if delta > window_seconds:
            return None
        return event
    return None


def read_log_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        if not path.exists():
            continue
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
            yield from handle


def expand_log_paths(path: Path) -> list[Path]:
    matches = [Path(match) for match in glob.glob(str(path) + "*")]
    return sorted(matches, key=lambda candidate: (candidate.stat().st_mtime, candidate.name))


def markdown_escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def write_cases_yaml(cases: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cases": cases}
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_feedback_report(cases: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# v8std Search Feedback Cases",
        "",
        "| Query | Expected | Frequency | Dominance |",
        "| --- | --- | ---: | ---: |",
    ]
    for case in cases:
        feedback = case.get("feedback", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(case.get("query", "")),
                    markdown_escape(case.get("expected", "")),
                    str(feedback.get("frequency", "")),
                    str(feedback.get("dominance", "")),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build weak search benchmark cases from MCP usage logs.")
    parser.add_argument("--usage-log", action="append", type=Path, default=None)
    parser.add_argument("--cases-out", type=Path, default=Path("docs/ai/search-feedback-cases.yml"))
    parser.add_argument("--report", type=Path, default=Path("docs/ai/search-feedback-cases.md"))
    parser.add_argument("--window-seconds", type=int, default=DEFAULT_WINDOW_SECONDS)
    parser.add_argument("--min-frequency", type=int, default=DEFAULT_MIN_FREQUENCY)
    parser.add_argument("--dominance", type=float, default=DEFAULT_DOMINANCE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = args.usage_log or [DEFAULT_USAGE_LOG]
    paths: list[Path] = []
    for root in roots:
        expanded = expand_log_paths(root)
        paths.extend(expanded or [root])

    cases = build_feedback_cases(
        read_log_lines(paths),
        window_seconds=args.window_seconds,
        min_frequency=args.min_frequency,
        dominance=args.dominance,
    )
    write_cases_yaml(cases, args.cases_out)
    write_feedback_report(cases, args.report)
    print(f"cases={len(cases)} cases_out={args.cases_out} report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
