import unittest
from pathlib import Path


import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from v8std_mcp_index import V8StdIndex, normalize_lookup_key, normalize_page_schema  # noqa: E402


class V8StdMcpIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = V8StdIndex(pages_path=REPO_ROOT / "docs" / "ai" / "pages.jsonl")
        cls.index.load()

    def test_normalizes_common_ids_aliases_and_urls(self):
        self.assertEqual(normalize_lookup_key("#std437"), "std437")
        self.assertEqual(normalize_lookup_key("стандарт 437"), "std437")
        self.assertEqual(normalize_lookup_key("АПК:1245"), "acc:1245")
        self.assertEqual(
            normalize_lookup_key("https://v8std.ru/diagnostics/bslls/AssignAliasFieldsInQuery/"),
            "bslls:assignaliasfieldsinquery",
        )

    def test_search_finds_standards_and_diagnostics(self):
        std_results = self.index.search("std437", limit=3)["results"]
        acc_results = self.index.search("acc:1245", limit=3)["results"]
        bslls_results = self.index.search("AssignAliasFieldsInQuery", limit=3)["results"]

        self.assertEqual(std_results[0]["id"], "std437")
        self.assertEqual(acc_results[0]["id"], "acc:1245")
        self.assertEqual(bslls_results[0]["id"], "bslls:AssignAliasFieldsInQuery")

    def test_normalizes_legacy_rows_without_markdown_url(self):
        row = normalize_page_schema(
            {
                "id": "std437",
                "source_path": "std/437.md",
                "url": "https://v8std.ru/std/437/",
            }
        )

        self.assertEqual(row["markdown_url"], "https://v8std.ru/std/437.md")
        self.assertEqual(row["aliases"], ["std437"])
        self.assertEqual(row["related"], [])

    def test_get_and_related_use_exact_alias_resolution(self):
        page = self.index.get("#std437")["page"]
        related = self.index.related("std437")["related"]

        self.assertEqual(page["id"], "std437")
        self.assertTrue(
            any(item["id"] == "bslls:AssignAliasFieldsInQuery" for item in related)
        )

    def test_explain_diagnostic_returns_linked_standards(self):
        payload = self.index.explain_diagnostic("acc 1245")

        self.assertTrue(payload["found"])
        self.assertEqual(payload["diagnostic"]["id"], "acc:1245")
        self.assertTrue(payload["standards"])


if __name__ == "__main__":
    unittest.main()
