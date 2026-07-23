import tempfile
import unittest
from pathlib import Path

from scripts.autoformat_fixes import load_autoformat_catalog
from scripts.diagnostic_standard_links import rewrite_standard_page
from scripts.generate_diagnostic_standard_links import (
    load_standard_pages,
    render_registry_index,
)


ROOT = Path(__file__).resolve().parents[1]


class AutoformatCatalogTests(unittest.TestCase):
    def test_catalog_has_unique_rule_keys_and_existing_targets(self):
        catalog = load_autoformat_catalog(ROOT / "data/autoformat-fixes.json")
        self.assertEqual(len(catalog.fixes), 34)
        self.assertEqual(len({fix.key for fix in catalog.fixes}), 34)
        for fix in catalog.fixes:
            self.assertTrue((ROOT / "docs/std" / f"{fix.standard[3:]}.md").is_file())

    def test_catalog_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(
                '{"version":1,"tool_url":"x","download_url":"x",'
                '"artifact_sha256":"' + "0" * 64 + '","fixes":[],"extra":true}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unexpected fields"):
                load_autoformat_catalog(path)

    def test_registry_and_standard_page_use_one_autoformat_link(self):
        catalog = load_autoformat_catalog(ROOT / "data/autoformat-fixes.json")
        pages = load_standard_pages(ROOT / "docs/std")
        registry = render_registry_index((), pages, catalog.fixes)
        self.assertIn("1 исправление", registry)
        self.assertIn('href="autoformat/index.md">autoformat</a>', registry)

        source = (ROOT / "docs/std/765.md").read_text(encoding="utf-8")
        rewritten = rewrite_standard_page(source, "std765", (), catalog.fixes)
        self.assertIn('aria-label="Исправления"', rewritten)
        self.assertEqual(
            rewritten.count(
                'href="../diagnostics/autoformat/index.md">autoformat</a>'
            ),
            5,
        )


if __name__ == "__main__":
    unittest.main()
