#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from v8std_mcp_index import (
    DEFAULT_CACHE_DIR,
    DEFAULT_INDEX_URL,
    DEFAULT_REFRESH_SECONDS,
    DEFAULT_VECTORS_URL,
    MAX_BODY_CHARS,
    V8StdIndex,
)


MCP_SELF_DOC_MESSAGE = "This is a MCP Streamable HTTP endpoint"
MCP_DOCUMENTATION_URL = "https://v8std.ru/mcp/"
MCP_PUBLIC_ENDPOINT = "https://ai.v8std.ru/mcp"
MCP_HEALTH_PATH = "/healthz"
MCP_VERSION_PATH = "/version"
MCP_CODEX_CONFIG = """[mcp_servers.v8std]
url = "https://ai.v8std.ru/mcp"
"""
MCP_CURL_EXAMPLE = (
    "curl -H 'Accept: application/json, text/event-stream' "
    "-H 'Content-Type: application/json' "
    "-X POST https://ai.v8std.ru/mcp "
    "-d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{"
    "\"protocolVersion\":\"2025-03-26\",\"capabilities\":{},"
    "\"clientInfo\":{\"name\":\"curl\",\"version\":\"1\"}}}'"
)


def normalize_mcp_path(mcp_path: str) -> str:
    normalized = "/" + mcp_path.strip("/")
    return normalized if normalized != "/" else "/mcp"


class SelfDocumentingMcpApp:
    def __init__(self, downstream: Any, *, mcp_path: str) -> None:
        self.downstream = downstream
        self.mcp_path = normalize_mcp_path(mcp_path)
        self.slash_path = f"{self.mcp_path}/"

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.downstream(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        path = scope.get("path", "")

        if path == self.slash_path:
            status = 303 if method in {"GET", "HEAD"} else 308
            await self._send_empty_response(send, status, [(b"location", self.mcp_path.encode("ascii"))])
            return

        if path == self.mcp_path and method == "HEAD":
            await self._send_self_documentation(send, prefer_json=False, include_body=False)
            return

        if path == self.mcp_path and method == "GET" and not self._accepts_event_stream(scope):
            await self._send_self_documentation(send, prefer_json=self._prefers_json(scope), include_body=True)
            return

        await self.downstream(scope, receive, send)

    def _accept_header(self, scope: dict[str, Any]) -> str:
        for key, value in scope.get("headers", []):
            if key.lower() == b"accept":
                return value.decode("latin-1").lower()
        return ""

    def _accepts_event_stream(self, scope: dict[str, Any]) -> bool:
        return "text/event-stream" in self._accept_header(scope)

    def _prefers_json(self, scope: dict[str, Any]) -> bool:
        accept = self._accept_header(scope)
        if "application/json" not in accept:
            return False
        if "text/html" not in accept:
            return True
        return accept.find("application/json") < accept.find("text/html")

    def _payload(self) -> dict[str, str]:
        return {
            "message": MCP_SELF_DOC_MESSAGE,
            "endpoint": MCP_PUBLIC_ENDPOINT,
            "documentation": MCP_DOCUMENTATION_URL,
            "health": MCP_HEALTH_PATH,
            "version": MCP_VERSION_PATH,
            "codex_config": MCP_CODEX_CONFIG,
            "curl": MCP_CURL_EXAMPLE,
        }

    def _html_body(self) -> str:
        payload = self._payload()
        return (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head><meta charset=\"utf-8\"><title>v8std MCP</title></head>\n"
            "<body>\n"
            f"<h1>{html.escape(payload['message'])}</h1>\n"
            "<p>The MCP endpoint is healthy, but MCP clients must use the "
            "<code>Accept: application/json, text/event-stream</code> header.</p>\n"
            "<dl>\n"
            f"<dt>Documentation</dt><dd><a href=\"{payload['documentation']}\">{payload['documentation']}</a></dd>\n"
            f"<dt>Health</dt><dd><a href=\"{payload['health']}\">{payload['health']}</a></dd>\n"
            f"<dt>Version</dt><dd><a href=\"{payload['version']}\">{payload['version']}</a></dd>\n"
            "</dl>\n"
            "<h2>Codex configuration</h2>\n"
            f"<pre><code>{html.escape(payload['codex_config'], quote=False)}</code></pre>\n"
            "<h2>Protocol check</h2>\n"
            f"<pre><code>{html.escape(payload['curl'], quote=False)}</code></pre>\n"
            "</body>\n"
            "</html>\n"
        )

    async def _send_self_documentation(self, send: Any, *, prefer_json: bool, include_body: bool) -> None:
        if prefer_json:
            body = json.dumps(self._payload(), indent=2).encode("utf-8")
            content_type = b"application/json; charset=utf-8"
        else:
            body = self._html_body().encode("utf-8")
            content_type = b"text/html; charset=utf-8"
        await self._send_response(
            send,
            200,
            [],
            content_type,
            body if include_body else b"",
        )

    async def _send_empty_response(self, send: Any, status: int, extra_headers: list[tuple[bytes, bytes]]) -> None:
        await self._send_response(send, status, extra_headers, b"text/plain; charset=utf-8", b"")

    async def _send_response(
        self,
        send: Any,
        status: int,
        extra_headers: list[tuple[bytes, bytes]],
        content_type: bytes,
        body: bytes,
    ) -> None:
        headers = [
            (b"cache-control", b"no-store"),
            (b"content-type", content_type),
            (b"content-length", str(len(body)).encode("ascii")),
            *extra_headers,
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})


