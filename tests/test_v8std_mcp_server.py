from __future__ import annotations

import ast
import asyncio
import json
import logging
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from functools import lru_cache


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / 'runtime/v8std_mcp_server.py'
SCRIPTS_PATH = REPO_ROOT / "scripts"

EXPECTED_TOOL_NAMES = [
    "v8std_search",
    "v8std_get_page",
    "v8std_get_related",
    "v8std_explain_snippet",
    "v8std_explain_diagnostics",
]

EXPECTED_TOOL_GUIDANCE = {
    "v8std_search": ["natural-language", "v8std_explain_diagnostics", "v8std_explain_snippet", "not probabilities"],
    "v8std_get_page": ["Markdown", "body_truncated", "found=false", "v8std_search"],
    "v8std_get_related": ["explicit corpus links", "not evidence", "v8std_get_page"],
    "v8std_explain_snippet": ["one BSL procedure", "not confirmed violations", "heuristic confidence", "smaller relevant fragment"],
    "v8std_explain_diagnostics": ["source-code comments", "unknown_codes", "does not justify", "No wildcard"],
}


OPENAI_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
LOWER_SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


def _install_server_dependency_stubs() -> None:
    mcp_module = types.ModuleType("mcp")
    mcp_server_module = types.ModuleType("mcp.server")
    fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    transport_security_module = types.ModuleType("mcp.server.transport_security")
    starlette_module = types.ModuleType("starlette")
    starlette_requests_module = types.ModuleType("starlette.requests")
    starlette_responses_module = types.ModuleType("starlette.responses")

    class FastMCP:
        pass

    class TransportSecuritySettings:
        def __init__(self, *_args, **_kwargs):
            pass

    class Request:
        pass

    class Response:
        pass

    class JSONResponse(Response):
        pass

    class RedirectResponse(Response):
        pass

    fastmcp_module.FastMCP = FastMCP
    transport_security_module.TransportSecuritySettings = TransportSecuritySettings
    starlette_requests_module.Request = Request
    starlette_responses_module.JSONResponse = JSONResponse
    starlette_responses_module.RedirectResponse = RedirectResponse
    starlette_responses_module.Response = Response

    sys.modules.setdefault("mcp", mcp_module)
    sys.modules.setdefault("mcp.server", mcp_server_module)
    sys.modules.setdefault("mcp.server.fastmcp", fastmcp_module)
    sys.modules.setdefault("mcp.server.transport_security", transport_security_module)
    sys.modules.setdefault("starlette", starlette_module)
    sys.modules.setdefault("starlette.requests", starlette_requests_module)
    sys.modules.setdefault("starlette.responses", starlette_responses_module)


def load_server_module():
    if str(SCRIPTS_PATH) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_PATH))
    try:
        import runtime.v8std_mcp_server as v8std_mcp_server

        return v8std_mcp_server
    except ModuleNotFoundError as error:
        if error.name not in {"mcp", "starlette"}:
            raise
        _install_server_dependency_stubs()
        sys.modules.pop("runtime.v8std_mcp_server", None)
        import runtime.v8std_mcp_server as v8std_mcp_server

        return v8std_mcp_server


class FakeDownstreamApp:
    def __init__(self) -> None:
        self.calls = []

    async def __call__(self, scope, receive, send) -> None:
        self.calls.append({"method": scope["method"], "path": scope["path"]})
        await send(
            {
                "type": "http.response.start",
                "status": 209,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"downstream"})


