from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CombinedMcpRuntimeTests(unittest.TestCase):
    def test_one_server_and_service_are_the_only_runtime_surfaces(self):
        server = (ROOT / "scripts/v8std_mcp_server.py").read_text(encoding="utf-8")
        service = (ROOT / "deploy/systemd/v8std-mcp.service").read_text(encoding="utf-8")
        nginx = (ROOT / "deploy/nginx/server-v8std-mcp.conf").read_text(encoding="utf-8")

        self.assertNotIn("/v3/mcp", server)
        self.assertNotIn("/v3/mcp", service)
        self.assertNotIn("/v3/mcp", nginx)
        self.assertIn("v8std_mcp_server.py", service)
        self.assertIn("proxy_pass http://v8std_mcp_upstream/mcp;", nginx)

        tree = ast.parse(server)
        fastmcp_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "FastMCP"
        ]
        self.assertEqual(len(fastmcp_calls), 1)

    def test_combined_profiles_keep_legacy_tool_and_resources(self):
        server = (ROOT / "scripts/v8std_mcp_server.py").read_text(encoding="utf-8")

        self.assertIn('MCP_API_PROFILES = ["legacy-tools", "resources"]', server)
        self.assertIn('name="v8std_get_page"', server)
        self.assertIn('@server.resource(', server)
        self.assertIn('"api_profiles": MCP_API_PROFILES', server)


if __name__ == "__main__":
    unittest.main()
