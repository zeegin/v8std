import base64
import json
import os
import struct
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from v8std_mcp_index import (  # noqa: E402
    IndexLoadError,
    VECTOR_DIM,
    V8StdIndex,
    normalize_lookup_key,
    normalize_page_schema,
)


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

    def test_generated_code_aliases_are_top_ranked(self):
        layout_results = self.index.search("ыев437", limit=3)["results"]
        bare_number_results = self.index.search("#437", limit=3)["results"]
        acc_layout_results = self.index.search("фсс361", limit=3)["results"]

        self.assertEqual(layout_results[0]["id"], "std437")
        self.assertIn("keyboard_layout", layout_results[0]["score_details"])
        self.assertEqual(bare_number_results[0]["id"], "std437")
        self.assertIn("code_variant", bare_number_results[0]["score_details"])
        self.assertEqual(acc_layout_results[0]["id"], "acc:361")
        self.assertIn("keyboard_layout", acc_layout_results[0]["score_details"])

    def test_fuzzy_code_lookup_is_limited_to_code_like_queries(self):
        fuzzy_results = self.index.search("AssignToReadOnlyProperti", limit=3)["results"]
        exact_results = self.index.search("AssignAliasFieldsInQuery", limit=3)["results"]
        compact_results = self.index.search("acc361", limit=3)["results"]
        prose_results = self.index.search("запрос в цикле производительность", limit=5)["results"]

        self.assertEqual(fuzzy_results[0]["id"], "bslls:AssignToReadOnlyProperty")
        self.assertIn("fuzzy_code", fuzzy_results[0]["score_details"])
        self.assertNotIn("fuzzy_code", exact_results[0]["score_details"])
        self.assertNotIn("fuzzy_code", compact_results[0]["score_details"])
        self.assertFalse(
            any("fuzzy_code" in item["score_details"] for item in prose_results)
        )

    def test_generated_numeric_aliases_do_not_pollute_code_snippet_search(self):
        results = self.index.search(
            'ПарольSMTP = "qwerty123";\n'
            "Соединение = Новый HTTPСоединение(Сервер, 443,,,, ПарольSMTP);",
            limit=5,
        )["results"]

        self.assertIn("std740", [item["id"] for item in results[:3]])
        self.assertFalse(
            any(item["id"] == "std791" and "alias" in item["score_details"] for item in results)
        )

    def test_field_aware_scoring_prefers_specific_metadata_match(self):
        diagnostic_results = self.index.search(
            "общий модуль клиент сервер должен оканчиваться на КлиентСервер",
            types=["diagnostic"],
            limit=3,
        )["results"]
        role_results = self.index.search(
            "видимость элементов формы по ролям при большом количестве ролей",
            types=["standard"],
            limit=5,
        )["results"]

        self.assertEqual(diagnostic_results[0]["id"], "v8cs:common-module-name-client-server")
        self.assertIn("metadata_coverage", diagnostic_results[0]["score_details"])
        self.assertIn("std737", [item["id"] for item in role_results[:3]])

    def test_explain_snippet_detects_hardcoded_secret_literal(self):
        result = self.index.explain_snippet(
            'ПарольSMTP = "qwerty123";\n'
            "Соединение = Новый HTTPСоединение(Сервер, 443,,,, ПарольSMTP);",
            limit=5,
        )

        self.assertTrue(any(item["id"] == "std740" for item in result["standards"][:3]))
        self.assertTrue(
            any(signal["type"] == "secret_literal" for signal in result["signals"])
        )

    def test_hybrid_search_finds_ui_design_standards(self):
        exact_results = self.index.search("std500", types=["standard"], limit=3)["results"]
        title_results = self.index.search(
            "общие правила построения интерфейсов",
            types=["standard"],
            limit=5,
        )["results"]

        self.assertEqual(exact_results[0]["id"], "std500")
        self.assertEqual(title_results[0]["id"], "std500")

    def test_rules_cover_semantic_and_code_like_queries(self):
        separation = self.index.search(
            "форма не должна содержать бизнес-логику и доступ к данным",
            limit=3,
        )["results"]
        query_allowed = self.index.search(
            'Запрос = Новый Запрос("ВЫБРАТЬ РАЗРЕШЕННЫЕ ...")',
            limit=3,
        )["results"]
        modal = self.index.search("модальные окна в управляемом приложении", limit=3)["results"]
        log_event = self.index.search("журнал регистрации", limit=3)["results"]

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

    def test_related_merges_rules_and_normalizes_relation_filters(self):
        modal_related = self.index.related("bslls:UsingModalWindows")["related"]
        modal_batch = self.index.explain_diagnostics(["bslls:UsingModalWindows"])
        canonical = self.index.related("std456", relations=["standard"])["related"]
        legacy = self.index.related("std456", relations=["related_standard"])["related"]

        modal_standards = [item for item in modal_related if item["relation"] == "standard"]
        self.assertEqual([item["id"] for item in modal_standards], ["std703"])
        self.assertEqual(modal_standards[0]["url"], "https://v8std.ru/std/703/#1")
        self.assertEqual(modal_batch["standards"][0]["id"], "std703")
        self.assertEqual(modal_batch["standards"][0]["url"], "https://v8std.ru/std/703/#1")
        self.assertTrue(any(item["id"] == "std437" for item in canonical))
        self.assertTrue(
            any(item["id"] == "std437" and item["relation"] == "standard" for item in legacy)
        )
        with self.assertRaises(ValueError):
            self.index.related("std456", relations=["bad"])

    def test_related_and_batch_preserve_multiple_clauses_of_one_standard(self):
        related = self.index.related("bslls:DeprecatedCurrentDate")["related"]
        batch = self.index.explain_diagnostics(["bslls:DeprecatedCurrentDate"])
        expected = {
            "https://v8std.ru/std/643/#21",
            "https://v8std.ru/std/643/#31",
        }

        self.assertEqual(
            {item["url"] for item in related if item["id"] == "std643"},
            expected,
        )
        self.assertEqual(
            {item["url"] for item in batch["standards"] if item["id"] == "std643"},
            expected,
        )

    def test_explain_snippet_and_batch_diagnostics(self):
        snippet = self.index.explain_snippet(
            'Запрос = Новый Запрос("ВЫБРАТЬ РАЗРЕШЕННЫЕ ...")'
        )
        modal_call = self.index.explain_snippet('Предупреждение("Текст");')
        modal_identifier = self.index.explain_snippet("Предупреждение = Новый Структура;")
        batch = self.index.explain_diagnostics(["acc 1245", "АПК:361", "bad"])

        self.assertTrue(any(item["id"] == "std415" for item in snippet["standards"]))
        self.assertTrue(any(item["id"] == "bslls:UsingModalWindows" for item in modal_call["diagnostics"]))
        self.assertFalse(
            any(item["id"] == "bslls:UsingModalWindows" for item in modal_identifier["diagnostics"])
        )
        self.assertTrue(any(item["id"] == "acc:1245" for item in batch["diagnostics"]))
        self.assertTrue(any(item["code"] == "bad" for item in batch["unknown_codes"]))

    def test_security_input_limits(self):
        with self.assertRaises(ValueError):
            self.index.search("x" * 501)
        with self.assertRaises(ValueError):
            self.index.page("x" * 1001)
        with self.assertRaises(ValueError):
            self.index.related("x" * 1001)
        with self.assertRaises(ValueError):
            self.index.explain_snippet("x" * 4001)
        with self.assertRaises(ValueError):
            self.index.explain_diagnostics(["acc:1"] * 501)
        with self.assertRaises(ValueError):
            self.index.explain_diagnostics(["x" * 201])

    def test_remote_cache_fetches_stale_cache_and_falls_back_on_error(self):
        fresh_payload = '{"id":"std999","type":"standard","title":"Fresh"}\n'
        stale_payload = '{"id":"std111","type":"standard","title":"Stale"}\n'

        class FetchingIndex(V8StdIndex):
            def __init__(self, *args, fail: bool = False, **kwargs):
                super().__init__(*args, **kwargs)
                self.fail = fail
                self.fetches = []

            def _fetch_url(self, url: str, *, max_bytes: int) -> str:
                self.fetches.append(url)
                if self.fail or url != self.index_url:
                    raise URLError("offline")
                return fresh_payload

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache_path = cache_dir / "pages.jsonl"
            cache_path.write_text(stale_payload, encoding="utf-8")
            old_time = time.time() - 7200
            os.utime(cache_path, (old_time, old_time))

            index = FetchingIndex(
                index_url="https://example.test/pages.jsonl",
                vectors_url="https://example.test/search-vectors.jsonl",
                cache_dir=cache_dir,
                refresh_seconds=3600,
            )
            index.load()

            self.assertEqual(index.metadata.source, "https://example.test/pages.jsonl")
            self.assertIsNotNone(index.resolve("std999"))
            self.assertIsNone(index.resolve("std111"))

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache_path = cache_dir / "pages.jsonl"
            cache_path.write_text(stale_payload, encoding="utf-8")
            old_time = time.time() - 7200
            os.utime(cache_path, (old_time, old_time))

            index = FetchingIndex(
                index_url="https://example.test/pages.jsonl",
                vectors_url="https://example.test/search-vectors.jsonl",
                cache_dir=cache_dir,
                refresh_seconds=3600,
                fail=True,
            )
            index.load()

            self.assertEqual(index.metadata.source, str(cache_path))
            self.assertIsNotNone(index.resolve("std111"))

    def test_remote_resource_cache_uses_ttl_and_fallback(self):
        pages_payload = '{"id":"std111","type":"standard","title":"Cached"}\n'

        class ResourceIndex(V8StdIndex):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fail = False
                self.fetches = []
                self.payloads = {"https://v8std.ru/llms.txt": "fresh llms"}

            def _fetch_url(self, url: str, *, max_bytes: int) -> str:
                self.fetches.append(url)
                if self.fail or url not in self.payloads:
                    raise URLError("offline")
                return self.payloads[url]

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            (cache_dir / "pages.jsonl").write_text(pages_payload, encoding="utf-8")
            (cache_dir / "search-vectors.jsonl").write_text("", encoding="utf-8")
            llms_cache = cache_dir / "llms.txt"
            llms_cache.write_text("cached llms", encoding="utf-8")

            index = ResourceIndex(cache_dir=cache_dir, refresh_seconds=3600)
            index.load()
            self.assertEqual(index.fetches, [])

            self.assertEqual(index.read_resource_text("llms.txt"), "cached llms")
            self.assertEqual(index.fetches, [])

            old_time = time.time() - 7200
            os.utime(llms_cache, (old_time, old_time))
            self.assertEqual(index.read_resource_text("llms.txt"), "fresh llms")
            self.assertEqual(index.fetches, ["https://v8std.ru/llms.txt"])

            os.utime(llms_cache, (old_time, old_time))
            index.fail = True
            self.assertEqual(index.read_resource_text("llms.txt"), "fresh llms")
            self.assertEqual(index.fetches[-1], "https://v8std.ru/llms.txt")

    def test_fetch_url_rejects_oversized_payload(self):
        class FakeResponse:
            status = 200
            headers = {}

            def __init__(self, payload: bytes):
                self.payload = payload
                self.offset = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size: int = -1) -> bytes:
                if self.offset >= len(self.payload):
                    return b""
                if size < 0:
                    size = len(self.payload) - self.offset
                chunk = self.payload[self.offset:self.offset + size]
                self.offset += len(chunk)
                return chunk

        with patch("v8std_mcp_index.urlopen", return_value=FakeResponse(b"x" * 11)):
            with self.assertRaises(IndexLoadError):
                V8StdIndex()._fetch_url("https://example.test/index.jsonl", max_bytes=10)

    def test_vector_parser_rejects_unsafe_payloads(self):
        good_vector = base64.b64encode(struct.pack(f"<{VECTOR_DIM}f", *([0.0] * VECTOR_DIM))).decode()
        small_vector = base64.b64encode(struct.pack("<4f", *([0.0] * 4))).decode()

        def vector_row(**overrides):
            row = {
                "id": "std111",
                "field": "body",
                "chunk_index": 0,
                "model": "v8std-hash-embeddings-v1",
                "dim": VECTOR_DIM,
                "vector_base64": good_vector,
            }
            row.update(overrides)
            return row

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pages_path = temp_path / "pages.jsonl"
            vectors_path = temp_path / "search-vectors.jsonl"
            pages_path.write_text(
                '{"id":"std111","type":"standard","title":"Cached"}\n',
                encoding="utf-8",
            )

            invalid_payloads = [
                vector_row(dim=4, vector_base64=small_vector),
                vector_row(vector_base64="A" * 8193),
                [
                    vector_row(model="model-a"),
                    vector_row(model="model-b", chunk_index=1),
                ],
            ]
            for payload in invalid_payloads:
                rows = payload if isinstance(payload, list) else [payload]
                vectors_path.write_text(
                    "\n".join(json.dumps(row) for row in rows) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaises(IndexLoadError):
                    V8StdIndex(pages_path=pages_path, vectors_path=vectors_path).load()


if __name__ == "__main__":
    unittest.main()
