#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import anyio

import mcp.types as mcp_types
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from runtime.v8std_mcp_index import (
    DEFAULT_CACHE_DIR,
    DEFAULT_INDEX_URL,
    DEFAULT_REFRESH_SECONDS,
    DEFAULT_VECTORS_URL,
    MAX_BODY_CHARS,
    MAX_SNIPPET_CHARS,
    MAX_SNIPPET_LIMIT_CHARS,
    V8StdIndex,
    validate_max_snippet_chars,
)
from runtime.v8std_mcp_runtime import SnapshotIndex
from runtime.v8std_mcp_snapshot_format import DEFAULT_SITE_URL, SnapshotError, normalize_site_url


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
MCP_EVENT_STREAM_DISABLED_MESSAGE = (
    "This stateless MCP endpoint does not provide an unsolicited SSE stream; "
    "send JSON-RPC requests with POST."
)
MCP_API_PROFILES = ["legacy-tools"]
MAX_USAGE_TEXT_CHARS = 240
MAX_USAGE_RESULTS = 50
MAX_USAGE_CODES = 500
DEFAULT_LOG_LEVEL = "WARNING"
CLIENT_SYSTEM_CONTEXT: ContextVar[str] = ContextVar("v8std_client_system", default="unknown")
ALLOWED_CLIENT_SYSTEMS = {
    "codex",
    "claude",
    "cursor",
    "jetbrains",
    "vscode",
    "curl",
    "browser",
    "node",
    "opencode",
    "go",
    "python_httpx",
    "kilo",
    "java",
    "unknown",
    "other",
}


