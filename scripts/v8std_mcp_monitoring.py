#!/usr/bin/env python3

from __future__ import annotations

import argparse
import gzip
import html
import json
import shlex
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator


DEFAULT_ACCESS_LOG = Path("/var/log/nginx/ai.v8std.ru.access.log")
DEFAULT_USAGE_LOG = Path("/var/lib/v8std-mcp/tool-usage.jsonl")
DEFAULT_OUTPUT_DIR = Path("/var/www/ai.v8std.ru-monitoring")
DEFAULT_SERVICE = "v8std-mcp.service"
DEFAULT_WINDOW_HOURS = 24
TOP_RANKING_LIMIT = 50
RECENT_SEARCH_LIMIT = 10
MAX_SEARCH_RESULTS_PER_QUERY = 50

SYSTEM_LABELS = {
    "codex": "Codex",
    "claude": "Claude",
    "cursor": "Cursor",
    "jetbrains": "JetBrains",
    "vscode": "VS Code",
    "monitoring": "Monitoring",
    "curl": "curl",
    "browser": "Browser",
    "unknown": "Unknown",
    "other": "Other",
}

TOOL_LABELS = {
    "v8std_search": "v8std_search",
    "v8std_get_page": "v8std_get_page",
    "v8std_get_related": "v8std_get_related",
    "v8std_explain_snippet": "v8std_explain_snippet",
    "v8std_explain_diagnostics": "v8std_explain_diagnostics",
}

IGNORED_NON_MCP_PATHS = {"/", "/healthz", "/version", "/monitoring"}

def parse_log_line(line: str) -> dict[str, str] | None:
    try:
        parts = shlex.split(line)
    except ValueError:
        return None

    fields: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key] = value
    return fields if "ts" in fields else None


def parse_iso_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_mcp_request(uri: str) -> bool:
    return uri.split("?", 1)[0] in {"/mcp", "/mcp/"}


def is_ignored_non_mcp_request(uri: str) -> bool:
    path = uri.split("?", 1)[0]
    return path in IGNORED_NON_MCP_PATHS or path.startswith("/monitoring/")


def classify_other_request(method: str, uri: str, status: int | None) -> str:
    path = uri.split("?", 1)[0] or "/"
    if len(path) > 80:
        path = f"{path[:77]}..."
    status_text = str(status) if status is not None else "unknown"
    return f"{method.upper() or 'UNKNOWN'} {path} -> {status_text}"


def classify_system(user_agent: str) -> str:
    ua = user_agent.strip().lower()
    if not ua or ua == "-":
        return "unknown"
    if "codex" in ua or "openai" in ua:
        return "codex"
    if "claude" in ua or "anthropic" in ua:
        return "claude"
    if "cursor" in ua:
        return "cursor"
    if "jetbrains" in ua or "intellij" in ua or "pycharm" in ua or "webstorm" in ua:
        return "jetbrains"
    if "vscode" in ua or "visual studio code" in ua:
        return "vscode"
    if "uptime" in ua or "health" in ua or "monitor" in ua or "prometheus" in ua:
        return "monitoring"
    if "curl" in ua:
        return "curl"
    if "mozilla/" in ua or "safari/" in ua or "chrome/" in ua or "firefox/" in ua:
        return "browser"
    return "other"


def is_rate_limited(fields: dict[str, str], status: int | None) -> bool:
    uri = fields.get("uri", "")
    upstream_time = fields.get("upstream_time", "")
    return status in {429, 503} and uri.split("?", 1)[0] in {"/mcp", "/mcp/"} and upstream_time in {"", "-"}


def parse_usage_line(line: str) -> dict[str, object] | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    ts = payload.get("ts")
    tool = payload.get("tool")
    if not isinstance(ts, str) or not isinstance(tool, str):
        return None
    return payload


def public_text(value: object, *, limit: int = 240) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text:
        return None
    return text[:limit]


def public_system(value: object) -> str:
    system = public_text(value, limit=80)
    if system is None:
        return "unknown"
    system = system.lower()
    if system in SYSTEM_LABELS:
        return system
    return "unknown"


def public_url(value: object) -> str | None:
    url = public_text(value, limit=500)
    if url is None or not url.startswith("https://v8std.ru/"):
        return None
    return url


