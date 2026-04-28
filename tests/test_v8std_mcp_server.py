from __future__ import annotations

import ast
import asyncio
import json
import re
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "scripts" / "v8std_mcp_server.py"
SCRIPTS_PATH = REPO_ROOT / "scripts"

EXPECTED_TOOL_NAMES = [
    "v8std_search",
    "v8std_get_page",
    "v8std_get_related",
    "v8std_explain_snippet",
    "v8std_explain_diagnostics",
]

EXPECTED_TOOL_GUIDANCE = {
    "v8std_search": [
        "Use this when",
        "arbitrary phrase",
        "Do not use this first for code snippets",
        "diagnostic-code lists",
    ],
    "v8std_get_page": [
        "Use this when",
        "clean Markdown",
        "exact id",
        "After v8std_search",
    ],
    "v8std_get_related": [
        "Use this when",
        "from a known standard or diagnostic",
        "related standards",
        "diagnostics",
    ],
    "v8std_explain_snippet": [
        "Use this when",
        "short BSL or SDBL code fragment",
        "applicable standards",
        "Do not use it for ordinary prose",
    ],
    "v8std_explain_diagnostics": [
        "Use this when",
        "ACC",
        "BSLLS",
        "EDT",
        "standard clauses",
    ],
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
        import v8std_mcp_server

        return v8std_mcp_server
    except ModuleNotFoundError as error:
        if error.name not in {"mcp", "starlette"}:
            raise
        _install_server_dependency_stubs()
        sys.modules.pop("v8std_mcp_server", None)
        import v8std_mcp_server

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


def registered_tools() -> dict[str, str]:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    tools: dict[str, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr != "tool":
                continue

            name = None
            description = None
            for keyword in decorator.keywords:
                if keyword.arg == "name":
                    name = _constant_string(keyword.value)
                if keyword.arg == "description":
                    description = _constant_string(keyword.value)

            if name is not None and description is not None:
                tools[name] = description

    return tools


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
            "short BSL/SDBL snippet",
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

    def test_mcp_get_with_event_stream_accept_reaches_downstream(self):
        app, downstream = self.app()

        status, _headers, body = asyncio.run(
            asgi_request(app, "GET", "/mcp", {"Accept": "application/json, text/event-stream"})
        )

        self.assertEqual(status, 209)
        self.assertEqual(body, b"downstream")
        self.assertEqual(downstream.calls, [{"method": "GET", "path": "/mcp"}])

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


if __name__ == "__main__":
    unittest.main()
