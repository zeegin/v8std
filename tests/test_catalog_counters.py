import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CatalogCounterTests(unittest.TestCase):
    def test_home_page_catalog_counters_match_committed_catalogs(self):
        source_catalog = json.loads(
            (REPO_ROOT / "data/diagnostic-sources.json").read_text(encoding="utf-8")
        )
        family_counts = {
            family["family"]: len(family["diagnostics"])
            for family in source_catalog["families"]
        }
        acc_count = len(
            json.loads(
                (REPO_ROOT / "data/acc-diagnostics.json").read_text(encoding="utf-8")
            )["diagnostics"]
        )
        expected = {
            "diagnostics/acc/": acc_count,
            "diagnostics/bslls/": family_counts["bslls"],
            "diagnostics/v8-code-style/": family_counts["v8-code-style"],
        }
        self.assertEqual(expected["diagnostics/acc/"], 691)
        self.assertEqual(expected["diagnostics/bslls/"], 186)
        self.assertEqual(expected["diagnostics/v8-code-style/"], 172)

        home = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
        for href, count in expected.items():
            match = re.search(
                rf'<a class="v8std-home-link-card" href="{re.escape(href)}">\s*'
                rf'<p class="v8std-home-link-card__eyebrow">(\d+) диагностик(?:а|и)?</p>',
                home,
            )
            self.assertIsNotNone(match, href)
            self.assertEqual(int(match.group(1)), count, href)


if __name__ == "__main__":
    unittest.main()
