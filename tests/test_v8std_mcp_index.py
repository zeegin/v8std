import unittest
from pathlib import Path

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from v8std_mcp_index import V8StdIndex, normalize_lookup_key, normalize_page_schema  # noqa: E402


class V8StdMcpIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vectors_path = REPO_ROOT / "docs" / "ai" / "search-vectors.jsonl"
        cls.index = V8StdIndex(
            pages_path=REPO_ROOT / "docs" / "ai" / "pages.jsonl",
            vectors_path=vectors_path if vectors_path.exists() else None,
        )
        cls.index.load()

    def test_normalizes_common_ids_aliases_and_urls(self):
        self.assertEqual(normalize_lookup_key("#std437"), "std437")
        self.assertEqual(normalize_lookup_key("стандарт 437"), "std437")
        self.assertEqual(normalize_lookup_key("АПК:1245"), "acc:1245")
        self.assertEqual(normalize_lookup_key("acc361"), "acc:361")
        self.assertEqual(
            normalize_lookup_key("https://v8std.ru/diagnostics/bslls/AssignAliasFieldsInQuery/"),
            "bslls:assignaliasfieldsinquery",
        )

    def test_hybrid_search_finds_standards_and_diagnostics(self):
        std_results = self.index.search("std437", limit=3)["results"]
        acc_results = self.index.search("acc:1245", limit=3)["results"]
        bslls_results = self.index.search("AssignAliasFieldsInQuery", limit=3)["results"]

        self.assertEqual(std_results[0]["id"], "std437")
        self.assertEqual(acc_results[0]["id"], "acc:1245")
        self.assertEqual(bslls_results[0]["id"], "bslls:AssignAliasFieldsInQuery")
        self.assertIn("match_reasons", std_results[0])
        self.assertIn("score_details", std_results[0])

    def test_rules_cover_semantic_and_code_like_queries(self):
        separation = self.index.search(
            "форма не должна содержать бизнес-логику и доступ к данным",
            limit=3,
        )["results"]
        query_allowed = self.index.search(
            'Запрос = Новый Запрос("ВЫБРАТЬ РАЗРЕШЕННЫЕ ...")',
            limit=3,
        )["results"]
        modal = self.index.search("ОткрытьФормуМодально Предупреждение Вопрос", limit=3)[
            "results"
        ]
        log_event = self.index.search("ЗаписьЖурналаРегистрации", limit=3)["results"]

        self.assertEqual(separation[0]["id"], "patterns:engineering:separation_of_concerns")
        self.assertEqual(query_allowed[0]["id"], "std415")
        self.assertEqual(modal[0]["id"], "bslls:UsingModalWindows")
        self.assertEqual(log_event[0]["id"], "std498")

    def test_search_validates_types_and_modes(self):
        with self.assertRaises(ValueError):
            self.index.search("std437", types="standard")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.index.search("std437", types=["bad"])
        with self.assertRaises(ValueError):
            self.index.search("std437", mode="bad")

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

    def test_page_and_related_use_exact_alias_resolution(self):
        page = self.index.page("#std437")["page"]
        related = self.index.related("std437")["related"]

        self.assertEqual(page["id"], "std437")
        self.assertTrue(
            any(item["id"] == "bslls:AssignAliasFieldsInQuery" for item in related)
        )

    def test_explain_snippet_and_batch_diagnostics(self):
        snippet = self.index.explain_snippet(
            'Запрос = Новый Запрос("ВЫБРАТЬ РАЗРЕШЕННЫЕ ...")'
        )
        batch = self.index.explain_diagnostics(["acc 1245", "АПК:361", "bad"])

        self.assertTrue(any(item["id"] == "std415" for item in snippet["standards"]))
        self.assertTrue(any(item["id"] == "acc:1245" for item in batch["diagnostics"]))
        self.assertTrue(any(item["code"] == "bad" for item in batch["unknown_codes"]))


if __name__ == "__main__":
    unittest.main()
