#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from v8std_mcp_index import (
    DEFAULT_CACHE_DIR,
    DEFAULT_INDEX_URL,
    DEFAULT_REFRESH_SECONDS,
    DEFAULT_VECTORS_URL,
    MAX_BODY_CHARS,
    V8StdIndex,
)


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
            "Read-only access to v8std.ru standards, diagnostics, aliases, "
            "relations, source URLs, and cleaned Markdown."
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
            "Hybrid search over v8std.ru standards, diagnostics, patterns, and service pages."
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
        description="Get a v8std.ru page by id, alias, source path, HTML URL, or Markdown URL.",
    )
    def page(id_or_alias_or_url: str, body_limit: int = MAX_BODY_CHARS) -> dict[str, Any]:
        return index.page(id_or_alias_or_url, body_limit=body_limit)

    @server.tool(
        name="v8std_get_related",
        description="Return related standards, diagnostics, and EDT checks for a v8std.ru page.",
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
            "Analyze a short BSL/SDBL snippet and return recognized tokens, likely diagnostics, "
            "standards, and confidence."
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
            "Explain a batch of BSLLS, ACC, or v8-code-style diagnostics and group linked standards."
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

    @server.custom_route(f"{mcp_path.rstrip('/')}/", methods=["GET", "POST", "DELETE"], include_in_schema=False)
    async def mcp_slash_redirect(_: Request) -> Response:
        return RedirectResponse(mcp_path.rstrip("/") or "/mcp", status_code=308)

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
