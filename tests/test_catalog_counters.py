import re
import unittest
from pathlib import Path

from scripts.diagnostic_inventory import diagnostic_family_counts


REPO_ROOT = Path(__file__).resolve().parents[1]


class CatalogCounterTests(unittest.TestCase):
    def test_home_page_standard_total_matches_standard_pages(self):
        expected_total = len(list((REPO_ROOT / "docs/std").glob("*.md")))
        home = (REPO_ROOT / "overrides/home.html").read_text(encoding="utf-8")
        match = re.search(
            r'<div class="v8std-home-metric">\s*'
            r'<strong>(\d+)</strong>\s*'
            r'<span>стандартов</span>',
            home,
        )

        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), expected_total)

    def test_home_page_catalog_counters_match_committed_catalogs(self):
        family_counts = diagnostic_family_counts(REPO_ROOT)
        expected = {
            "diagnostics/acc/": family_counts["acc"],
            "diagnostics/bslls/": family_counts["bslls"],
            "diagnostics/v8-code-style/": family_counts["v8-code-style"],
        }

        home = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
        for href, count in expected.items():
            match = re.search(
                rf'<a class="v8std-home-link-card" href="{re.escape(href)}">\s*'
                rf'<p class="v8std-home-link-card__eyebrow">(\d+) диагностик(?:а|и)?</p>',
                home,
            )
            self.assertIsNotNone(match, href)
            self.assertEqual(int(match.group(1)), count, href)

    def test_home_page_hero_total_matches_committed_catalogs(self):
        expected_total = sum(diagnostic_family_counts(REPO_ROOT).values())
        home = (REPO_ROOT / "overrides/home.html").read_text(encoding="utf-8")
        match = re.search(
            r'<div class="v8std-home-metric">\s*'
            r'<strong>(\d+)</strong>\s*'
            r'<span>диагностик</span>',
            home,
        )

        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), expected_total)


if __name__ == "__main__":
    unittest.main()
