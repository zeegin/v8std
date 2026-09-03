---
schema_version: 1
kind: contract
id: MCP_API
scope: product
version: 2
revision: 1
compatibility: backward-compatible
design: design:mcp-100k-agent-capacity
producer: MCP v2 /mcp
consumers:
  - existing MCP clients
requirements:
  - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
  - MCP_POST_ONLY_AGENT_TRANSPORT
  - MCP_AGENT_REQUESTS_SCALE_HORIZONTALLY
  - MCP_OVERLOAD_RETURNS_RETRYABLE_STATUS
governs:
  - scripts/v8std_mcp_server.py
  - deploy/nginx/server-v8std-mcp.conf
  - docs/mcp.md
  - tests/test_v8std_mcp_server.py
  - tests/test_v8std_mcp_capacity.py
conformance:
  module: tests.test_v8std_mcp_server
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_mcp_capacity -v
required_when: implemented
supersedes:
  - contract:MCP_API@2.0
deprecates: []
---

# MCP API v2.1

The `/mcp` endpoint preserves the v2 tools, inputs, JSON-RPC POST lifecycle,
resources, and browser self-documentation. Because the server is stateless and
does not send unsolicited server-to-client messages, `GET /mcp` requests that
offer `text/event-stream` receive `405 Method Not Allowed` with
`Allow: POST, HEAD`. This is the transport-level capacity clarification; it
does not remove or rename any v2 tool.

Admission overload is represented by retryable 429/503 responses at the edge;
upstream 502/504 failures are normalized to 503, rather than exposing an
nginx 500 caused by exhausted worker connections.
