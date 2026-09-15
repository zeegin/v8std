"""Bounded acceptance-profile accounting; no production traffic or Docker by default."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class LoadProfileTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("check_mcp_load"))
        self.load = importlib.import_module("check_mcp_load")

    def test_mix_exercises_real_tools_and_all_retained_resources(self):
        requests = [self.load.request(index) for index in range(20)]
        names = [label for label, _ in requests]
        self.assertEqual({name: names.count(name) for name in set(names)}, {
            "search": 7, "page": 5, "snippet": 3, "diagnostics": 2,
            "resource:llms.txt": 1, "resource:llms-full.txt": 1, "resource:ai/pages.jsonl": 1})
        for _, message in requests:
            self.assertNotIn(message["method"], {"ping", "initialize"})
        self.assertEqual({message["params"]["uri"] for _, message in requests if message["method"] == "resources/read"},
                         {"v8std://llms.txt", "v8std://llms-full.txt", "v8std://ai/pages.jsonl"})

    def test_errors_and_retryable_admission_are_not_success_latency(self):
        rows = [dict(kind="search", seconds=.1, status=200, outcome="ok", bytes=20),
                dict(kind="search", seconds=.4, status=200, outcome="ok", bytes=30),
                dict(kind="search", seconds=.01, status=429, outcome="admission", bytes=10),
                dict(kind="page", seconds=.02, status=503, outcome="admission", bytes=10),
                dict(kind="page", seconds=10, status=0, outcome="timeout", bytes=0)]
        report = self.load.summarize(rows, 2)
        self.assertEqual(report["requests"], 5)
        self.assertEqual(report["admitted_successes"], 2)
        self.assertEqual(report["retryable_429_503"], 2)
        self.assertEqual(report["unexpected_errors"], 1)
        self.assertEqual(report["successful_rps"], 1)
        self.assertEqual(report["success_p95_seconds"], .4)
        self.assertEqual(report["success_p99_seconds"], .4)

    def test_resource_empty_or_mcp_error_is_not_a_successful_bulk_read(self):
        for value in ({"error": {"code": -1}}, {"result": {"contents": []}},
                      {"result": {"contents": [{"uri": "wrong", "text": "content"}]}}):
            self.assertFalse(self.load.valid_reply("resource:llms-full.txt", json.dumps(value).encode()))
        good = {"result": {"contents": [{"uri": "v8std://llms-full.txt", "text": "real corpus"}]}}
        self.assertTrue(self.load.valid_reply("resource:llms-full.txt", json.dumps(good).encode()))

    def test_edge_retains_admission_budgets_and_only_translates_fixture_transport(self):
        config = self.load.edge_config("mcp-a")
        for value in ("rate=100r/s", "burst=400", "max_conns=2048", "keepalive 256", "limit_req_status 429",
                      "limit_conn_status 503", "limit_conn v8std_mcp_connections 40000"):
            self.assertIn(value, config)
        self.assertIn("server mcp-a:8000 max_conns=2048", config)
        self.assertNotIn("ssl_certificate", config)
        self.assertIn("listen 8000;", config)
        self.assertNotIn("listen 443", config)

    def test_cleanup_attempts_each_exact_owned_resource_and_preserves_primary_error(self):
        stack = self.load.Stack()
        stack.owned = [("container", stack.prefix + "-a"), ("container", stack.prefix + "-b"),
                       ("volume", stack.prefix + "-data")]
        alive = {name for _, name in stack.owned}
        removed = []
        def docker(*args, **kwargs):
            if args[:2] == ("container", "ls") or args[:2] == ("volume", "ls"):
                name = args[args.index("--filter") + 1].removeprefix("name=").removeprefix("^/").removesuffix("$")
                return name + "\n" if name in alive else ""
            if args[0] == "inspect":
                return json.dumps([{"Config": {"Labels": {"pro.v8std.load": stack.prefix}}}])
            if args[:2] == ("volume", "inspect"):
                return json.dumps([{"Labels": {"pro.v8std.load": stack.prefix}}])
            if args[:2] == ("rm", "-f"):
                removed.append(args[2])
                if args[2].endswith("-a"):
                    raise RuntimeError("owned removal denied")
                alive.remove(args[2])
                return ""
            if args[:2] == ("volume", "rm"):
                removed.append(args[2])
                alive.remove(args[2])
                return ""
            raise AssertionError(args)
        primary = RuntimeError("primary probe failed")
        with patch.object(stack, "docker", side_effect=docker):
            self.assertFalse(stack.__exit__(RuntimeError, primary, None))
        self.assertIn("owned removal denied", " ".join(primary.__notes__))
        self.assertEqual(set(removed), {name for _, name in stack.owned})

    def test_uncertain_create_is_owned_before_daemon_call(self):
        stack = self.load.Stack()
        with patch.object(stack, "docker", side_effect=RuntimeError("client timeout")):
            with self.assertRaisesRegex(RuntimeError, "client timeout"):
                stack.launch("candidate", "fixture-image", "--network=none")
        self.assertEqual(stack.owned, [("container", stack.prefix + "-candidate")])

    def test_request_timeout_and_429_are_counted_at_real_async_client_boundary(self):
        import asyncio
        import httpx
        async def check():
            def respond(request):
                if request.headers.get("x-fixture") == "timeout":
                    raise httpx.ReadTimeout("synthetic timeout")
                return httpx.Response(429, headers={"Retry-After": "2"})
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                row = await self.load.measure(client, "http://fixture/mcp", "search", self.load.request(0)[1])
                self.assertEqual(row["outcome"], "admission")
                self.assertEqual(row["retry_after"], "2")
                row = await self.load.measure(client, "http://fixture/mcp", "search", self.load.request(0)[1],
                                              headers={"x-fixture": "timeout"})
                self.assertEqual(row["outcome"], "timeout")
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
