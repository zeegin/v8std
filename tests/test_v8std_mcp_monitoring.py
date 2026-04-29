from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = REPO_ROOT / "scripts"
USAGE_LOGROTATE_PATH = SCRIPTS_PATH / "v8std_mcp_usage.logrotate"

if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

import v8std_mcp_monitoring as monitoring


NOW = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)


class V8StdMcpMonitoringTests(unittest.TestCase):
    def test_usage_logrotate_retains_search_history_for_one_year(self):
        config = USAGE_LOGROTATE_PATH.read_text(encoding="utf-8")

        self.assertIn("/var/lib/v8std-mcp/tool-usage.jsonl", config)
        self.assertIn("daily", config)
        self.assertIn("rotate 365", config)
        self.assertIn("compress", config)

    def test_build_report_focuses_on_mcp_and_separates_rate_limit_from_real_errors(self):
        report = monitoring.build_report(
            [
                'ts=2026-04-29T11:59:00+00:00 remote=203.0.113.10 method=POST uri=/mcp status=200 request_time=0.006 upstream_time=0.005 bytes=438 ua="codex-cli/0.8"',
                'ts=2026-04-29T11:58:00+00:00 remote=203.0.113.11 method=GET uri=/mcp status=200 request_time=0.001 upstream_time=0.001 bytes=972 ua="curl/8.7.1"',
                'ts=2026-04-29T11:57:00+00:00 remote=203.0.113.12 method=GET uri=/healthz status=200 request_time=0.002 upstream_time=0.002 bytes=2 ua="Uptime-Kuma/1.23"',
                'ts=2026-04-29T11:56:00+00:00 remote=203.0.113.13 method=POST uri=/mcp status=503 request_time=0.000 upstream_time=- bytes=197 ua="Claude Desktop"',
                'ts=2026-04-29T11:55:00+00:00 remote=203.0.113.14 method=POST uri=/mcp status=503 request_time=0.010 upstream_time=0.010 bytes=197 ua="Mozilla/5.0"',
                'ts=2026-04-29T11:54:00+00:00 remote=203.0.113.16 method=GET uri=/monitoring/stats.json status=200 request_time=0.000 upstream_time=- bytes=1200 ua="curl/8.7.1"',
                'ts=2026-04-29T11:53:00+00:00 remote=203.0.113.17 method=GET uri=/wp-login.php status=404 request_time=0.000 upstream_time=- bytes=120 ua="bot"',
                'ts=2026-04-28T11:59:00+00:00 remote=203.0.113.15 method=POST uri=/mcp status=200 request_time=0.002 upstream_time=0.002 bytes=48 ua="stale-client"',
            ],
            usage_lines=[
                '{"ts":"2026-04-29T11:59:30+00:00","tool":"v8std_search"}',
                '{"ts":"2026-04-29T11:58:30+00:00","tool":"v8std_search","system":"cursor","query":"модальные окна","results":[{"id":"std404","title":"Модальные окна","url":"https://v8std.ru/std/404/"},{"id":"std519","title":"Оповещения","url":"https://v8std.ru/std/519/"}]}',
                '{"ts":"2026-04-29T11:57:30+00:00","tool":"v8std_get_page","requested_page":"std437","page_id":"std437","title":"Оформление текстов запросов","url":"https://v8std.ru/std/437/"}',
                '{"ts":"2026-04-29T11:56:30+00:00","tool":"v8std_get_page","requested_page":"https://v8std.ru/std/437/","page_id":"std437","title":"Оформление текстов запросов","url":"https://v8std.ru/std/437/"}',
                '{"ts":"2026-04-29T11:55:30+00:00","tool":"v8std_explain_diagnostics","diagnostics":[{"id":"bslls:UsingModalWindows","title":"Использование модальных окон","url":"https://v8std.ru/diagnostics/bslls/UsingModalWindows/","frequency":2},{"id":"acc:1245","title":"Нельзя использовать * в запросах","url":"https://v8std.ru/diagnostics/acc/1245/","frequency":1},{"id":"external","title":"External","url":"https://example.com/","frequency":99}],"unknown_codes":[{"code":"v8cs:NewUnknownDiagnostic","frequency":3}],"standards_without_page":[{"id":"std999","title":"Стандарт без страницы","frequency":2}]}',
                '{"ts":"2026-04-28T11:57:30+00:00","tool":"v8std_get_page"}',
            ],
            now=NOW,
            window_hours=24,
            uptime={
                "service": "v8std-mcp.service",
                "active": True,
                "active_since": "2026-04-28T16:22:56+00:00",
                "seconds": 70424,
            },
        )

        self.assertEqual(report["totals"]["mcp_requests"], 3)
        self.assertEqual(report["totals"]["tool_calls"], 5)
        self.assertEqual(report["totals"]["rate_limited"], 1)
        self.assertNotIn("real_5xx", report["totals"])
        self.assertEqual(report["uptime"]["human"], "19h 33m")

        self.assertNotIn("request_types", report)

        systems = {item["key"]: item["count"] for item in report["systems"]}
        self.assertEqual(systems["codex"], 1)
        self.assertEqual(systems["curl"], 1)
        self.assertEqual(systems["claude"], 1)
        self.assertEqual(systems["browser"], 1)
        self.assertNotIn("monitoring", systems)

        tools = {item["key"]: item["count"] for item in report["tools"]}
        self.assertEqual(tools["v8std_search"], 2)
        self.assertEqual(tools["v8std_get_page"], 2)
        self.assertEqual(tools["v8std_explain_diagnostics"], 1)

        self.assertEqual(report["top_pages"][0]["count"], 2)
        self.assertEqual(report["top_pages"][0]["title"], "Оформление текстов запросов")
        self.assertEqual(report["top_pages"][0]["url"], "https://v8std.ru/std/437/")

        self.assertNotIn("top_searches", report)
        self.assertEqual(report["recent_searches"][0]["query"], "модальные окна")
        self.assertEqual(report["recent_searches"][0]["system"], "cursor")
        self.assertEqual(report["recent_searches"][0]["system_label"], "Cursor")
        self.assertEqual(report["recent_searches"][0]["results"][0]["url"], "https://v8std.ru/std/404/")

        diagnostics_by_id = {item["id"]: item for item in report["top_diagnostics"]}
        self.assertEqual(diagnostics_by_id["v8cs:NewUnknownDiagnostic"]["count"], 3)
        self.assertEqual(diagnostics_by_id["v8cs:NewUnknownDiagnostic"]["title"], "Неизвестная диагностика: v8cs:NewUnknownDiagnostic")
        self.assertEqual(diagnostics_by_id["v8cs:NewUnknownDiagnostic"]["url"], "")
        self.assertEqual(diagnostics_by_id["v8cs:NewUnknownDiagnostic"]["kind"], "unknown_code")
        self.assertEqual(diagnostics_by_id["bslls:UsingModalWindows"]["count"], 2)
        self.assertEqual(diagnostics_by_id["bslls:UsingModalWindows"]["title"], "Использование модальных окон")
        self.assertEqual(diagnostics_by_id["bslls:UsingModalWindows"]["url"], "https://v8std.ru/diagnostics/bslls/UsingModalWindows/")
        self.assertEqual(diagnostics_by_id["std999"]["count"], 2)
        self.assertEqual(diagnostics_by_id["std999"]["title"], "Стандарт без страницы: Стандарт без страницы")
        self.assertEqual(diagnostics_by_id["std999"]["url"], "")
        self.assertEqual(diagnostics_by_id["std999"]["kind"], "standard_without_page")
        self.assertEqual(diagnostics_by_id["acc:1245"]["count"], 1)
        self.assertEqual(diagnostics_by_id["acc:1245"]["url"], "https://v8std.ru/diagnostics/acc/1245/")
        self.assertNotIn("example.com", json.dumps(report["top_diagnostics"], ensure_ascii=False))

        self.assertNotIn("status_classes", report)

        other = {item["key"]: item["count"] for item in report["other_requests"]}
        self.assertEqual(other["GET /wp-login.php -> 404"], 1)
        self.assertNotIn("GET /healthz -> 200", other)
        self.assertNotIn("GET /monitoring/stats.json -> 200", other)

    def test_build_report_keeps_ten_latest_searches(self):
        usage_lines = [
            json.dumps(
                    {
                        "ts": f"2026-04-29T11:{index:02d}:00+00:00",
                        "tool": "v8std_search",
                        "system": "claude" if index % 2 else "cursor",
                        "query": f"query-{index}",
                    "results": [
                        {
                            "id": f"std{index}",
                            "title": f"Result {index}",
                            "url": f"https://v8std.ru/std/{index}/",
                        }
                    ],
                }
            )
            for index in range(11)
        ]

        report = monitoring.build_report(
            [],
            usage_lines=usage_lines,
            now=NOW,
            window_hours=24,
            uptime={"service": "v8std-mcp.service", "active": True, "seconds": 60},
        )

        self.assertEqual(len(report["recent_searches"]), 10)
        self.assertEqual([item["query"] for item in report["recent_searches"]], [f"query-{index}" for index in range(10, 0, -1)])
        self.assertEqual(report["recent_searches"][0]["system_label"], "Cursor")
        self.assertEqual(report["recent_searches"][1]["system_label"], "Claude")
        self.assertEqual(report["recent_searches"][0]["results"][0]["url"], "https://v8std.ru/std/10/")
        self.assertNotIn("top_searches", report)

    def test_render_page_ranking_splits_rows_by_column_not_by_grid_rows(self):
        items = [
            {
                "key": f"std{index}",
                "title": f"Page {index}",
                "url": f"https://v8std.ru/std/{index}/",
                "count": index,
            }
            for index in range(1, 5)
        ]

        html = monitoring.render_page_ranking(items)

        self.assertEqual(html.count('class="page-ranking__column"'), 2)
        first_column_start = html.index('class="page-ranking__column"')
        second_column_start = html.index('class="page-ranking__column"', first_column_start + 1)

        self.assertLess(html.index('<div class="rank-row__index">1</div>'), second_column_start)
        self.assertLess(html.index('<div class="rank-row__index">2</div>'), second_column_start)
        self.assertGreater(html.index('<div class="rank-row__index">3</div>'), second_column_start)
        self.assertGreater(html.index('<div class="rank-row__index">4</div>'), second_column_start)

    def test_render_html_is_mcp_focused_and_omits_raw_clients_and_nginx_details(self):
        report = monitoring.build_report(
            [
                'ts=2026-04-29T11:59:00+00:00 remote=203.0.113.10 method=POST uri=/mcp status=200 request_time=0.006 upstream_time=0.005 bytes=438 ua="codex-cli/0.8"',
                'ts=2026-04-29T11:56:00+00:00 remote=203.0.113.13 method=POST uri=/mcp status=503 request_time=0.000 upstream_time=- bytes=197 ua="Claude Desktop"',
                'ts=2026-04-29T11:53:00+00:00 remote=203.0.113.17 method=GET uri=/wp-login.php status=404 request_time=0.000 upstream_time=- bytes=120 ua="bot"',
            ],
            usage_lines=[
                '{"ts":"2026-04-29T11:59:30+00:00","tool":"v8std_search","system":"cursor","query":"модальные окна","results":[{"id":"std404","title":"Модальные окна","url":"https://v8std.ru/std/404/"}]}',
                '{"ts":"2026-04-29T11:58:30+00:00","tool":"v8std_get_page","requested_page":"std437","page_id":"std437","title":"Оформление текстов запросов","url":"https://v8std.ru/std/437/"}',
                '{"ts":"2026-04-29T11:57:30+00:00","tool":"v8std_explain_diagnostics","diagnostics":[{"id":"bslls:UsingModalWindows","title":"Использование модальных окон","url":"https://v8std.ru/diagnostics/bslls/UsingModalWindows/","frequency":2}],"unknown_codes":[{"code":"v8cs:NewUnknownDiagnostic","frequency":1}],"standards_without_page":[{"id":"std999","title":"Стандарт без страницы","frequency":1}]}',
            ],
            now=NOW,
            window_hours=24,
            uptime={"service": "v8std-mcp.service", "active": True, "seconds": 3600},
        )

        html = monitoring.render_html(report)

        self.assertIn("Мониторинг v8std MCP", html)
        self.assertIn("MCP запросы", html)
        self.assertIn("Tool calls", html)
        self.assertNotIn("Реальные 5xx", html)
        self.assertIn("Прочие запросы", html)
        self.assertIn("GET /wp-login.php -&gt; 404", html)
        self.assertIn("v8std_search", html)
        self.assertIn("Топ страниц get_page", html)
        self.assertIn("Последние 10 запросов search", html)
        self.assertNotIn("Топ запросов search", html)
        self.assertIn("Топ диагностик explain_diagnostics", html)
        self.assertIn("https://v8std.ru/std/437/", html)
        self.assertIn("https://v8std.ru/std/404/", html)
        self.assertIn("https://v8std.ru/diagnostics/bslls/UsingModalWindows/", html)
        self.assertIn("Использование модальных окон", html)
        self.assertIn("Cursor", html)
        self.assertIn("Неизвестная диагностика: v8cs:NewUnknownDiagnostic", html)
        self.assertIn("Стандарт без страницы: Стандарт без страницы", html)
        self.assertIn('<section class="rank-stack">', html)
        self.assertIn('<div class="page-ranking">', html)
        self.assertIn("page-ranking__column", html)
        self.assertIn(".page-ranking__column .rank-row:first-child", html)
        self.assertNotIn("column-count: 2", html)
        self.assertIn('<div class="search-ranking">', html)
        self.assertIn('<div class="search-results">', html)
        self.assertLess(html.index("Последние 10 запросов search"), html.index("Топ диагностик explain_diagnostics"))
        self.assertLess(html.index("Топ диагностик explain_diagnostics"), html.index("Топ страниц get_page"))
        self.assertNotIn("rank-grid", html)
        self.assertNotIn("result-links", html)
        self.assertIn('rel="icon" href="data:,"', html)
        self.assertNotIn("MCP обращения", html)
        self.assertNotIn("Коды MCP", html)
        self.assertNotIn("203.0.113.10", html)
        self.assertNotIn("codex-cli/0.8", html)
        self.assertNotIn("nginx", html.lower())

    def test_write_dashboard_outputs_html_and_json(self):
        report = monitoring.build_report(
            [
                'ts=2026-04-29T11:59:00+00:00 remote=203.0.113.10 method=POST uri=/mcp status=200 request_time=0.001 upstream_time=0.001 bytes=2 ua="curl/8.7.1"',
            ],
            usage_lines=['{"ts":"2026-04-29T11:59:30+00:00","tool":"v8std_search"}'],
            now=NOW,
            window_hours=24,
            uptime={"service": "v8std-mcp.service", "active": True, "seconds": 60},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            monitoring.write_dashboard(report, output_dir)

            html = (output_dir / "index.html").read_text(encoding="utf-8")
            payload = json.loads((output_dir / "stats.json").read_text(encoding="utf-8"))

        self.assertIn("<!doctype html>", html)
        self.assertEqual(payload["totals"]["mcp_requests"], 1)
        self.assertEqual(payload["tools"][0]["key"], "v8std_search")
        self.assertEqual(payload["top_pages"], [])
        self.assertEqual(payload["recent_searches"], [])
        self.assertNotIn("top_searches", payload)
        self.assertEqual(payload["top_diagnostics"], [])


if __name__ == "__main__":
    unittest.main()
