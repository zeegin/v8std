"""Tools-only contract at real SDK transport and verified-generation boundaries."""
from contextlib import contextmanager
from dataclasses import fields
import json
from pathlib import Path
import pickle
import tempfile
import time
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from tests import mcp_snapshot_fixtures as fixture
from tests.test_v8std_mcp_runtime import Current
from tests.test_v8std_mcp_snapshots import Source
from runtime.v8std_mcp_index import V8StdIndex
from runtime.v8std_mcp_runtime import SnapshotIndex, build_generation
from runtime.v8std_mcp_server import build_server
from runtime.v8std_mcp_snapshot_format import verify_archive
from runtime.v8std_mcp_snapshots import SnapshotStore


TOOL_NAMES = ["v8std_search", "v8std_get_page", "v8std_get_related",
              "v8std_explain_snippet", "v8std_explain_diagnostics"]
RESOURCE_REQUESTS = (
    ("resources/list", {}),
    ("resources/templates/list", {}),
    ("resources/read", {"uri": "v8std://llms.txt"}),
    ("resources/read", {"uri": "v8std://llms-full.txt"}),
    ("resources/read", {"uri": "v8std://ai/pages.jsonl"}),
    ("resources/read", {"uri": "v8std://missing"}),
    ("resources/subscribe", {"uri": "v8std://llms.txt"}),
    ("resources/unsubscribe", {"uri": "v8std://llms.txt"}),
)
TOOL_ARGUMENTS = ({"query": "std437"}, {"id_or_alias_or_url": "std437"},
                  {"id_or_alias_or_url": "std437"}, {"snippet": "std437"},
                  {"codes": ["missing"]})

# Hand-written expectations for the five inherited signatures, including defaults.
SCHEMAS = (
    ("search", ["query"], {
        "query": {"title": "Query", "type": "string"},
        "limit": {"default": 10, "title": "Limit", "type": "integer"},
        "types": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                  "default": None, "title": "Types"},
        "mode": {"default": "hybrid", "title": "Mode", "type": "string"},
    }),
    ("page", ["id_or_alias_or_url"], {
        "id_or_alias_or_url": {"title": "Id Or Alias Or Url", "type": "string"},
        "body_limit": {"default": 12000, "title": "Body Limit", "type": "integer"},
    }),
    ("related", ["id_or_alias_or_url"], {
        "id_or_alias_or_url": {"title": "Id Or Alias Or Url", "type": "string"},
        "relations": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                      "default": None, "title": "Relations"},
        "limit": {"default": 10, "title": "Limit", "type": "integer"},
    }),
    ("explain_snippet", ["snippet"], {
        "snippet": {"maxLength": 4000, "title": "Snippet", "type": "string"},
        "language": {"default": "auto", "title": "Language", "type": "string"},
        "limit": {"default": 10, "title": "Limit", "type": "integer"},
    }),
    ("explain_diagnostics", ["codes"], {
        "codes": {"items": {"type": "string"}, "title": "Codes", "type": "array"},
    }),
)


class HttpRpc:
    """One protocol driver shared by ASGI and loopback HTTP tests."""
    def __init__(self, client):
        self.client = client
        self.number = 0
        self.headers = {"Accept": "application/json, text/event-stream"}

    def call(self, method, params=None):
        self.number += 1
        response = self.client.post("/mcp", headers=self.headers,
            json={"jsonrpc": "2.0", "id": self.number, "method": method, "params": params or {}})
        if response.status_code != 200 or response.headers.get("content-type") != "application/json":
            raise AssertionError((response.status_code, response.headers, response.text))
        reply = response.json()
        if reply.get("id") != self.number or reply.get("jsonrpc") != "2.0":
            raise AssertionError(reply)
        return reply

    def notify(self, method, params=None):
        response = self.client.post("/mcp", headers=self.headers,
            json={"jsonrpc": "2.0", "method": method, "params": params or {}})
        if response.status_code != 202 or response.content:
            raise AssertionError((response.status_code, response.text))


