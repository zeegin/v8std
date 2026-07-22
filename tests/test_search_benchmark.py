import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from search_benchmark import parse_args, ranked_summary, read_case_payloads  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