def public_result(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    url = public_url(value.get("url"))
    if url is None:
        return None
    result = {"url": url}
    item_id = public_text(value.get("id"), limit=120)
    title = public_text(value.get("title"))
    if item_id:
        result["id"] = item_id
    if title:
        result["title"] = title
    return result


def public_ranked_item(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    raw_url = public_text(value.get("url"), limit=500)
    url = public_url(value.get("url"))
    if raw_url and url is None:
        return None
    item_id = public_text(value.get("id"), limit=120)
    code = public_text(value.get("code"), limit=120)
    title = public_text(value.get("title"))
    result: dict[str, str] = {}
    if item_id:
        result["id"] = item_id
    elif code:
        result["id"] = code
    if title:
        result["title"] = title
    if url:
        result["url"] = url
    return result or None


def public_frequency(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(1, min(value, TOP_RANKING_LIMIT * 10))
    return 1


def add_diagnostic_ranking_item(
    requests: Counter[str],
    metadata: dict[str, dict[str, str]],
    *,
    item_id: str,
    title: str,
    frequency: int,
    kind: str,
    url: str = "",
) -> None:
    key = f"{kind}:{url or item_id or title}"
    requests[key] += frequency
    metadata.setdefault(
        key,
        {
            "key": key,
            "id": item_id,
            "title": title,
            "url": url,
            "kind": kind,
        },
    )


def human_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "unknown"
    total_minutes = max(0, int(seconds) // 60)
    days, day_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(day_minutes, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def normalize_uptime(uptime: dict[str, object] | None) -> dict[str, object]:
    payload = {
        "service": DEFAULT_SERVICE,
        "active": None,
        "active_since": None,
        "seconds": None,
        "human": "unknown",
        "restarts": None,
    }
    if uptime:
        payload.update(uptime)
    if payload.get("active") is False:
        payload["human"] = "down"
    elif "human" not in payload or payload["human"] == "unknown":
        payload["human"] = human_duration(payload.get("seconds"))  # type: ignore[arg-type]
    return payload


def counter_items(counter: Counter[str], labels: dict[str, str]) -> list[dict[str, object]]:
    items = [
        {
            "key": key,
            "label": labels.get(key, key),
            "count": count,
        }
        for key, count in counter.items()
        if count > 0
    ]
    return sorted(items, key=lambda item: (-int(item["count"]), str(item["label"])))


def build_report(
    log_lines: Iterable[str],
    *,
    usage_lines: Iterable[str] | None = None,
    now: datetime | None = None,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    uptime: dict[str, object] | None = None,
) -> dict[str, object]:
    generated_at = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    window_start = generated_at - timedelta(hours=window_hours)
    future_cutoff = generated_at + timedelta(minutes=5)

    systems: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    other_requests: Counter[str] = Counter()
    page_requests: Counter[str] = Counter()
    page_metadata: dict[str, dict[str, str]] = {}
    search_events: list[tuple[datetime, dict[str, object]]] = []
    diagnostic_requests: Counter[str] = Counter()
    diagnostic_metadata: dict[str, dict[str, str]] = {}
    mcp_requests = 0
    rate_limited = 0

    for line in log_lines:
        fields = parse_log_line(line)
        if not fields:
            continue

        ts = parse_iso_datetime(fields.get("ts", ""))
        if ts is None or ts < window_start or ts > future_cutoff:
            continue

        try:
            status = int(fields.get("status", ""))
        except ValueError:
            status = None

        uri = fields.get("uri", "")
        method = fields.get("method", "")
        limited = is_rate_limited(fields, status)
        if limited:
            rate_limited += 1

        if is_mcp_request(uri):
            if uri.split("?", 1)[0] == "/mcp" and method.upper() == "POST":
                mcp_requests += 1
            systems[classify_system(fields.get("ua", ""))] += 1
            continue

        if not is_ignored_non_mcp_request(uri):
            other_requests[classify_other_request(method, uri, status)] += 1

    for line in usage_lines or []:
        usage = parse_usage_line(line)
        if not usage:
            continue
        ts = parse_iso_datetime(usage["ts"])
        if ts is None or ts < window_start or ts > future_cutoff:
            continue
        tool = usage["tool"]
        tools[tool] += 1
        if tool == "v8std_get_page":
            url = public_url(usage.get("url"))
            page_id = public_text(usage.get("page_id"), limit=120)
            requested_page = public_text(usage.get("requested_page"), limit=120)
            title = public_text(usage.get("title")) or page_id or requested_page or url
            page_key = url or page_id or requested_page
            if page_key:
                page_requests[page_key] += 1
                page_metadata.setdefault(
                    page_key,
                    {
                        "key": page_key,
                        "title": title or page_key,
                        "url": url or "",
                    },
                )
        elif tool == "v8std_search":
            query = public_text(usage.get("query"))
            if query:
                system = public_system(usage.get("system"))
                results = []
                seen = set()
                raw_results = usage.get("results")
                if isinstance(raw_results, list):
                    for raw_result in raw_results:
                        result = public_result(raw_result)
                        if result is None or result["url"] in seen:
                            continue
                        seen.add(result["url"])
                        results.append(result)
                        if len(results) >= MAX_SEARCH_RESULTS_PER_QUERY:
                            break
                search_events.append(
                    (
                        ts,
                        {
                            "ts": ts.replace(microsecond=0).isoformat(),
                            "query": query,
                            "system": system,
                            "system_label": SYSTEM_LABELS[system],
                            "results": results,
                        },
                    )
                )
        elif tool == "v8std_explain_diagnostics":
            raw_diagnostics = usage.get("diagnostics")
            if isinstance(raw_diagnostics, list):
                for raw_diagnostic in raw_diagnostics:
                    diagnostic = public_ranked_item(raw_diagnostic)
                    if diagnostic is None:
                        continue
                    diagnostic_id = diagnostic.get("id") or diagnostic.get("url") or diagnostic.get("title")
                    if not diagnostic_id:
                        continue
                    frequency = public_frequency(raw_diagnostic.get("frequency") if isinstance(raw_diagnostic, dict) else None)
                    add_diagnostic_ranking_item(
                        diagnostic_requests,
                        diagnostic_metadata,
                        item_id=diagnostic_id,
                        title=diagnostic.get("title") or diagnostic_id,
                        url=diagnostic.get("url", ""),
                        frequency=frequency,
                        kind="diagnostic",
                    )
            raw_unknown_codes = usage.get("unknown_codes")
            if isinstance(raw_unknown_codes, list):
                for raw_unknown_code in raw_unknown_codes:
                    if not isinstance(raw_unknown_code, dict):
                        continue
                    code = public_text(raw_unknown_code.get("code"), limit=120)
                    if code is None:
                        continue
                    add_diagnostic_ranking_item(
                        diagnostic_requests,
                        diagnostic_metadata,
                        item_id=code,
                        title=f"Неизвестная диагностика: {code}",
                        frequency=public_frequency(raw_unknown_code.get("frequency")),
                        kind="unknown_code",
                    )
            raw_standards = usage.get("standards_without_page")
            if isinstance(raw_standards, list):
                for raw_standard in raw_standards:
                    standard = public_ranked_item(raw_standard)
                    if standard is None or standard.get("url"):
                        continue
                    standard_id = standard.get("id") or standard.get("title")
                    if not standard_id:
                        continue
                    standard_title = standard.get("title") or standard_id
                    add_diagnostic_ranking_item(
                        diagnostic_requests,
                        diagnostic_metadata,
                        item_id=standard_id,
                        title=f"Стандарт без страницы: {standard_title}",
                        frequency=public_frequency(raw_standard.get("frequency") if isinstance(raw_standard, dict) else None),
                        kind="standard_without_page",
                    )

    tool_items = counter_items(tools, TOOL_LABELS)
    tool_calls = sum(int(item["count"]) for item in tool_items)
    top_pages = [
        {**page_metadata[key], "count": count}
        for key, count in page_requests.most_common(TOP_RANKING_LIMIT)
    ]
    recent_searches = [
        event
        for _ts, event in sorted(search_events, key=lambda item: item[0], reverse=True)[:RECENT_SEARCH_LIMIT]
    ]
    top_diagnostics = [
        {**diagnostic_metadata[key], "count": count}
        for key, count in diagnostic_requests.most_common(TOP_RANKING_LIMIT)
    ]

    return {
        "generated_at": generated_at.replace(microsecond=0).isoformat(),
        "window_hours": window_hours,
        "window_start": window_start.replace(microsecond=0).isoformat(),
        "totals": {
            "mcp_requests": mcp_requests,
            "tool_calls": tool_calls,
            "rate_limited": rate_limited,
        },
        "tools": tool_items,
        "top_pages": top_pages,
        "recent_searches": recent_searches,
        "top_diagnostics": top_diagnostics,
        "systems": counter_items(systems, SYSTEM_LABELS),
        "other_requests": counter_items(other_requests, {}),
        "uptime": normalize_uptime(uptime),
    }


def read_log_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        if not path.exists():
            continue
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
            yield from handle


def expand_access_logs(path: Path) -> list[Path]:
    candidates = [path, path.with_name(f"{path.name}.1"), path.with_name(f"{path.name}.1.gz")]
    return [candidate for candidate in candidates if candidate.exists()]


def parse_systemd_timestamp(value: str) -> datetime | None:
    if not value or value == "n/a":
        return None
    parts = value.split(maxsplit=1)
    if len(parts) == 2 and "," not in parts[0]:
        value = parts[1]
    for fmt in ("%Y-%m-%d %H:%M:%S.%f %Z", "%Y-%m-%d %H:%M:%S %Z"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=timezone.utc)
    return None


def read_service_uptime(service: str, *, now: datetime | None = None) -> dict[str, object]:
    generated_at = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    result = subprocess.run(
        [
            "systemctl",
            "show",
            service,
            "-p",
            "ActiveState",
            "-p",
            "ActiveEnterTimestamp",
            "-p",
            "NRestarts",
            "--no-pager",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    fields = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key] = value

    active_since = parse_systemd_timestamp(fields.get("ActiveEnterTimestamp", ""))
    active = fields.get("ActiveState") == "active" if fields else None
    seconds = None
    if active and active_since:
        seconds = max(0, int((generated_at - active_since).total_seconds()))
    try:
        restarts: int | None = int(fields["NRestarts"])
    except (KeyError, ValueError):
        restarts = None

    return {
        "service": service,
        "active": active,
        "active_since": active_since.isoformat() if active_since else fields.get("ActiveEnterTimestamp") or None,
        "seconds": seconds,
        "restarts": restarts,
    }


def metric_card(label: str, value: object, detail: str) -> str:
    return (
        '<section class="metric">'
        f'<div class="metric__label">{html.escape(label)}</div>'
        f'<div class="metric__value">{html.escape(str(value))}</div>'
        f'<div class="metric__detail">{html.escape(detail)}</div>'
        "</section>"
    )


def render_bar_list(items: list[dict[str, object]], empty_text: str) -> str:
    if not items:
        return f'<p class="empty">{html.escape(empty_text)}</p>'
    max_count = max(int(item["count"]) for item in items) or 1
    rows = []
    for item in items:
        count = int(item["count"])
        width = max(4, round(count / max_count * 100))
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-row__top"><span>{html.escape(str(item["label"]))}</span><strong>{count}</strong></div>'
            '<div class="bar-row__track">'
            f'<div class="bar-row__fill" style="width: {width}%"></div>'
            "</div>"
            "</div>"
        )
    return "\n".join(rows)


def render_link(url: object, label: object) -> str:
    url_text = public_url(url)
    label_text = public_text(label) or url_text or ""
    if url_text is None:
        return html.escape(label_text)
    return f'<a href="{html.escape(url_text)}">{html.escape(label_text)}</a>'


def render_page_ranking(items: list[dict[str, object]]) -> str:
    if not items:
        return '<p class="empty">Данных по v8std_get_page пока нет.</p>'
    rows = []
    limited_items = items[:TOP_RANKING_LIMIT]
    for index, item in enumerate(limited_items, start=1):
        title = item.get("title") or item.get("key") or item.get("url")
        rows.append(
            '<div class="rank-row">'
            f'<div class="rank-row__index">{index}</div>'
            '<div class="rank-row__body">'
            f'<div class="rank-row__title">{render_link(item.get("url"), title)}</div>'
            f'<div class="rank-row__meta">{html.escape(str(item.get("url") or item.get("key") or ""))}</div>'
            "</div>"
            f'<strong class="rank-row__count">{int(item["count"])}</strong>'
            "</div>"
        )
    split_index = (len(rows) + 1) // 2
    columns = [rows[:split_index], rows[split_index:]]
    return "\n".join(
        '<div class="page-ranking__column">' + "\n".join(column_rows) + "</div>"
        for column_rows in columns
        if column_rows
    )


def render_search_time(value: object) -> str:
    if not isinstance(value, str):
        return ""
    ts = parse_iso_datetime(value)
    if ts is None:
        return ""
    return ts.strftime("%H:%M UTC")


def render_search_ranking(items: list[dict[str, object]]) -> str:
    if not items:
        return '<p class="empty">Данных по v8std_search пока нет.</p>'
    rows = []
    for index, item in enumerate(items[:TOP_RANKING_LIMIT], start=1):
        results = item.get("results")
        result_rows = []
        if isinstance(results, list):
            for result_index, result in enumerate(results[:MAX_SEARCH_RESULTS_PER_QUERY], start=1):
                if isinstance(result, dict):
                    title = result.get("title") or result.get("id") or result.get("url")
                    meta = result.get("url") or result.get("id") or ""
                    result_rows.append(
                        '<div class="search-result-row">'
                        f'<div class="rank-row__index">{index}.{result_index}</div>'
                        '<div class="rank-row__body">'
                        f'<div class="rank-row__title">{render_link(result.get("url"), title)}</div>'
                        f'<div class="rank-row__meta">{html.escape(str(meta))}</div>'
                        "</div>"
                        "</div>"
                    )
        rendered_results = (
            '<div class="search-results">' + "\n".join(result_rows) + "</div>"
            if result_rows
            else '<div class="rank-row__meta">Результатов в логе нет.</div>'
        )
        rows.append(
            '<div class="search-entry">'
            '<div class="rank-row">'
            f'<div class="rank-row__index">{index}</div>'
            '<div class="rank-row__body">'
            f'<div class="rank-row__title">{html.escape(str(item["query"]))}</div>'
            f'<div class="rank-row__meta">{html.escape(str(item.get("system_label") or "Unknown"))} · запрос v8std_search</div>'
            "</div>"
            f'<strong class="rank-row__count">{html.escape(render_search_time(item.get("ts")))}</strong>'
            "</div>"
            f"{rendered_results}"
            "</div>"
        )
    return "\n".join(rows)


def render_diagnostic_ranking(items: list[dict[str, object]]) -> str:
    if not items:
        return '<p class="empty">Данных по v8std_explain_diagnostics пока нет.</p>'
    kind_labels = {
        "unknown_code": "неизвестная диагностика",
        "standard_without_page": "стандарт без страницы",
    }
    rows = []
    for index, item in enumerate(items[:TOP_RANKING_LIMIT], start=1):
        title = item.get("title") or item.get("id") or item.get("key") or item.get("url")
        diagnostic_id = public_text(item.get("id"), limit=120)
        kind = public_text(item.get("kind"), limit=80)
        meta_parts = []
        if kind in kind_labels:
            meta_parts.append(kind_labels[kind])
        if diagnostic_id:
            meta_parts.append(diagnostic_id)
        meta = " · ".join(meta_parts) or item.get("url") or item.get("key") or ""
        rows.append(
            '<div class="rank-row">'
            f'<div class="rank-row__index">{index}</div>'
            '<div class="rank-row__body">'
            f'<div class="rank-row__title">{render_link(item.get("url"), title)}</div>'
            f'<div class="rank-row__meta">{html.escape(str(meta))}</div>'
            "</div>"
            f'<strong class="rank-row__count">{int(item["count"])}</strong>'
            "</div>"
        )
    return "\n".join(rows)


def render_html(report: dict[str, object]) -> str:
    totals = report["totals"]  # type: ignore[assignment]
    uptime = report["uptime"]  # type: ignore[assignment]
    tools = report["tools"]  # type: ignore[assignment]
    top_pages = report["top_pages"]  # type: ignore[assignment]
    recent_searches = report["recent_searches"]  # type: ignore[assignment]
    top_diagnostics = report["top_diagnostics"]  # type: ignore[assignment]
    systems = report["systems"]  # type: ignore[assignment]
    other_requests = report["other_requests"]  # type: ignore[assignment]
    generated_at = str(report["generated_at"])
    window_hours = int(report["window_hours"])
    active = "active" if uptime.get("active") else "not active" if uptime.get("active") is False else "unknown"  # type: ignore[attr-defined]

    metrics = "\n".join(
        [
            metric_card("MCP запросы", totals["mcp_requests"], f"Последние {window_hours} часа"),  # type: ignore[index]
            metric_card("Tool calls", totals["tool_calls"], "вызовы MCP tools"),  # type: ignore[index]
            metric_card("Rate limit", totals["rate_limited"], "отклонено лимитом"),  # type: ignore[index]
            metric_card("Аптайм MCP", uptime.get("human", "unknown"), f'{uptime.get("service", DEFAULT_SERVICE)}: {active}'),  # type: ignore[attr-defined]
        ]
    )

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <link rel="icon" href="data:,">
  <title>Мониторинг v8std MCP</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fa;
      --surface: #ffffff;
      --surface-soft: #eef3f7;
      --text: #17202a;
      --muted: #657386;
      --border: #d9e1ea;
      --accent: #0f766e;
      --blue: #2563eb;
      --warn: #b45309;
      --danger: #b91c1c;
      --shadow: 0 8px 24px rgba(23, 32, 42, 0.07);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-width: 320px;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 40px;
    }}
    header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(24px, 4vw, 34px);
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .stamp {{
      flex: 0 0 auto;
      color: var(--muted);
      font-size: 13px;
      text-align: right;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .metric, .panel {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .metric {{
      min-height: 118px;
      padding: 16px;
    }}
    .metric__label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .metric__value {{
      margin-top: 10px;
      font-size: 30px;
      font-weight: 700;
      line-height: 1;
    }}
    .metric__detail {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      padding: 18px;
    }}
    .panel + .panel {{
      margin-top: 16px;
    }}
    .grid > .panel + .panel {{
      margin-top: 0;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 17px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    .bar-row + .bar-row {{
      margin-top: 14px;
    }}
    .bar-row__top {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 6px;
    }}
    .bar-row__top span {{
      min-width: 0;
      overflow-wrap: anywhere;
    }}
    .bar-row__top strong {{
      font-variant-numeric: tabular-nums;
    }}
    .bar-row__track {{
      width: 100%;
      height: 8px;
      overflow: hidden;
      border-radius: 4px;
      background: var(--surface-soft);
    }}
    .bar-row__fill {{
      height: 100%;
      border-radius: 4px;
      background: var(--accent);
    }}
    .side .bar-row__fill {{
      background: var(--blue);
    }}
    .tools .bar-row__fill {{
      background: var(--accent);
    }}
    .wide {{
      margin-top: 16px;
    }}
    .rank-stack {{
      display: grid;
      gap: 16px;
      margin-top: 16px;
    }}
    .page-ranking {{
      display: grid;
      grid-template-columns: 1fr;
      column-gap: 24px;
      align-items: start;
    }}
    .page-ranking__column + .page-ranking__column .rank-row:first-child {{
      border-top: 1px solid var(--surface-soft);
      padding-top: 10px;
    }}
    .rank-row {{
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr) auto;
      gap: 12px;
      align-items: start;
      padding: 10px 0;
      border-top: 1px solid var(--surface-soft);
    }}
    .rank-row:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    .rank-row__index {{
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }}
    .rank-row__body {{
      min-width: 0;
    }}
    .rank-row__title {{
      font-weight: 650;
      overflow-wrap: anywhere;
    }}
    .rank-row__meta {{
      margin-top: 2px;
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .rank-row__count {{
      font-variant-numeric: tabular-nums;
    }}
    .search-entry {{
      border-top: 1px solid var(--surface-soft);
      padding: 12px 0;
    }}
    .search-entry:first-of-type {{
      border-top: 0;
      padding-top: 0;
    }}
    .search-entry .rank-row {{
      border-top: 0;
      padding: 0;
    }}
    .search-results {{
      margin: 8px 0 0 40px;
      border-left: 2px solid var(--surface-soft);
    }}
    .search-result-row {{
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      padding: 8px 0 8px 12px;
      border-top: 1px solid var(--surface-soft);
    }}
    .search-result-row:first-child {{
      border-top: 0;
    }}
    .empty {{
      margin: 0;
      color: var(--muted);
    }}
    footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 12px;
    }}
    a {{
      color: var(--blue);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    @media (max-width: 820px) {{
      main {{
        width: min(100% - 24px, 1120px);
        padding-top: 24px;
      }}
      header {{
        display: block;
      }}
      .stamp {{
        margin-top: 10px;
        text-align: left;
      }}
      .metrics, .grid {{
        grid-template-columns: 1fr;
      }}
      .search-results {{
        margin-left: 0;
      }}
    }}
    @media (min-width: 821px) {{
      .page-ranking {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .page-ranking__column .rank-row:first-child {{
        border-top: 0;
        padding-top: 0;
      }}
    }}
    @media (min-width: 821px) and (max-width: 1040px) {{
      .metrics {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Мониторинг v8std MCP</h1>
      </div>
      <div class="stamp">Обновлено<br>{html.escape(generated_at)}</div>
    </header>

    <section class="metrics" aria-label="Ключевые метрики">
      {metrics}
    </section>

    <section class="grid">
      <section class="panel tools">
        <h2>MCP tools</h2>
        {render_bar_list(tools, "Вызовов tools/call после включения счетчика пока нет.")}
      </section>

      <section class="panel">
        <h2>Системы</h2>
        {render_bar_list(systems, "User-Agent по MCP пока не накоплен.")}
      </section>
    </section>

    <section class="rank-stack">
      <section class="panel">
        <h2>Последние 10 запросов search</h2>
        <div class="search-ranking">
          {render_search_ranking(recent_searches)}
        </div>
      </section>

      <section class="panel">
        <h2>Топ диагностик explain_diagnostics</h2>
        {render_diagnostic_ranking(top_diagnostics)}
      </section>

      <section class="panel">
        <h2>Топ страниц get_page</h2>
        <div class="page-ranking">
          {render_page_ranking(top_pages)}
        </div>
      </section>
    </section>

    <section class="panel wide">
      <h2>Прочие запросы</h2>
      {render_bar_list(other_requests[:10], "Прочих запросов нет.")}
    </section>

    <footer>
      Данные агрегированы без IP-адресов и исходных User-Agent.
      JSON: <a href="stats.json">stats.json</a>
    </footer>
  </main>
</body>
</html>
"""


def write_dashboard(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"
    json_path = output_dir / "stats.json"
    html_tmp = output_dir / ".index.html.tmp"
    json_tmp = output_dir / ".stats.json.tmp"

    html_tmp.write_text(render_html(report), encoding="utf-8")
    json_tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_tmp.replace(html_path)
    json_tmp.replace(json_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a static public dashboard for the v8std MCP endpoint.")
    parser.add_argument("--access-log", action="append", type=Path, default=None)
    parser.add_argument("--usage-log", action="append", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--service", default=DEFAULT_SERVICE)
    parser.add_argument("--window-hours", type=int, default=DEFAULT_WINDOW_HOURS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    access_logs = args.access_log or [DEFAULT_ACCESS_LOG]
    log_paths: list[Path] = []
    for access_log in access_logs:
        expanded = expand_access_logs(access_log)
        log_paths.extend(expanded or [access_log])
    usage_logs = args.usage_log or [DEFAULT_USAGE_LOG]
    usage_paths: list[Path] = []
    for usage_log in usage_logs:
        expanded = expand_access_logs(usage_log)
        usage_paths.extend(expanded or [usage_log])

    now = datetime.now(timezone.utc)
    report = build_report(
        read_log_lines(log_paths),
        usage_lines=read_log_lines(usage_paths),
        now=now,
        window_hours=args.window_hours,
        uptime=read_service_uptime(args.service, now=now),
    )
    write_dashboard(report, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