async def asgi_request(app, method: str, path: str, headers: dict[str, str] | None = None):
    messages = []
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [
            (key.lower().encode("ascii"), value.encode("utf-8"))
            for key, value in (headers or {}).items()
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_headers = {
        key.decode("ascii").lower(): value.decode("utf-8")
        for message in messages
        if message["type"] == "http.response.start"
        for key, value in message["headers"]
    }
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return status, response_headers, body


def _constant_string(value: ast.AST) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


@lru_cache(maxsize=1)
def registered_tools() -> dict[str, str]:
    module = load_server_module()
    server = module.build_server(module.V8StdIndex(), host="127.0.0.1", port=8765,
        mcp_path="/mcp", allowed_hosts=["127.0.0.1:*"], allowed_origins=[])
    return {tool.name: tool.description or "" for tool in asyncio.run(server.list_tools())}


def registered_tool_names() -> list[str]:
    return list(registered_tools())


def server_instructions() -> str:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "FastMCP":
            continue
        for keyword in node.keywords:
            if keyword.arg == "instructions":
                instructions = _constant_string(keyword.value)
                if instructions is not None:
                    return instructions

    return ""


class V8StdMcpServerToolNameTests(unittest.TestCase):
    def test_tool_names_are_openai_style(self):
        tool_names = registered_tool_names()

        self.assertEqual(tool_names, EXPECTED_TOOL_NAMES)
        for name in tool_names:
            self.assertRegex(name, LOWER_SNAKE_RE)
            self.assertRegex(name, OPENAI_TOOL_NAME_RE)

    def test_antigravity_prefixed_tool_names_stay_valid(self):
        prefix = "mcp_ai-v8std-ru_"

        for name in registered_tool_names():
            prefixed_name = f"{prefix}{name}"
            self.assertLessEqual(len(prefixed_name), 64)
            self.assertRegex(prefixed_name, OPENAI_TOOL_NAME_RE)

    def test_server_instructions_teach_tool_selection(self):
        instructions = server_instructions()

        for expected in [
            "read-only",
            "does not run analyzers",
            "one BSL procedure or SDBL fragment",
            "diagnostic codes",
            "clean Markdown",
            "arbitrary prose search",
        ]:
            self.assertIn(expected, instructions)

    def test_tool_descriptions_explain_when_to_use_them(self):
        tools = registered_tools()

        self.assertEqual(list(tools), EXPECTED_TOOL_NAMES)
        for tool_name, expected_phrases in EXPECTED_TOOL_GUIDANCE.items():
            description = tools[tool_name]
            for expected in expected_phrases:
                self.assertIn(expected, description)


class SelfDocumentingMcpAppTests(unittest.TestCase):
    def app(self):
        server_module = load_server_module()
        downstream = FakeDownstreamApp()
        return server_module.SelfDocumentingMcpApp(downstream, mcp_path="/mcp"), downstream

    def test_plain_get_returns_html_self_documentation(self):
        app, downstream = self.app()

        status, headers, body = asyncio.run(asgi_request(app, "GET", "/mcp"))
        text = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])
        self.assertIn("This is a MCP Streamable HTTP endpoint", text)
        self.assertIn("https://v8std.ru/mcp/", text)
        self.assertIn("/healthz", text)
        self.assertIn("/version", text)
        self.assertIn("[mcp_servers.v8std]", text)
        self.assertIn('url = "https://ai.v8std.ru/mcp"', text)
        self.assertIn("Accept: application/json, text/event-stream", text)
        self.assertEqual(downstream.calls, [])

    def test_json_accept_returns_json_self_documentation(self):
        app, downstream = self.app()

        status, headers, body = asyncio.run(
            asgi_request(app, "GET", "/mcp", {"Accept": "application/json"})
        )
        payload = json.loads(body)

        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["content-type"])
        self.assertEqual(payload["message"], "This is a MCP Streamable HTTP endpoint")
        self.assertEqual(payload["documentation"], "https://v8std.ru/mcp/")
        self.assertEqual(payload["health"], "/healthz")
        self.assertEqual(payload["version"], "/version")
        self.assertIn("[mcp_servers.v8std]", payload["codex_config"])
        self.assertIn("Accept: application/json, text/event-stream", payload["curl"])
        self.assertEqual(downstream.calls, [])

    def test_head_returns_200_without_body(self):
        app, downstream = self.app()

        status, _headers, body = asyncio.run(asgi_request(app, "HEAD", "/mcp"))

        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(downstream.calls, [])

    def test_mcp_get_with_event_stream_accept_is_rejected(self):
        app, downstream = self.app()

        status, headers, body = asyncio.run(
            asgi_request(app, "GET", "/mcp", {"Accept": "application/json, text/event-stream"})
        )

        self.assertEqual(status, 405)
        self.assertEqual(headers["allow"], "POST, HEAD")
        self.assertIn(b"does not provide an unsolicited SSE stream", body)
        self.assertEqual(downstream.calls, [])

    def test_post_reaches_downstream_even_with_bad_accept(self):
        app, downstream = self.app()

        status, _headers, body = asyncio.run(asgi_request(app, "POST", "/mcp", {"Accept": "text/plain"}))

        self.assertEqual(status, 209)
        self.assertEqual(body, b"downstream")
        self.assertEqual(downstream.calls, [{"method": "POST", "path": "/mcp"}])

    def test_get_slash_redirects_to_mcp(self):
        app, downstream = self.app()

        status, headers, body = asyncio.run(asgi_request(app, "GET", "/mcp/"))

        self.assertEqual(status, 303)
        self.assertEqual(headers["location"], "/mcp")
        self.assertEqual(body, b"")
        self.assertEqual(downstream.calls, [])

    def test_post_slash_redirect_preserves_method(self):
        app, downstream = self.app()

        status, headers, body = asyncio.run(asgi_request(app, "POST", "/mcp/"))

        self.assertEqual(status, 308)
        self.assertEqual(headers["location"], "/mcp")
        self.assertEqual(body, b"")
        self.assertEqual(downstream.calls, [])


