from __future__ import annotations

import contextlib
import io
import json
import os
import random
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from runtime.v8std_mcp_index import V8StdIndex, truncate_for_query
from scripts.v8std_retrieval_rules import (
    RetrievalRule, RetrievalRules, SECRET_ASSIGNMENT_RE, SECRET_IDENTIFIER_RE, has_secret_literal,
)
from runtime.v8std_mcp_server import McpToolUsageLogger, build_server, main, parse_args
from starlette.testclient import TestClient


SIGNAL_CASES = (
    ('ПарольSMTP = "qwerty123";', "std740"),
    ("УстановитьПривилегированныйРежим(Истина);", "std485"),
    ('Запрос = Новый Запрос("ВЫБРАТЬ РАЗРЕШЕННЫЕ ...");', "std415"),
    ('Предупреждение("Текст");', "bslls:UsingModalWindows"),
)


def procedure(size: int, signal: str, position: str = "end") -> str:
    """Pad with real unrelated statements, keeping the input length exact."""
    padding_size = size - len(signal) - 2
    if padding_size < 0:
        raise ValueError("fixture too small")
    filler = "ВычислитьЗначение(Объект);\n"
    padding = (filler * (padding_size // len(filler) + 1))[:padding_size]
    offset = {"start": 0, "middle": len(padding) // 2, "end": len(padding)}[position]
    return padding[:offset] + "\n" + signal + "\n" + padding[offset:]


def result_ids(result: dict) -> list[str]:
    return [item["id"] for field in ("diagnostics", "standards") for item in result[field]]


def loaded_index(**kwargs) -> V8StdIndex:
    index = V8StdIndex(pages_path=ROOT / "docs/ai/pages.jsonl",
                       vectors_path=ROOT / "docs/ai/search-vectors.jsonl", **kwargs)
    index.load()
    return index


class SnippetRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = loaded_index()

    def test_response_deduplication_does_not_change_ordinary_query_term_weights(self):
        query = (SIGNAL_CASES[2][0] + "\n") * 2
        tokens = self.index._query_tokens(query)
        # Baseline: two query occurrences + two signal occurrences, identifier
        # expansion and the canonical term. Multiplicity is existing search policy.
        self.assertEqual(tokens.count("выбрать"), 7)
        self.assertEqual(tokens.count("разрешенные"), 7)

    def test_primary_target_survives_every_position_and_one_search_budget(self):
        for signal, expected in SIGNAL_CASES:
            for position in ("start", "middle", "end"):
                with self.subTest(expected=expected, position=position):
                    with patch.object(self.index, "search", wraps=self.index.search) as search:
                        try:
                            result = self.index.explain_snippet(procedure(4000, signal, position), limit=1)
                        except ValueError as error:
                            self.fail(f"accepted procedure failed: {error}")
                    self.assertEqual(result_ids(result), [expected])
                    self.assertEqual(search.call_count, 1)
                    self.assertLessEqual(len(search.call_args.args[0]), 500)

    def test_all_primary_targets_precede_secondary_targets_with_one_total_limit(self):
        source = procedure(4000, "\n".join(signal for signal, _ in SIGNAL_CASES))
        result = self.index.explain_snippet(source, limit=4)
        self.assertEqual(set(result_ids(result)), {"std740", "std485", "std415", "bslls:UsingModalWindows"})
        for limit in (1, 2, 3, 10, 50):
            with self.subTest(limit=limit):
                first = self.index.explain_snippet(source, limit=limit)
                second = self.index.explain_snippet(source, limit=limit)
                self.assertEqual(first, second)
                self.assertLessEqual(len(result_ids(first)), limit)
                self.assertEqual(len(result_ids(first)), len(set(result_ids(first))))

    def test_text_score_cannot_displace_a_primary_signal(self):
        noise = self.index.search("std437", limit=1)["results"][0]
        noise["score"] = 1_000_000_000
        with patch.object(self.index, "search", return_value={"results": [noise]}):
            result = self.index.explain_snippet(SIGNAL_CASES[1][0], limit=1)
        self.assertEqual(result_ids(result), ["std485"])
        entry = result["standards"][0]
        self.assertEqual(entry["score_details"]["snippet_signal"], 4200)
        self.assertIn("snippet_signal:privileged_mode", entry["match_reasons"])

    def test_missing_target_does_not_hide_an_existing_one(self):
        analysis = {"normalized_text": "", "tokens": [], "signals": [
            {"type": "sdbl_keyword", "value": "test", "target_ids": ["std999999", "std485"]},
        ]}
        with patch.object(self.index.rules, "analyze_snippet", return_value=analysis):
            result = self.index.explain_snippet("test", limit=2)
        self.assertEqual(result_ids(result), ["std485"])
        self.assertEqual(result["signals"][0]["target_ids"], ["std999999", "std485"])

    def test_repeated_signals_have_one_bonus_and_one_response_entry(self):
        signal = SIGNAL_CASES[2][0]
        for count in (1, 30):
            with self.subTest(count=count):
                result = self.index.explain_snippet((signal + "\n") * count, limit=1)
                self.assertEqual(len(result["signals"]), 1)
                self.assertEqual(result_ids(result), ["std415"])
                self.assertEqual(result["standards"][0]["score_details"]["snippet_signal"], 4200)

    def test_primary_priority_wins_when_target_also_has_secondary_evidence(self):
        rules = RetrievalRules([
            RetrievalRule("first", "std498", (), ("Первый",), (), ("std485",)),
            RetrievalRule("second", "std485", (), ("Второй",), (), ()),
        ])
        with patch.object(self.index, "rules", rules), patch.object(self.index, "search", return_value={"results": []}):
            result = self.index.explain_snippet("Первый(); Второй();", limit=2)
        self.assertEqual(set(result_ids(result)), {"std498", "std485"})
        for entry in result["standards"]:
            self.assertEqual(entry["score_details"]["snippet_signal"], 4200)

    def test_identifier_without_call_is_not_a_call_signal(self):
        result = self.index.explain_snippet("Предупреждение = Новый Структура;")
        self.assertFalse(any(item["type"] == "snippet_call" for item in result["signals"]))
        self.assertNotIn("bslls:UsingModalWindows", result_ids(result))

    def test_empty_input_keeps_empty_result_shape(self):
        self.assertEqual(self.index.explain_snippet(" \n"), {
            "language": "auto", "normalized_text": "", "tokens": [], "signals": [],
            "diagnostics": [], "standards": [], "confidence": 0.0,
        })


class SnippetPreviewTests(unittest.TestCase):
    def test_query_truncation_keeps_whole_words_when_a_boundary_exists(self):
        self.assertEqual(truncate_for_query("alpha " + "z" * 600), "alpha")
        self.assertEqual(truncate_for_query("z" * 600), "z" * 500)
        self.assertEqual(truncate_for_query("x" * 500), "x" * 500)

    @classmethod
    def setUpClass(cls):
        cls.rules = RetrievalRules.load(ROOT / "retrieval-rules.yml")

    def test_long_token_is_not_echoed_or_used_to_truncate_signal_scan(self):
        analysis = self.rules.analyze_snippet("я" * 5000 + "\n" + SIGNAL_CASES[1][0])
        self.assertEqual(analysis["tokens"], [])
        self.assertEqual(len(analysis["normalized_text"]), 1000)
        self.assertTrue(any("std485" in signal["target_ids"] for signal in analysis["signals"]))

    def test_token_preview_is_whole_prefix_with_two_budgets(self):
        tokens = ["т" * 99 + str(i) for i in range(200)]
        analysis = self.rules.analyze_snippet(" ".join(tokens))
        self.assertLessEqual(len(analysis["tokens"]), 80)
        self.assertLessEqual(sum(map(len, analysis["tokens"])), 4000)
        self.assertEqual(analysis["tokens"], tokens[:len(analysis["tokens"])])
        short = self.rules.analyze_snippet(" ".join("имя" + str(i) for i in range(100)))
        self.assertEqual(len(short["tokens"]), 80)

    def test_shared_analysis_preserves_signal_occurrences_for_ordinary_search(self):
        analysis = self.rules.analyze_snippet((SIGNAL_CASES[2][0] + "\n") * 500)
        self.assertEqual(len(analysis["signals"]), 500)
        self.assertEqual(analysis["signals"][0]["target_ids"], ["std415"])

    def test_secret_scanner_preserves_assignment_consumption_and_literal_semantics(self):
        for source, expected in (
            ('Пароль = "abcd"', True), ('Пароль = "abc"', False),
            ('foo = "secret = \'abcd\'"', False), ('Пароль = "&parameter"', False),
            ('foo = "abcd"; Пароль = "efgh"', True),
            ('я' * 31900 + 'Пароль = "abcd"', True),
            ('1Пароль = "abcd"', True), ('secret = "' + 'x' * 161 + '"', False),
        ):
            with self.subTest(source=source[:50]):
                self.assertEqual(has_secret_literal(source), expected)
        randomizer = random.Random(31)
        parts = ['Пароль', 'secret', 'foo', '1Пароль', '=', ' ', '\n', '"', "'", 'abcd',
                 '&parameter', '"foo secret=\'abcd\' bar"', 'İtoken', '""']
        for _ in range(1000):
            source = ''.join(randomizer.choices(parts, k=randomizer.randint(1, 25)))
            # Differential oracle is the previous scanner, not the new candidate iterator.
            expected = any(match.group('value').strip()
                and not match.group('value').strip().startswith('&')
                and SECRET_IDENTIFIER_RE.search(match.group('name'))
                for match in SECRET_ASSIGNMENT_RE.finditer(source))
            self.assertEqual(has_secret_literal(source), bool(expected), source)


class SnippetConfigurationTests(unittest.TestCase):
    def test_config_uses_cli_then_environment_then_default(self):
        for environment, argv, expected in (
            ({}, [], 4000),
            ({"V8STD_MCP_MAX_SNIPPET_CHARS": "32000"}, [], 32000),
            ({"V8STD_MCP_MAX_SNIPPET_CHARS": " 08000 "}, [], 8000),
            ({"V8STD_MCP_MAX_SNIPPET_CHARS": "bad"}, ["--max-snippet-chars", "4000"], 4000),
        ):
            with self.subTest(environment=environment, argv=argv), patch.dict(os.environ, environment, clear=True):
                self.assertEqual(parse_args(argv).max_snippet_chars, expected)

    def test_invalid_config_fails_before_loading_the_index(self):
        for value in ("", "0", "3999", "32001", "-4000", "+4000", "4e3", "4000.0", "４０００", "private_marker"):
            for source in ("env", "cli"):
                environment = {"V8STD_MCP_MAX_SNIPPET_CHARS": value} if source == "env" else {}
                argv = [] if source == "env" else ["--max-snippet-chars", value]
                stderr = io.StringIO()
                with self.subTest(value=value, source=source), patch.dict(os.environ, environment, clear=True), \
                     patch("runtime.v8std_mcp_server.V8StdIndex.load") as load, contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as error:
                        main(argv)
                    self.assertNotEqual(error.exception.code, 0)
                    load.assert_not_called()
                    self.assertNotIn("private_marker", stderr.getvalue())

    def test_index_rejects_invalid_limit_types_and_ranges(self):
        for value in (True, False, "32000", 4000.0, None, 3999, 32001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                V8StdIndex(max_snippet_chars=value)

    def test_default_index_does_not_read_environment_or_allow_live_limit_changes(self):
        with patch.dict(os.environ, {"V8STD_MCP_MAX_SNIPPET_CHARS": "32000"}):
            index = V8StdIndex()
        self.assertEqual(index.max_snippet_chars, 4000)
        with self.assertRaises(AttributeError):
            index.max_snippet_chars = 32000


class LargeSnippetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.default = loaded_index()
        cls.large = loaded_index(max_snippet_chars=32000)

    def test_instances_enforce_decoded_input_boundaries_independently(self):
        for index, maximum in ((self.default, 4000), (self.large, 32000)):
            for size in (maximum - 1, maximum):
                with self.subTest(maximum=maximum, size=size):
                    source = "я😀 " * (size // 3) + " " * (size % 3)
                    self.assertEqual(len(source), size)
                    self.assertEqual(index.explain_snippet(source)["language"], "auto")
            with self.assertRaisesRegex(ValueError, f"max {maximum} characters"):
                index.explain_snippet(" " * (maximum + 1))
            with self.assertRaisesRegex(ValueError, "max 500 characters"):
                index.search("я" * 501)
        with self.assertRaisesRegex(ValueError, "max 4000"):
            self.default.explain_snippet(procedure(4001, SIGNAL_CASES[1][0]))

    def test_32k_signals_survive_positions_with_and_without_vectors(self):
        for vectors in (self.large._vectors, []):
            with patch.object(self.large, "_vectors", vectors):
                for signal, expected in SIGNAL_CASES:
                    for position in ("start", "middle", "end"):
                        with self.subTest(expected=expected, position=position, vectors=bool(vectors)):
                            with patch.object(self.large, "search", wraps=self.large.search) as search:
                                result = self.large.explain_snippet(procedure(32000, signal, position), limit=1)
                            self.assertEqual(result_ids(result), [expected])
                            self.assertEqual(search.call_count, 1)
                            self.assertLessEqual(len(search.call_args.args[0]), 500)

    def test_many_signals_do_not_add_search_passes(self):
        source = ("\n".join(signal for signal, _ in SIGNAL_CASES) + "\n") * 100
        with patch.object(self.large, "search", wraps=self.large.search) as search:
            result = self.large.explain_snippet(source, limit=4)
        self.assertEqual(set(result_ids(result)), {"std740", "std485", "std415", "bslls:UsingModalWindows"})
        self.assertEqual(len(result["signals"]), 4)
        self.assertEqual(search.call_count, 1)


class SnippetWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = loaded_index()

    def test_schema_calls_errors_and_usage_share_one_instance_limit(self):
        for maximum in (4000, 32000):
            index = self.index if maximum == 4000 else loaded_index(max_snippet_chars=maximum)
            with self.subTest(maximum=maximum), tempfile.TemporaryDirectory() as directory:
                usage_path = Path(directory) / "usage.jsonl"
                server = build_server(index, host="127.0.0.1", port=8765, mcp_path="/mcp",
                                      allowed_hosts=["127.0.0.1:*"], allowed_origins=[],
                                      usage_logger=McpToolUsageLogger(usage_path))
                with TestClient(server.streamable_http_app(), base_url="http://127.0.0.1:8765") as client:
                    def rpc(method, params, ensure_ascii=False):
                        response = client.post("/mcp", content=json.dumps({"jsonrpc": "2.0", "id": 1,
                            "method": method, "params": params}, ensure_ascii=ensure_ascii).encode("utf-8"),
                            headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"})
                        self.assertEqual(response.status_code, 200, response.text)
                        return response.json()["result"]

                    initialized = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "codex", "version": "test"}})
                    self.assertIn("tools", initialized["capabilities"])
                    tools = rpc("tools/list", {})["tools"]
                    self.assertEqual({tool["name"] for tool in tools}, {"v8std_search", "v8std_get_page",
                        "v8std_get_related", "v8std_explain_snippet", "v8std_explain_diagnostics"})
                    tool = next(tool for tool in tools if tool["name"] == "v8std_explain_snippet")
                    self.assertEqual(tool["inputSchema"]["properties"]["snippet"].get("maxLength"), maximum)
                    self.assertIn(str(maximum), tool["description"])
                    for ascii_json in (False, True):
                        signal = SIGNAL_CASES[1][0]
                        source = "😀" * (maximum - len(signal) - 1) + "\n" + signal
                        success = rpc("tools/call", {"name": "v8std_explain_snippet",
                            "arguments": {"snippet": source, "limit": 1}}, ensure_ascii=ascii_json)
                        self.assertFalse(success.get("isError", False))
                        result = json.loads(success["content"][0]["text"])
                        self.assertEqual(result_ids(result), ["std485"])
                    oversized = "private_marker" + " " * maximum
                    error = rpc("tools/call", {"name": "v8std_explain_snippet", "arguments": {"snippet": oversized}})
                    self.assertTrue(error["isError"])
                    self.assertIn(str(maximum), json.dumps(error))
                    self.assertNotIn("private_marker", json.dumps(error))
                    self.assertEqual(client.get("/mcp", headers={"Accept": "text/event-stream"}).status_code, 405)
                events = usage_path.read_text(encoding="utf-8")
                self.assertNotIn("private_marker", events)
                self.assertNotIn("УстановитьПривилегированныйРежим", events)


if __name__ == "__main__":
    unittest.main()
