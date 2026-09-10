import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from snippet_benchmark import within_budget, summarize_series


class SnippetBenchmarkTests(unittest.TestCase):
    def test_median_of_three_p95_values_rejects_single_fast_series(self):
        series = [list(range(1, 21)), list(range(2, 42, 2)), list(range(3, 63, 3))]
        result = summarize_series(series)
        self.assertEqual(result["series_p95_ms"], [19, 38, 57])
        self.assertEqual(result["p95_ms"], 38)

    def test_budget_uses_larger_of_relative_and_absolute_allowance(self):
        for baseline, current, relative, absolute, expected in (
            (100, 120, .2, 10, True), (100, 120.01, .2, 10, False),
            (1, 11, .2, 10, True), (1, 11.01, .2, 10, False),
            (100, 125, .25, 20, True), (100, 125.01, .25, 20, False),
            (1, 21, .25, 20, True), (1, 21.01, .25, 20, False),
        ):
            with self.subTest(baseline=baseline, current=current):
                self.assertEqual(within_budget(baseline, current, relative, absolute), expected)