class RuntimeLoggingTests(unittest.TestCase):
    def test_default_log_level_is_warning_to_keep_journald_small(self):
        server_module = load_server_module()

        args = server_module.parse_args([])

        self.assertEqual(args.log_level, "WARNING")

    def test_runtime_logging_suppresses_mcp_and_uvicorn_info_logs(self):
        server_module = load_server_module()
        loggers = ["mcp", "uvicorn", "uvicorn.access", "uvicorn.error"]
        previous_levels = {name: logging.getLogger(name).level for name in loggers}

        try:
            server_module.configure_runtime_logging("WARNING")

            for name in loggers:
                self.assertEqual(logging.getLogger(name).level, logging.WARNING)
        finally:
            for name, level in previous_levels.items():
                logging.getLogger(name).setLevel(level)


class ClientSystemTrackingTests(unittest.TestCase):
    def test_classifies_known_mcp_clients(self):
        server_module = load_server_module()

        self.assertEqual(server_module.classify_client_system("Cursor/0.45"), "cursor")
        self.assertEqual(server_module.classify_client_system("Claude Desktop"), "claude")
        self.assertEqual(server_module.classify_client_system("codex-cli/0.8"), "codex")
        self.assertEqual(server_module.classify_client_system("JetBrains IDE"), "jetbrains")
        self.assertEqual(server_module.classify_client_system("Visual Studio Code"), "vscode")
        self.assertEqual(server_module.classify_client_system("curl/8.7.1"), "curl")
        self.assertEqual(server_module.classify_client_system("Mozilla/5.0"), "browser")
        self.assertEqual(server_module.classify_client_system("node"), "node")
        self.assertEqual(server_module.classify_client_system("opencode/1.2.27"), "opencode")
        self.assertEqual(server_module.classify_client_system("Go-http-client/1.1"), "go")
        self.assertEqual(server_module.classify_client_system("python-httpx/0.28.1"), "python_httpx")
        self.assertEqual(server_module.classify_client_system("kilo/7.2.25"), "kilo")
        self.assertEqual(server_module.classify_client_system("Java-http-client/17.0.16"), "java")
        self.assertEqual(server_module.classify_client_system("undici"), "node")
        self.assertEqual(
            server_module.classify_client_system("got (https://github.com/sindresorhus/got)"),
            "node",
        )
        self.assertEqual(server_module.classify_client_system("custom-client"), "other")
        self.assertEqual(server_module.classify_client_system(""), "unknown")

    def test_classifies_unica_and_copilot_clients(self):
        server_module = load_server_module()

        self.assertEqual(server_module.classify_client_system("unica/0.13.2 (darwin; aarch64)"), "unica")
        self.assertEqual(server_module.classify_client_system("ureq/2.12.1"), "unica_legacy")
        self.assertEqual(server_module.classify_client_system("GitHubCopilotChat/0.22.4"), "copilot")
        self.assertEqual(server_module.classify_client_system("copilot-language-server/1.2"), "copilot")
        for system in ("unica", "unica_legacy", "copilot"):
            self.assertIn(system, server_module.ALLOWED_CLIENT_SYSTEMS)

    def test_mcp_request_sets_current_client_system_for_downstream_app(self):
        server_module = load_server_module()
        observed_systems = []

        async def downstream(scope, receive, send):
            observed_systems.append(server_module.current_client_system())
            await send(
                {
                    "type": "http.response.start",
                    "status": 209,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send({"type": "http.response.body", "body": b"downstream"})

        app = server_module.SelfDocumentingMcpApp(downstream, mcp_path="/mcp")

        status, _headers, _body = asyncio.run(
            asgi_request(app, "POST", "/mcp", {"User-Agent": "Cursor/0.45"})
        )

        self.assertEqual(status, 209)
        self.assertEqual(observed_systems, ["cursor"])
        self.assertEqual(server_module.current_client_system(), "unknown")


class UsageWireTests(unittest.TestCase):
    def test_initialize_client_and_search_shape_reach_usage_log_over_http(self):
        from starlette.testclient import TestClient

        from runtime.v8std_mcp_index import V8StdIndex
        from runtime.v8std_mcp_server import McpToolUsageLogger, build_server

        index = V8StdIndex(pages_path=REPO_ROOT / "docs/ai/pages.jsonl", vectors_path=None)
        index.load()
        with tempfile.TemporaryDirectory() as directory:
            usage_path = Path(directory) / "usage.jsonl"
            server = build_server(index, host="127.0.0.1", port=8765, mcp_path="/mcp",
                                  allowed_hosts=["127.0.0.1:*"], allowed_origins=[],
                                  usage_logger=McpToolUsageLogger(usage_path))
            headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json",
                       "User-Agent": "unica/0.13.2", "X-Real-IP": "8.8.8.8"}
            with TestClient(server.streamable_http_app(), base_url="http://127.0.0.1:8765") as client:
                def rpc(method, params, number=1):
                    response = client.post("/mcp", headers=headers, content=json.dumps(
                        {"jsonrpc": "2.0", "id": number, "method": method, "params": params}).encode("utf-8"))
                    self.assertEqual(response.status_code, 200, response.text)
                    return response.json()["result"]

                initialized = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                                 "clientInfo": {"name": "unica", "version": "0.13.2"}})
                self.assertIn("serverInfo", initialized)
                first = rpc("tools/call", {"name": "v8std_search",
                                           "arguments": {"query": "модуль", "limit": 2, "mode": "bm25"}}, 2)
                cursor = first["structuredContent"]["next_cursor"]
                rpc("tools/call", {"name": "v8std_search", "arguments": {
                    "query": "модуль", "limit": 2, "mode": "bm25", "cursor": cursor}}, 3)
                rpc("tools/call", {"name": "v8std_get_page", "arguments": {"id_or_alias_or_url": "std437"}}, 4)
            rows = [json.loads(line) for line in usage_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([row["tool"] for row in rows],
                         ["mcp_initialize", "v8std_search", "v8std_search", "v8std_get_page"])
        sessions = {row.get("session") for row in rows}
        self.assertEqual(len(sessions), 1)
        self.assertIsNotNone(next(iter(sessions)))
        self.assertTrue(all(row["system"] == "unica" for row in rows))
        self.assertTrue(all((row["client_name"], row["client_version"]) == ("unica", "0.13.2") for row in rows))
        self.assertEqual([(row["mode"], row["limit"], row["page"], row["returned"]) for row in rows[1:3]],
                         [("bm25", 2, 0, 2), ("bm25", 2, 1, 2)])
        self.assertGreater(rows[1]["total"], 2)
        self.assertNotIn("8.8.8.8", usage_path.name + json.dumps(rows))


class McpToolUsageLoggerTests(unittest.TestCase):
    def test_search_record_carries_request_shape_and_counts(self):
        server_module = load_server_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "tool-usage.jsonl"
            logger = server_module.McpToolUsageLogger(log_path)
            result = {
                "normalized_query": "модальные окна",
                "mode": "hybrid",
                "types": ["diagnostic", "standard", "secret"],
                "total": 14,
                "results": [{"id": "std404", "title": "Модальные окна", "url": "https://v8std.ru/std/404/"}],
            }
            logger.record_search("модальные окна", result, system="unica", limit=1, page=3)
            logger.record_search("бессмыслица", {"mode": "exact", "types": None, "total": 0, "results": []},
                                 system="unica", limit=10, page=0)
            rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(
            {key: rows[0][key] for key in ("mode", "limit", "types", "page", "total", "returned")},
            {"mode": "hybrid", "limit": 1, "types": ["diagnostic", "standard"], "page": 3, "total": 14, "returned": 1},
        )
        self.assertEqual(
            {key: rows[1].get(key) for key in ("mode", "limit", "types", "page", "total", "returned")},
            {"mode": "exact", "limit": 10, "types": None, "page": 0, "total": 0, "returned": 0},
        )
        self.assertNotIn("session", rows[0])

    def test_session_pseudonym_links_requests_without_storing_the_address(self):
        server_module = load_server_module()
        tracker = server_module.ClientSessionTracker()

        def session(address, user_agent="unica/0.13.2", **headers):
            values = {b"user-agent": user_agent, **{key.encode(): value for key, value in headers.items()}}
            return tracker.session_for({"client": (address, 40000)}, values)

        first = session("8.8.8.8")
        self.assertRegex(first, r"^[0-9a-f]{16}$")
        self.assertEqual(session("8.8.8.8"), first)
        self.assertNotEqual(session("8.8.8.8", user_agent="codex-cli/0.8"), first)
        self.assertNotEqual(session("8.8.4.4"), first)
        self.assertNotEqual(server_module.ClientSessionTracker().session_for(
            {"client": ("8.8.8.8", 40000)}, {b"user-agent": "unica/0.13.2"}), first)
        # The edge proxy and container bridges are not client identities.
        self.assertIsNone(session("127.0.0.1"))
        self.assertIsNone(session("172.17.0.1"))
        self.assertEqual(session("127.0.0.1", **{"x-real-ip": "8.8.8.8"}), first)
        self.assertEqual(session("127.0.0.1", **{"x-forwarded-for": "8.8.8.8, 10.0.0.1"}), first)
        self.assertRegex(session("127.0.0.1", **{"mcp-session-id": "abc"}), r"^[0-9a-f]{16}$")
        self.assertNotIn("8.8.8.8", first)

    def test_initialize_client_info_is_sanitized(self):
        server_module = load_server_module()
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "unica\n<script>" + "x" * 100, "version": "0.13.2+abc"}}}).encode()

        name, version = server_module.initialize_client_info(body)

        self.assertEqual(version, "0.13.2+abc")
        self.assertTrue(name.startswith("unica script"))
        self.assertLessEqual(len(name), server_module.MAX_USAGE_CLIENT_CHARS)
        self.assertIsNone(server_module.initialize_client_info(b'{"method":"tools/list"}'))
        self.assertIsNone(server_module.initialize_client_info(b"not json"))
        self.assertEqual(server_module.initialize_client_info(b'{"method":"initialize","params":{}}'), (None, None))

    def test_usage_logger_writes_tool_name_without_arguments_by_default(self):
        server_module = load_server_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "tool-usage.jsonl"
            logger = server_module.McpToolUsageLogger(log_path)

            logger.record("v8std_search")

            payload = json.loads(log_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["tool"], "v8std_search")
        self.assertRegex(payload["ts"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual(set(payload), {"ts", "tool"})

    def test_usage_logger_writes_public_search_and_page_metadata_only(self):
        server_module = load_server_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "tool-usage.jsonl"
            logger = server_module.McpToolUsageLogger(log_path)

            logger.record_search(
                "модальные окна\nвызов",
                {
                    "normalized_query": "модальные окна вызов",
                    "results": [
                        {
                            "id": "std404",
                            "title": "Модальные окна",
                            "url": "https://v8std.ru/std/404/",
                            "body": "not public",
                        },
                        {
                            "id": "external",
                            "title": "External",
                            "url": "https://example.com/",
                        },
                    ],
                },
                system="cursor",
            )
            logger.record_page(
                "std437",
                {
                    "found": True,
                    "page": {
                        "id": "std437",
                        "title": "Оформление текстов запросов",
                        "url": "https://v8std.ru/std/437/",
                        "body": "not public",
                    },
                },
                system="node",
            )

            rows = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(rows[0]["tool"], "v8std_search")
        self.assertEqual(rows[0]["system"], "cursor")
        self.assertEqual(rows[0]["query"], "модальные окна вызов")
        self.assertEqual(rows[0]["results"], [
            {
                "id": "std404",
                "title": "Модальные окна",
                "url": "https://v8std.ru/std/404/",
            }
        ])
        self.assertNotIn("body", json.dumps(rows, ensure_ascii=False))

        self.assertEqual(rows[1]["tool"], "v8std_get_page")
        self.assertEqual(rows[1]["system"], "node")
        self.assertEqual(rows[1]["requested_page"], "std437")
        self.assertEqual(rows[1]["page_id"], "std437")
        self.assertEqual(rows[1]["title"], "Оформление текстов запросов")
        self.assertEqual(rows[1]["url"], "https://v8std.ru/std/437/")

    def test_usage_logger_writes_public_diagnostic_metadata_only(self):
        server_module = load_server_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "tool-usage.jsonl"
            logger = server_module.McpToolUsageLogger(log_path)

            logger.record_diagnostics(
                ["bslls:UsingModalWindows", "bslls:UsingModalWindows", "private\ntext"],
                {
                    "diagnostics": [
                        {
                            "id": "bslls:UsingModalWindows",
                            "title": "Использование модальных окон",
                            "url": "https://v8std.ru/diagnostics/bslls/UsingModalWindows/",
                            "markdown_url": "https://v8std.ru/diagnostics/bslls/UsingModalWindows.md",
                            "body": "not public",
                            "frequency": 2,
                        },
                        {
                            "id": "external",
                            "title": "External",
                            "url": "https://example.com/",
                            "frequency": 99,
                        },
                    ],
                    "unknown_codes": [
                        {
                            "code": "v8cs:NewUnknownDiagnostic",
                            "frequency": 3,
                        },
                    ],
                    "standards": [
                        {
                            "id": "std404",
                            "title": "Modal",
                            "url": "https://v8std.ru/std/404/",
                        },
                        {
                            "id": "std999",
                            "title": "Стандарт без страницы",
                            "frequency": 2,
                        }
                    ],
                },
                system="opencode",
            )

            payload = json.loads(log_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["tool"], "v8std_explain_diagnostics")
        self.assertEqual(payload["system"], "opencode")
        self.assertNotIn("requested_codes", payload)
        self.assertEqual(
            payload["diagnostics"],
            [
                {
                    "id": "bslls:UsingModalWindows",
                    "title": "Использование модальных окон",
                    "url": "https://v8std.ru/diagnostics/bslls/UsingModalWindows/",
                    "frequency": 2,
                }
            ],
        )
        self.assertEqual(payload["unknown_codes"], [{"code": "v8cs:NewUnknownDiagnostic", "frequency": 3}])
        self.assertEqual(
            payload["standards_without_page"],
            [
                {
                    "id": "std999",
                    "title": "Стандарт без страницы",
                    "frequency": 2,
                }
            ],
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("body", serialized)
        self.assertNotIn("example.com", serialized)


if __name__ == "__main__":
    unittest.main()
