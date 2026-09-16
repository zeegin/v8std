from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CombinedMcpRuntimeTests(unittest.TestCase):
    @unittest.skip("No validated topology rule: counting FastMCP calls is insufficient; spec/architecture-review.md")
    def test_one_server_and_service_are_the_only_runtime_surfaces(self):
        server = (ROOT / "runtime/v8std_mcp_server.py").read_text(encoding="utf-8")
        self.assertNotIn("/v3/mcp", server)

        tree = ast.parse(server)
        fastmcp_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "FastMCP"
        ]
        self.assertEqual(len(fastmcp_calls), 1)

    def test_common_server_keeps_legacy_tools_without_resources(self):
        from tests import mcp_snapshot_fixtures as fixture
        from tests.test_v8std_mcp_tools_only import (
            http_rpc, initialize, assert_tool_catalog, assert_resources_disabled, call_tool,
        )
        from runtime.v8std_mcp_index import V8StdIndex

        files = fixture.corpus_files()
        index = V8StdIndex.from_validated_bytes(files["pages.jsonl"], files["search-vectors.jsonl"])
        with http_rpc(index) as rpc:
            initialized = initialize(rpc)
            self.assertNotIn("resources", initialized["result"]["capabilities"])
            assert_tool_catalog(self, rpc)
            assert_resources_disabled(self, rpc)
            result = call_tool(self, rpc, "v8std_get_page", {"id_or_alias_or_url": "std437"})
            self.assertTrue(result["found"])
            self.assertEqual(result["page"]["body_markdown"], fixture.BODY)
            version = rpc.client.get("/version").json()
            self.assertEqual(version["api"], "v2")
            self.assertEqual(version["api_profiles"], ["legacy-tools"])


if __name__ == "__main__":
    unittest.main()