def initialize(rpc, name="tools-only"):
    reply = rpc.call("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                   "clientInfo": {"name": name, "version": "1"}})
    if reply["result"]["protocolVersion"] != "2025-03-26":
        raise AssertionError(reply)
    if isinstance(rpc, HttpRpc):
        rpc.headers["MCP-Protocol-Version"] = reply["result"]["protocolVersion"]
    rpc.notify("notifications/initialized")
    return reply


@contextmanager
def http_rpc(index):
    server = build_server(index, host="127.0.0.1", port=8765, mcp_path="/mcp",
                          allowed_hosts=["testserver"], allowed_origins=[])
    with TestClient(server.streamable_http_app()) as client:
        yield HttpRpc(client)


def assert_resources_disabled(test, rpc):
    for method, params in RESOURCE_REQUESTS:
        with test.subTest(method=method, params=params):
            reply = rpc.call(method, params)
            test.assertEqual(reply.get("error", {}).get("code"), -32601, reply)
            test.assertNotIn("result", reply)
            test.assertLess(len(json.dumps(reply)), 256, "error must not contain corpus data")


def assert_tool_catalog(test, rpc):
    tools = rpc.call("tools/list")["result"]["tools"]
    test.assertEqual([tool["name"] for tool in tools], TOOL_NAMES)
    for tool, (name, required, properties) in zip(tools, SCHEMAS):
        schema = dict(tool["inputSchema"])
        schema["properties"] = {}
        for key, value in tool["inputSchema"]["properties"].items():
            test.assertTrue(value.get("description"), (tool["name"], key))
            schema["properties"][key] = {k: v for k, v in value.items() if k != "description"}
        test.assertEqual(schema, {"properties": properties, "required": required,
                                              "title": name + "Arguments", "type": "object"})
        test.assertEqual(tool["outputSchema"], {"additionalProperties": True,
                                               "title": name + "DictOutput", "type": "object"})


def call_tool(test, rpc, name, arguments):
    result = rpc.call("tools/call", {"name": name, "arguments": arguments})["result"]
    test.assertFalse(result.get("isError", False), result)
    test.assertEqual([item["type"] for item in result["content"]], ["text"])
    test.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
    return result["structuredContent"]


class ToolsOnlyWireTests(unittest.TestCase):
    def assert_ready_tools(self, rpc, site_url):
        results = [call_tool(self, rpc, name, arguments)
                   for name, arguments in zip(TOOL_NAMES, TOOL_ARGUMENTS)]
        search, page, related, snippet, diagnostics = results
        self.assertEqual(search["mode"], "hybrid")
        self.assertEqual([item["id"] for item in search["results"]], ["std437"])
        self.assertTrue(page["found"])
        self.assertEqual(page["candidates"], [])
        self.assertEqual(page["page"]["url"], site_url + "std/437/")
        self.assertIn("[Стандарт](" + site_url + "std/437/?view=full#query)", page["page"]["body_markdown"])
        self.assertIn('Адрес = "https://v8std.ru/std/437/";', page["page"]["body_markdown"])
        self.assertFalse(page["page"]["body_truncated"])
        self.assertEqual(related, {"found": True, "id": "std437", "title": "Запросы",
                                   "relations": None, "related": []})
        self.assertEqual([item["id"] for item in snippet["standards"]], ["std437"])
        self.assertEqual(diagnostics, {"diagnostics": [], "standards": [],
            "unknown_codes": [{"code": "missing", "frequency": 1}], "total_input": 1, "unique_codes": 1})

    def assert_cold_tools(self, rpc):
        for name, arguments in zip(TOOL_NAMES, TOOL_ARGUMENTS):
            result = rpc.call("tools/call", {"name": name, "arguments": arguments})["result"]
            self.assertTrue(result["isError"], result)
            self.assertIn("INDEX_NOT_READY", result["content"][0]["text"])

    def test_http_cold_and_ready_resources_fail_while_tools_keep_their_contract(self):
        # Catches handlers accidentally retained on the common HTTP server.
        source = Source()
        source.fault = "headers"
        self.addCleanup(source.close)
        with tempfile.TemporaryDirectory() as directory:
            index = SnapshotIndex(site_url=source.url, cache_dir=Path(directory), refresh_seconds=0)
            with http_rpc(index) as rpc:
                for state in ("cold", "ready"):
                    with self.subTest(state=state):
                        initialized = initialize(rpc, state)
                        with self.subTest(capabilities=True):
                            self.assertNotIn("resources", initialized["result"]["capabilities"])
                            self.assertEqual(initialized["result"]["capabilities"]["prompts"], {"listChanged": False})
                        assert_tool_catalog(self, rpc)
                        assert_resources_disabled(self, rpc)
                        if state == "cold":
                            self.assert_cold_tools(rpc)
                            self.assertEqual(rpc.client.get("/healthz").status_code, 503)
                            source.release.set()
                            deadline = time.monotonic() + 8
                            while rpc.client.get("/healthz").status_code != 200:
                                self.assertLess(time.monotonic(), deadline, "snapshot startup timeout")
                                time.sleep(.02)
                        else:
                            self.assert_ready_tools(rpc, source.url)
                version = rpc.client.get("/version").json()
                self.assertEqual(version["api"], "v2")
                self.assertEqual(version["api_profiles"], ["legacy-tools"])
                response = rpc.client.get("/mcp", headers={"Accept": "text/event-stream"})
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers["allow"], "POST, HEAD")


    def test_resource_rejection_never_accesses_data_or_starts_io(self):
        # Any data-facade lookup is a bug, even when its failure is masked as -32601.
        class FailingDataFacade:
            max_snippet_chars = 4000

            def __init__(self):
                self.accesses = []

            def __getattr__(self, name):
                self.accesses.append(name)
                raise AssertionError("unexpected data access: " + name)

        index = FailingDataFacade()
        with http_rpc(index) as rpc:
            initialize(rpc)
            with patch("runtime.v8std_mcp_snapshots._download", side_effect=AssertionError("download")), \
                 patch("runtime.v8std_mcp_snapshots._read_file", side_effect=AssertionError("cache read")), \
                 patch.object(V8StdIndex, "_fetch_url", side_effect=AssertionError("legacy fetch")):
                assert_resources_disabled(self, rpc)
            self.assertEqual(index.accesses, [])