def install_self_documenting_mcp_app(server: FastMCP, *, mcp_path: str) -> None:
    original_streamable_http_app = server.streamable_http_app

    def streamable_http_app_with_self_documentation():
        return SelfDocumentingMcpApp(original_streamable_http_app(), mcp_path=mcp_path)

    server.streamable_http_app = streamable_http_app_with_self_documentation  # type: ignore[method-assign]


def build_server(
    index: V8StdIndex,
    *,
    host: str,
    port: int,
    mcp_path: str,
    allowed_hosts: list[str],
    allowed_origins: list[str],
) -> FastMCP:
    server = FastMCP(
        "v8std",
        instructions=(
            "Use this read-only MCP as a v8std.ru knowledge source for 1C:Enterprise "
            "BSL/SDBL standards, diagnostics, aliases, relations, source URLs, and "
            "clean Markdown. It does not run analyzers, inspect projects, or change code. "
            "Tool selection: use v8std_explain_snippet for a short BSL/SDBL snippet; "
            "use v8std_explain_diagnostics for ACC, BSLLS, or EDT/v8-code-style "
            "diagnostic codes; use v8std_get_page when you already have an id, alias, "
            "path, or URL and need the full clean Markdown page; use v8std_get_related "
            "to move between a known standard and linked diagnostics or standards; "
            "use v8std_search for arbitrary prose search or unknown ids."
        ),
        host=host,
        port=port,
        streamable_http_path=mcp_path,
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        ),
    )

    @server.tool(
        name="v8std_search",
        description=(
            "Use this when the user asks an arbitrary phrase question or topic search "
            "over v8std.ru standards, diagnostics, patterns, or service pages, including "
            "natural Russian phrases, standard ids such as std437, and diagnostic names "
            "when no exact list is available. Do not use this first for code snippets "
            "or diagnostic-code lists; prefer v8std_explain_snippet or "
            "v8std_explain_diagnostics, then use search only if those results are "
            "insufficient. Returns ranked ids, aliases, URLs, snippets, and match reasons."
        ),
    )
    def search(
        query: str,
        limit: int = 10,
        types: list[str] | None = None,
        mode: str = "hybrid",
    ) -> dict[str, Any]:
        return index.search(query, types=types, mode=mode, limit=limit)

    @server.tool(
        name="v8std_get_page",
        description=(
            "Use this when you already have an exact id, alias, source path, HTML URL, "
            "or Markdown URL and need the full clean Markdown page text for a standard, "
            "diagnostic, pattern, or service page. After v8std_search, "
            "v8std_explain_snippet, v8std_explain_diagnostics, or v8std_get_related "
            "returns an id, call this to read the authoritative content before "
            "explaining or fixing code. Not for discovery; use search, snippet, "
            "or diagnostics tools first."
        ),
    )
    def page(id_or_alias_or_url: str, body_limit: int = MAX_BODY_CHARS) -> dict[str, Any]:
        return index.page(id_or_alias_or_url, body_limit=body_limit)

    @server.tool(
        name="v8std_get_related",
        description=(
            "Use this when you need to move from a known standard or diagnostic to "
            "related standards, diagnostics, or EDT/v8-code-style checks. Typical flow: "
            "after search, snippet, diagnostics, or page lookup gives an id, call this "
            "to collect surrounding rule context for code review, explanation, or "
            "remediation planning. Not for arbitrary search; use v8std_search first "
            "when no starting id is known."
        ),
    )
    def related(
        id_or_alias_or_url: str,
        relations: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return index.related(id_or_alias_or_url, relations=relations, limit=limit)

    @server.tool(
        name="v8std_explain_snippet",
        description=(
            "Use this when the input is a short BSL or SDBL code fragment and the goal "
            "is to identify applicable standards, likely diagnostics, and confidence "
            "from code tokens or calls, for example ВЫБРАТЬ РАЗРЕШЕННЫЕ, "
            "ОткрытьФормуМодально, Предупреждение, or Вопрос. Do not use it for ordinary "
            "prose such as 'модальные окна'; use v8std_search for prose. For full rule "
            "text, call v8std_get_page on returned ids."
        ),
    )
    def explain_snippet(
        snippet: str,
        language: str = "auto",
        limit: int = 10,
    ) -> dict[str, Any]:
        return index.explain_snippet(snippet, language=language, limit=limit)

    @server.tool(
        name="v8std_explain_diagnostics",
        description=(
            "Use this when the user has a list of analyzer diagnostic codes from ACC/АПК, "
            "BSLLS, EDT, or v8-code-style and needs diagnostic descriptions grouped with "
            "linked standard clauses. Accepts values like acc 1245, АПК:361, "
            "bslls:AssignAliasFieldsInQuery, or v8cs:*. For the full Markdown text of "
            "a diagnostic or standard, call v8std_get_page on returned ids; do not use "
            "for raw code snippets."
        ),
    )
    def explain_diagnostics(codes: list[str]) -> dict[str, Any]:
        return index.explain_diagnostics(codes)

    @server.resource(
        "v8std://llms.txt",
        name="llms.txt",
        description="Compact v8std.ru LLM map.",
        mime_type="text/plain",
    )
    def llms_txt() -> str:
        return index.read_resource_text("llms.txt")

    @server.resource(
        "v8std://llms-full.txt",
        name="llms-full.txt",
        description="Full cleaned Markdown corpus for v8std.ru.",
        mime_type="text/plain",
    )
    def llms_full_txt() -> str:
        return index.read_resource_text("llms-full.txt")

    @server.resource(
        "v8std://ai/pages.jsonl",
        name="pages.jsonl",
        description="Machine-readable v8std.ru pages index.",
        mime_type="application/jsonl",
    )
    def pages_jsonl() -> str:
        return index.read_resource_text("pages.jsonl")

    @server.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(_: Request) -> Response:
        status = index.status()
        status_code = 200 if status.get("ok") else 503
        return JSONResponse(status, status_code=status_code)

    @server.custom_route("/version", methods=["GET"], include_in_schema=False)
    async def version(_: Request) -> Response:
        return JSONResponse({"service": "v8std-mcp", "api": "v2", **index.status()})

    install_self_documenting_mcp_app(server, mcp_path=mcp_path)

    return server


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the v8std.ru read-only MCP server.")
    parser.add_argument("--pages", type=Path, help="Read pages JSONL from a local file.")
    parser.add_argument("--vectors", type=Path, help="Read search vectors JSONL from a local file.")
    parser.add_argument("--index-url", default=DEFAULT_INDEX_URL, help="Remote pages JSONL URL.")
    parser.add_argument("--vectors-url", default=DEFAULT_VECTORS_URL, help="Remote vectors JSONL URL.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--refresh-seconds", type=int, default=DEFAULT_REFRESH_SECONDS)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--mcp-path", default="/mcp")
    parser.add_argument(
        "--allowed-host",
        action="append",
        default=["127.0.0.1:*", "localhost:*", "ai.v8std.ru", "ai.v8std.ru:*"],
        help="Allowed Host header for MCP transport security. Can be repeated.",
    )
    parser.add_argument(
        "--allowed-origin",
        action="append",
        default=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "https://ai.v8std.ru",
            "https://ai.v8std.ru:*",
        ],
        help="Allowed Origin header for MCP transport security. Can be repeated.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    index = V8StdIndex(
        pages_path=args.pages,
        vectors_path=args.vectors,
        index_url=args.index_url,
        vectors_url=args.vectors_url,
        cache_dir=args.cache_dir,
        refresh_seconds=args.refresh_seconds,
    )
    index.load()

    server = build_server(
        index,
        host=args.host,
        port=args.port,
        mcp_path=args.mcp_path,
        allowed_hosts=args.allowed_host,
        allowed_origins=args.allowed_origin,
    )
    server.run(transport="streamable-http")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