def configure_runtime_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.WARNING)
    for logger_name in ("mcp", "uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(logger_name).setLevel(level)


def classify_client_system(user_agent: str) -> str:
    ua = user_agent.strip().lower()
    if not ua or ua == "-":
        return "unknown"
    if "codex" in ua or "openai" in ua:
        return "codex"
    if "claude" in ua or "anthropic" in ua:
        return "claude"
    if "cursor" in ua:
        return "cursor"
    if "jetbrains" in ua or "intellij" in ua or "pycharm" in ua or "webstorm" in ua:
        return "jetbrains"
    if "vscode" in ua or "visual studio code" in ua:
        return "vscode"
    if ua == "node" or "node/" in ua or "node.js" in ua or ua == "undici" or ua.startswith("got "):
        return "node"
    if "opencode" in ua:
        return "opencode"
    if "go-http-client" in ua:
        return "go"
    if "python-httpx" in ua:
        return "python_httpx"
    if ua.startswith("kilo/"):
        return "kilo"
    if "java-http-client" in ua:
        return "java"
    if "curl" in ua:
        return "curl"
    if "mozilla/" in ua or "safari/" in ua or "chrome/" in ua or "firefox/" in ua:
        return "browser"
    return "other"


def current_client_system() -> str:
    return CLIENT_SYSTEM_CONTEXT.get()


def _usage_system(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    system = value.strip().lower()
    if system not in ALLOWED_CLIENT_SYSTEMS:
        return None
    return system


def _usage_text(value: Any, *, limit: int = MAX_USAGE_TEXT_CHARS) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return normalized[:limit]


def _usage_url(value: Any) -> str | None:
    text = _usage_text(value, limit=500)
    if text is None:
        return None
    if text.startswith("https://v8std.ru/"):
        return text
    return None


def _usage_result(item: Any) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    url = _usage_url(item.get("url"))
    if url is None:
        return None
    result: dict[str, str] = {"url": url}
    page_id = _usage_text(item.get("id"), limit=120)
    title = _usage_text(item.get("title"))
    if page_id:
        result["id"] = page_id
    if title:
        result["title"] = title
    return result


def _usage_public_item(item: Any) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    result: dict[str, str] = {}
    page_id = _usage_text(item.get("id"), limit=120)
    code = _usage_text(item.get("code"), limit=120)
    title = _usage_text(item.get("title"))
    raw_url = _usage_text(item.get("url"), limit=500)
    url = _usage_url(item.get("url"))
    if raw_url and url is None:
        return None
    if page_id:
        result["id"] = page_id
    elif code:
        result["code"] = code
    if title:
        result["title"] = title
    if url:
        result["url"] = url
    return result or None


def _usage_results(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    results = []
    seen_urls = set()
    for item in items:
        result = _usage_result(item)
        if result is None:
            continue
        if result["url"] in seen_urls:
            continue
        seen_urls.add(result["url"])
        results.append(result)
        if len(results) >= MAX_USAGE_RESULTS:
            break
    return results


def _usage_frequency(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(1, min(value, MAX_USAGE_CODES))
    return 1


def _usage_diagnostic(item: Any) -> dict[str, str | int] | None:
    result = _usage_public_item(item)
    if result is None:
        return None
    result["frequency"] = _usage_frequency(item.get("frequency") if isinstance(item, dict) else None)
    return result


def _usage_diagnostics(items: Any) -> list[dict[str, str | int]]:
    if not isinstance(items, list):
        return []
    diagnostics = []
    seen_keys = set()
    for item in items:
        diagnostic = _usage_diagnostic(item)
        if diagnostic is None:
            continue
        key = diagnostic.get("url") or diagnostic.get("id") or diagnostic.get("code") or diagnostic.get("title")
        if key in seen_keys:
            continue
        seen_keys.add(key)
        diagnostics.append(diagnostic)
        if len(diagnostics) >= MAX_USAGE_RESULTS:
            break
    return diagnostics


def _usage_unknown_code(item: Any) -> dict[str, str | int] | None:
    if not isinstance(item, dict):
        return None
    code = _usage_text(item.get("code"), limit=120)
    if code is None:
        return None
    return {
        "code": code,
        "frequency": _usage_frequency(item.get("frequency")),
    }


def _usage_unknown_codes(items: Any) -> list[dict[str, str | int]]:
    if not isinstance(items, list):
        return []
    codes = []
    seen_codes = set()
    for item in items:
        unknown = _usage_unknown_code(item)
        if unknown is None or unknown["code"] in seen_codes:
            continue
        seen_codes.add(unknown["code"])
        codes.append(unknown)
        if len(codes) >= MAX_USAGE_RESULTS:
            break
    return codes


def _usage_standards_without_page(items: Any) -> list[dict[str, str | int]]:
    if not isinstance(items, list):
        return []
    standards = []
    seen_keys = set()
    for item in items:
        standard = _usage_diagnostic(item)
        if standard is None or standard.get("url"):
            continue
        key = standard.get("id") or standard.get("title")
        if key in seen_keys:
            continue
        seen_keys.add(key)
        standards.append(standard)
        if len(standards) >= MAX_USAGE_RESULTS:
            break
    return standards


class McpToolUsageLogger:
    def __init__(self, path: Path | None) -> None:
        self.path = path

    def record(self, tool_name: str, **metadata: Any) -> None:
        if self.path is None:
            return
        payload = {
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "tool": tool_name,
        }
        payload.update(
            {
                key: value
                for key, value in metadata.items()
                if value is not None and value != "" and value != []
            }
        )
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        except OSError:
            return

    def record_search(self, query: str, result: dict[str, Any], *, system: str | None = None) -> None:
        self.record(
            "v8std_search",
            system=_usage_system(system),
            query=_usage_text(query),
            normalized_query=_usage_text(result.get("normalized_query")),
            results=_usage_results(result.get("results")),
        )

    def record_page(self, requested_page: str, result: dict[str, Any], *, system: str | None = None) -> None:
        page = result.get("page") if isinstance(result, dict) else None
        page_result = _usage_result(page)
        if page_result is None:
            self.record(
                "v8std_get_page",
                system=_usage_system(system),
                requested_page=_usage_text(requested_page),
            )
            return
        self.record(
            "v8std_get_page",
            system=_usage_system(system),
            requested_page=_usage_text(requested_page),
            page_id=page_result.get("id"),
            title=page_result.get("title"),
            url=page_result.get("url"),
        )

    def record_diagnostics(self, codes: list[str], result: dict[str, Any], *, system: str | None = None) -> None:
        self.record(
            "v8std_explain_diagnostics",
            system=_usage_system(system),
            diagnostics=_usage_diagnostics(result.get("diagnostics") if isinstance(result, dict) else None),
            unknown_codes=_usage_unknown_codes(result.get("unknown_codes") if isinstance(result, dict) else None),
            standards_without_page=_usage_standards_without_page(result.get("standards") if isinstance(result, dict) else None),
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

        if path == self.mcp_path and method == "GET" and self._accepts_event_stream(scope):
            await self._send_event_stream_not_available(send)
            return

        if path == self.mcp_path and method == "GET" and not self._accepts_event_stream(scope):
            await self._send_self_documentation(send, prefer_json=self._prefers_json(scope), include_body=True)
            return

        await self._send_to_downstream(scope, receive, send)

    async def _send_to_downstream(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        token = CLIENT_SYSTEM_CONTEXT.set(classify_client_system(self._header(scope, b"user-agent")))
        try:
            await self.downstream(scope, receive, send)
        finally:
            CLIENT_SYSTEM_CONTEXT.reset(token)

    def _accept_header(self, scope: dict[str, Any]) -> str:
        return self._header(scope, b"accept").lower()

    def _header(self, scope: dict[str, Any], header_name: bytes) -> str:
        for key, value in scope.get("headers", []):
            if key.lower() == header_name:
                return value.decode("latin-1")
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

    async def _send_event_stream_not_available(self, send: Any) -> None:
        await self._send_response(
            send,
            405,
            [(b"allow", b"POST, HEAD")],
            b"text/plain; charset=utf-8",
            MCP_EVENT_STREAM_DISABLED_MESSAGE.encode("utf-8"),
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


def install_self_documenting_mcp_app(server: FastMCP, *, mcp_path: str, index=None) -> None:
    original_streamable_http_app = server.streamable_http_app

    def streamable_http_app_with_self_documentation():
        app = original_streamable_http_app()
        if isinstance(index, SnapshotIndex):
            original_lifespan = app.router.lifespan_context

            @asynccontextmanager
            async def lifespan(app):
                index.start()
                try:
                    async with original_lifespan(app) as state:
                        yield state
                finally:
                    with anyio.CancelScope(shield=True):
                        await anyio.to_thread.run_sync(index.close)

            app.router.lifespan_context = lifespan
        return SelfDocumentingMcpApp(app, mcp_path=mcp_path)

    server.streamable_http_app = streamable_http_app_with_self_documentation  # type: ignore[method-assign]




def _disable_resource_handlers(server: FastMCP) -> None:
    # SDK 1.27 registers these even without resource decorators. Removing the
    # handlers also removes the capability and uses normal Method not found dispatch.
    for request_type in (
        mcp_types.ListResourcesRequest,
        mcp_types.ListResourceTemplatesRequest,
        mcp_types.ReadResourceRequest,
        mcp_types.SubscribeRequest,
        mcp_types.UnsubscribeRequest,
    ):
        server._mcp_server.request_handlers.pop(request_type, None)


def build_server(
    index: V8StdIndex | SnapshotIndex,
    *,
    host: str,
    port: int,
    mcp_path: str,
    allowed_hosts: list[str],
    allowed_origins: list[str],
    log_level: str = DEFAULT_LOG_LEVEL,
    usage_logger: McpToolUsageLogger | None = None,
) -> FastMCP:
    tool_usage = usage_logger or McpToolUsageLogger(None)
    server = FastMCP(
        "v8std",
        log_level=log_level,
        instructions=(
            "Use this read-only MCP as a v8std.ru knowledge source for 1C:Enterprise "
            "BSL/SDBL standards, diagnostics, aliases, relations, source URLs, and "
            "clean Markdown. It does not run analyzers, inspect projects, or change code. "
            "Tool selection: use v8std_explain_snippet for one BSL procedure or SDBL fragment; "
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
    _disable_resource_handlers(server)

    @server.tool(
        name="v8std_search",
        description=(
            'Search the v8std knowledge base by a natural-language question, topic, or uncertain '
            'identifier. Returns ranked page IDs, titles, descriptions, URLs, scores and match '
            'reasons; no full article text. Known diagnostic codes are handled by '
            'v8std_explain_diagnostics; BSL/SDBL source fragments by v8std_explain_snippet. An exact '
            'page ID or URL can be read with v8std_get_page. An empty result means no match in this '
            'corpus, not that the code is correct. Scores rank candidates and are not probabilities.'
        ),
    )
    def search(
        query: Annotated[str, Field(description="Question, topic or uncertain identifier; up to 500 Unicode characters. Example: модальные окна. Not a source module.")],
        limit: Annotated[int, Field(description="Maximum results, default 10; clamped to 1–50.")] = 10,
        types: Annotated[list[str] | None, Field(description="Page types: standard, diagnostic, fix, pattern, service. null or [] means all types.")] = None,
        mode: Annotated[str, Field(description="hybrid: combined search (default); exact: includes identifier variants and fuzzy code matches; bm25: text/metadata; semantic: indexed vectors.")] = "hybrid",
    ) -> dict[str, Any]:
        result = index.search(query, types=types, mode=mode, limit=limit)
        tool_usage.record_search(query, result, system=current_client_system())
        return result

    @server.tool(
        name="v8std_get_page",
        description=(
            'Read a known v8std article by ID, alias, source path, HTML URL or Markdown URL, for '
            'example std437. Returns found, page metadata, Markdown text and body_truncated; an '
            'unknown page returns found=false and possible candidates. body_limit defaults to 12000 '
            'characters and is clamped to 1000–30000. A truncated body is incomplete; the returned '
            'markdown_url identifies the full document. This is document retrieval, not code '
            'analysis. For an unknown topic, v8std_search finds candidate IDs.'
        ),
    )
    def page(id_or_alias_or_url: Annotated[str, Field(description="Known article ID, alias, source path, HTML or Markdown URL; up to 1000 Unicode characters. Example: std437.")], body_limit: Annotated[int, Field(description="Markdown character budget, default 12000; clamped to 1000–30000. Truncation marker may add characters; inspect body_truncated.")] = MAX_BODY_CHARS) -> dict[str, Any]:
        result = index.page(id_or_alias_or_url, body_limit=body_limit)
        tool_usage.record_page(id_or_alias_or_url, result, system=current_client_system())
        return result

    @server.tool(
        name="v8std_get_related",
        description=(
            'Retrieve explicit corpus links from a known standard or diagnostic article. Returns '
            'related page IDs, relation types, titles, descriptions and URLs, filtered by relations '
            'and limited by limit. An unknown starting page returns found=false; an empty related '
            'list means no matching recorded links. Links provide reading context, not evidence that '
            'a rule is violated. This tool does not discover arbitrary topics or retrieve full '
            'article bodies; those operations are v8std_search and v8std_get_page.'
        ),
    )
    def related(
        id_or_alias_or_url: Annotated[str, Field(description="Known article ID, alias, source path, HTML or Markdown URL; up to 1000 Unicode characters. Example: std437.")],
        relations: Annotated[list[str] | None, Field(description="Relation kinds: standard, diagnostic, edt_check, related. Legacy related_standard and related_diagnostic accepted. null or [] means all.")] = None,
        limit: Annotated[int, Field(description="Maximum results, default 10; clamped to 1–50.")] = 10,
    ) -> dict[str, Any]:
        tool_usage.record("v8std_get_related", system=_usage_system(current_client_system()))
        return index.related(id_or_alias_or_url, relations=relations, limit=limit)

    def explain_snippet(
        snippet: str,
        language: Annotated[str, Field(description="Source-language hint: auto (default), bsl or sdbl. Currently echoed without selecting a separate analyzer.")] = "auto",
        limit: Annotated[int, Field(description="Combined diagnostics and standards budget, default 10; clamped to 1–50.")] = 10,
    ) -> dict[str, Any]:
        tool_usage.record("v8std_explain_snippet", system=_usage_system(current_client_system()))
        return index.explain_snippet(snippet, language=language, limit=limit)

    # Publish the effective bound without Pydantic echoing source code in a
    # length ValidationError. The index enforces this same bound on every call.
    explain_snippet.__annotations__["snippet"] = Annotated[
        str, Field(description="One relevant BSL procedure or SDBL fragment, limited by maxLength. Normalized output may contain source text; omit secrets.", json_schema_extra={"maxLength": index.max_snippet_chars})
    ]
    server.tool(
        name="v8std_explain_snippet",
        description=(
            'Match one BSL procedure or SDBL fragment against signals in the v8std knowledge base. '
            'Returns candidate diagnostics and standards, matched signals and heuristic confidence, '
            'with at most limit recommendations in total. It does not execute code, inspect a '
            'repository or run a static analyzer; matches are not confirmed violations and no matches '
            'do not certify correctness. Full rule text is available through v8std_get_page. '
            'Diagnostic identifiers from reports or source comments are handled by '
            f'v8std_explain_diagnostics. The fragment limit is {index.max_snippet_chars} Unicode characters; '
            'a size error requires a smaller relevant fragment, not an unchanged retry. language '
            'records the supplied hint and currently does not select a separate analyzer.'
        ),
    )(explain_snippet)

    @server.tool(
        name="v8std_explain_diagnostics",
        description=(
            'Resolve diagnostic identifiers from analyzer reports or source-code comments and '
            'suppressions, such as acc 1245, АПК:361, bslls:AssignAliasFieldsInQuery or an exact v8cs '
            'identifier. Accepts up to 500 strings, each up to 200 characters. Returns known '
            'diagnostics grouped with linked standards, occurrence frequencies and unknown_codes. '
            'Empty entries are ignored; repeated codes are counted. Unknown means not resolved in '
            'this corpus, not a verified invalid diagnostic. Resolving a suppression code does not '
            'justify the suppression. No wildcard matching or analyzer execution is performed. Full '
            'descriptions are available through v8std_get_page using returned IDs.'
        ),
    )
    def explain_diagnostics(codes: Annotated[list[str], Field(description="Exact diagnostic IDs with analyzer namespace when known; up to 500 entries, each up to 200 characters. Example: [acc 1245, bslls:AssignAliasFieldsInQuery]. Not a raw report.")]) -> dict[str, Any]:
        result = index.explain_diagnostics(codes)
        tool_usage.record_diagnostics(codes, result, system=current_client_system())
        return result

    @server.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(_: Request) -> Response:
        status = index.status()
        status_code = 200 if status.get("ok") else 503
        return JSONResponse(status, status_code=status_code)

    @server.custom_route("/livez", methods=["GET"], include_in_schema=False)
    async def livez(_: Request) -> Response:
        return JSONResponse({"ok": True})

    @server.custom_route("/version", methods=["GET"], include_in_schema=False)
    async def version(_: Request) -> Response:
        return JSONResponse(
            {"service": "v8std-mcp", "api": "v2", "api_profiles": MCP_API_PROFILES, **index.status()}
        )

    install_self_documenting_mcp_app(server, mcp_path=mcp_path, index=index)

    return server


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the v8std.ru read-only MCP server.")
    parser.add_argument("--pages", type=Path, help="Read pages JSONL from a local file.")
    parser.add_argument("--vectors", type=Path, help="Read search vectors JSONL from a local file.")
    parser.add_argument("--index-url", default=None, help="Explicit legacy remote pages JSONL URL.")
    parser.add_argument("--vectors-url", default=None, help="Explicit legacy remote vectors JSONL URL.")
    parser.add_argument("--site-url", default=None, help="Snapshot source and presentation site URL.")
    parser.add_argument("--transport", choices=["streamable-http"], default="streamable-http")
    parser.add_argument("--cache-dir", default=None, help="Overrides V8STD_MCP_CACHE_DIR.")
    parser.add_argument("--refresh-seconds", type=int, default=DEFAULT_REFRESH_SECONDS)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--mcp-path", default="/mcp")
    parser.add_argument(
        "--max-snippet-chars", default=None,
        help=(f"Maximum decoded snippet characters ({MAX_SNIPPET_CHARS}..{MAX_SNIPPET_LIMIT_CHARS}). "
              "Overrides V8STD_MCP_MAX_SNIPPET_CHARS; default is 4000."),
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=DEFAULT_LOG_LEVEL,
        help="Runtime log level for MCP SDK and uvicorn loggers. Defaults to WARNING to keep journald small.",
    )
    parser.add_argument(
        "--usage-log",
        type=Path,
        default=None,
        help="Append JSONL tool-call usage events to this path. Disabled by default.",
    )
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
    args = parser.parse_args(argv)
    cache = (args.cache_dir if args.cache_dir is not None
             else os.environ.get("V8STD_MCP_CACHE_DIR", str(DEFAULT_CACHE_DIR)))
    if not cache.strip():
        parser.error("--cache-dir / V8STD_MCP_CACHE_DIR must not be empty")
    args.cache_dir = Path(cache)
    if not 0 <= args.port <= 65535:
        parser.error("port must be from 0 to 65535")
    site = args.site_url if args.site_url is not None else os.environ.get("V8STD_MCP_SITE_URL")
    legacy = any(value is not None for value in (args.pages, args.vectors, args.index_url, args.vectors_url))
    if legacy and site is not None:
        parser.error("explicit legacy sources cannot be combined with SITE_URL")
    if args.refresh_seconds < 0:
        parser.error("refresh-seconds must be nonnegative")
    try:
        args.site_url = None if legacy else normalize_site_url(site if site is not None else DEFAULT_SITE_URL)
    except SnapshotError:
        parser.error("invalid SITE_URL")
    args.index_url = args.index_url if args.index_url is not None else DEFAULT_INDEX_URL
    args.vectors_url = args.vectors_url if args.vectors_url is not None else DEFAULT_VECTORS_URL
    raw_limit = args.max_snippet_chars
    if raw_limit is None:
        raw_limit = os.environ.get("V8STD_MCP_MAX_SNIPPET_CHARS", str(MAX_SNIPPET_CHARS))
    raw_limit = raw_limit.strip()
    try:
        if not raw_limit.isascii() or not raw_limit.isdecimal():
            raise ValueError("not an ASCII integer")
        args.max_snippet_chars = validate_max_snippet_chars(int(raw_limit))
    except ValueError:
        parser.error(
            "--max-snippet-chars / V8STD_MCP_MAX_SNIPPET_CHARS must be an integer "
            f"from {MAX_SNIPPET_CHARS} to {MAX_SNIPPET_LIMIT_CHARS}"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    configure_runtime_logging(args.log_level)
    if args.site_url is not None:
        index = SnapshotIndex(site_url=args.site_url, cache_dir=args.cache_dir,
                              refresh_seconds=args.refresh_seconds, max_snippet_chars=args.max_snippet_chars,
                              runtime_sha=os.environ.get("V8STD_MCP_RUNTIME_SHA"))
    else:
        index = V8StdIndex(
            pages_path=args.pages,
            vectors_path=args.vectors,
            index_url=args.index_url,
            vectors_url=args.vectors_url,
            cache_dir=args.cache_dir,
            refresh_seconds=args.refresh_seconds,
            max_snippet_chars=args.max_snippet_chars,
        )
        index.load()

    server = build_server(
        index,
        host=args.host,
        port=args.port,
        mcp_path=args.mcp_path,
        allowed_hosts=args.allowed_host,
        allowed_origins=args.allowed_origin,
        log_level=args.log_level,
        usage_logger=McpToolUsageLogger(args.usage_log),
    )
    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
