import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from search_feedback_cases import (  # noqa: E402
    build_feedback_cases,
    sanitize_query,
    write_feedback_report,
)


def usage_line(**payload):
    return json.dumps(payload, ensure_ascii=False)


class SearchFeedbackCasesTests(unittest.TestCase):
    def test_builds_case_from_repeated_search_to_page_transition(self):
        lines = [
            usage_line(
                tool="v8std_search",
                ts="2026-06-21T10:00:00+00:00",
                system="node",
                query="запрос в цикле",
            ),
            usage_line(
                tool="v8std_get_page",
                ts="2026-06-21T10:01:00+00:00",
                system="node",
                page_id="std436",
                url="https://v8std.ru/std/436/",
            ),
            usage_line(
                tool="v8std_search",
                ts="2026-06-21T11:00:00+00:00",
                system="node",
                query="запрос в цикле",
            ),
            usage_line(
                tool="v8std_get_page",
                ts="2026-06-21T11:01:00+00:00",
                system="node",
                page_id="std436",
                url="https://v8std.ru/std/436/",
            ),
        ]

        cases = build_feedback_cases(lines, window_seconds=180, min_frequency=2, dominance=0.6)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["query"], "запрос в цикле")
        self.assertEqual(cases[0]["expected"], "std436")
        self.assertEqual(cases[0]["required_top"], 3)
        self.assertEqual(cases[0]["feedback"]["frequency"], 2)

    def test_excludes_late_and_ambiguous_transitions(self):
        lines = [
            usage_line(tool="v8std_search", ts="2026-06-21T10:00:00+00:00", system="node", query="x"),
            usage_line(tool="v8std_get_page", ts="2026-06-21T10:04:00+00:00", system="node", page_id="std436"),
            usage_line(tool="v8std_search", ts="2026-06-21T11:00:00+00:00", system="node", query="ambiguous"),
            usage_line(tool="v8std_get_page", ts="2026-06-21T11:00:30+00:00", system="node", page_id="std436"),
            usage_line(tool="v8std_search", ts="2026-06-21T12:00:00+00:00", system="node", query="ambiguous"),
            usage_line(tool="v8std_get_page", ts="2026-06-21T12:00:30+00:00", system="node", page_id="std437"),
        ]

        cases = build_feedback_cases(lines, window_seconds=180, min_frequency=2, dominance=0.6)

        self.assertEqual(cases, [])

    def test_sanitizes_raw_queries_in_case_and_report_output(self):
        lines = [
            usage_line(tool="v8std_search", ts="2026-06-21T10:00:00+00:00", system="node", query="```bsl\nПароль = 'secret'\n```"),
            usage_line(tool="v8std_get_page", ts="2026-06-21T10:00:30+00:00", system="node", page_id="std740"),
            usage_line(tool="v8std_search", ts="2026-06-21T11:00:00+00:00", system="node", query="```bsl\nПароль = 'secret'\n```"),
            usage_line(tool="v8std_get_page", ts="2026-06-21T11:00:30+00:00", system="node", page_id="std740"),
        ]

        cases = build_feedback_cases(lines, window_seconds=180, min_frequency=2, dominance=0.6)

        self.assertEqual(cases[0]["query"], sanitize_query("```bsl\nПароль = 'secret'\n```"))
        self.assertNotIn("\n", cases[0]["query"])
        self.assertNotIn("```", cases[0]["query"])

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.md"
            write_feedback_report(cases, report_path)
            report = report_path.read_text(encoding="utf-8")

        self.assertNotIn("```", report)
        self.assertNotIn("\nПароль", report)


if __name__ == "__main__":
    unittest.main()
