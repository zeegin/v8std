import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dev.checks.search_benchmark import main, parse_args, ranked_summary, read_case_payloads  # noqa: E402


class SearchBenchmarkTests(unittest.TestCase):
    def test_default_report_is_written_outside_docs_tree(self):
        with patch("sys.argv", ["search_benchmark.py"]):
            args = parse_args()

        self.assertEqual(args.report, Path(".cache/search-benchmark.md"))

    def test_extra_cases_are_optional_and_tagged_as_feedback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            static_path = temp_path / "static.yml"
            missing_extra_path = temp_path / "missing.yml"
            extra_path = temp_path / "extra.yml"

            static_path.write_text(
                "thresholds:\n  mrr: 0.9\ncases:\n- scenario: static\n  query: std437\n  expected: std437\n",
                encoding="utf-8",
            )
            extra_path.write_text(
                "cases:\n- scenario: feedback\n  query: запрос в цикле\n  expected: std436\n",
                encoding="utf-8",
            )

            cases, thresholds = read_case_payloads(static_path, missing_extra_path)
            self.assertEqual([case["_case_source"] for case in cases], ["static"])
            self.assertEqual(thresholds["mrr"], 0.9)

            cases, thresholds = read_case_payloads(static_path, extra_path)

        self.assertEqual([case["_case_source"] for case in cases], ["static", "feedback"])
        self.assertEqual(thresholds["mrr"], 0.9)

    def test_ranked_summary_can_be_filtered_by_case_source(self):
        records = [
            {"tool": "search", "rank": 1, "ok": True, "_case_source": "static"},
            {"tool": "search", "rank": 3, "ok": True, "_case_source": "feedback"},
            {"tool": "search", "rank": None, "ok": False, "_case_source": "feedback"},
            {"tool": "diagnostics", "rank": None, "ok": True, "_case_source": "feedback"},
        ]

        static_summary = ranked_summary(records, source="static")
        feedback_summary = ranked_summary(records, source="feedback")

        self.assertEqual(static_summary["ranked_cases"], 1)
        self.assertEqual(static_summary["top3_hits"], 1)
        self.assertEqual(static_summary["mrr"], 1.0)
        self.assertEqual(feedback_summary["ranked_cases"], 2)
        self.assertEqual(feedback_summary["top3_hits"], 1)
        self.assertAlmostEqual(feedback_summary["mrr"], 1 / 6)

    def test_max_total_cases_fail_when_search_returns_more(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cases_path = temp_path / "cases.yml"
            report_path = temp_path / "report.md"
            cases_path.write_text(
                "cases:\n"
                "- scenario: nonsense\n  query: zzzqqqxyz\n  max_total: 0\n"
                "- scenario: real topic\n  query: std437\n  max_total: 0\n",
                encoding="utf-8",
            )
            stderr = io.StringIO()
            argv = ["search_benchmark.py", "--cases", str(cases_path), "--report", str(report_path)]
            with patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(stderr):
                code = main()
            report = report_path.read_text(encoding="utf-8")

        self.assertEqual(code, 1)
        self.assertIn("real topic: 'std437': expected total <= 0", stderr.getvalue())
        self.assertNotIn("nonsense", stderr.getvalue())
        self.assertIn("total <= 0", report)

    def test_static_cases_pin_empty_results_for_nonsense_queries(self):
        cases, _thresholds = read_case_payloads(REPO_ROOT / "tests" / "search_benchmark_cases.yml")
        bounded = {case["query"]: case["max_total"] for case in cases if "max_total" in case}

        self.assertEqual(bounded.get("zzzqqqxyz"), 0)
        self.assertEqual(bounded.get("абырвалг"), 0)
        self.assertLessEqual(bounded.get("как сварить борщ", 99), 3)


if __name__ == "__main__":
    unittest.main()