class ToolsOnlyGenerationTests(unittest.TestCase):
    def test_verified_generation_skips_bulk_formatting_and_survives_pickle(self):
        # Restoring eager full-corpus presentation must fail before it can be activated.
        snapshot = verify_archive(*fixture.snapshot_fixture())
        with patch("runtime.v8std_mcp_runtime.present_result", side_effect=AssertionError("bulk formatting")), \
             patch("runtime.v8std_mcp_runtime.present_markdown", create=True, side_effect=AssertionError("bulk markdown")), \
             patch.object(V8StdIndex, "_fetch_url", side_effect=AssertionError("network")):
            generation = build_generation(snapshot, max_snippet_chars=4000)
            encoded = pickle.dumps(generation)
            with patch.object(V8StdIndex, "_parse_pages", side_effect=AssertionError("reparse")), \
                 patch.object(V8StdIndex, "_replace_index", side_effect=AssertionError("rebuild")):
                decoded = pickle.loads(encoded)
            self.assertEqual([item["id"] for item in decoded.index.search("std437")["results"]], ["std437"])
            self.assertEqual(decoded.index.page("std437")["page"]["body_markdown"], fixture.BODY)
            self.assertEqual(decoded.index.search("std437"), generation.index.search("std437"))
        self.assertEqual({field.name for field in fields(decoded)},
                         {"corpus_id", "index", "canonical_site_url", "page_paths"})

    def test_existing_archive_and_namespace_reused_offline_with_local_page_presentation(self):
        # A resource retirement must not invalidate a v1 cache or corrupt rebased tool links.
        source = Source()
        self.addCleanup(source.close)
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            store = SnapshotStore(source.url, cache)
            snapshot = store.refresh()
            namespace = cache / ("v1-" + fixture.sha256(source.url.encode()))
            archived = namespace / "generations" / source.manifest["archive"]["sha256"] / "snapshot.tar.gz"
            self.assertEqual(archived.read_bytes(), source.archive)
            source.server.shutdown()
            source.server.server_close()
            with patch("runtime.v8std_mcp_snapshots._download", side_effect=AssertionError("offline download")):
                cached = SnapshotStore(source.url, cache).cached()
                self.assertIsNotNone(cached)
                self.assertEqual(set(cached.files),
                                 {"metadata.json", "pages.jsonl", "search-vectors.jsonl", "llms.txt", "llms-full.txt"})
                self.assertEqual(cached.files, snapshot.files)
                self.assertEqual(cached.archive_sha256, snapshot.archive_sha256)
                generation = build_generation(cached, max_snippet_chars=4000, site_url=source.url)
                facade = SnapshotIndex(site_url=source.url, cache_dir=cache)
                facade.coordinator = Current(generation)
                page = facade.page(source.url + "std/437/")["page"]
                self.assertEqual(page["url"], source.url + "std/437/")
                self.assertEqual(page["markdown_url"], source.url + "std/437.md")
                self.assertIn("[Стандарт](" + source.url + "std/437/?view=full#query)", page["body_markdown"])
                self.assertIn('Адрес = "https://v8std.ru/std/437/";', page["body_markdown"])
                self.assertEqual(page["source_urls"], ["https://its.1c.ru/db/v8std#437"])
                self.assertEqual([item["id"] for item in facade.search("std437")["results"]], ["std437"])


if __name__ == "__main__":
    unittest.main()
