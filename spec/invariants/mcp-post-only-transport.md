---
schema_version: 1
kind: invariant
id: MCP_POST_ONLY_TRANSPORT
scope: product
introduced_by: adr:MCP_POST_ONLY_EDGE_DRAIN
requirements: [MCP_POST_ONLY_AGENT_TRANSPORT]
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_server.py
  - tests/test_v8std_mcp_server.py
check:
  module: tests.test_v8std_mcp_server
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_server -v
required_when: implemented
---

# Stateless MCP does not retain unsolicited SSE streams

`GET /mcp` with an `Accept` header containing `text/event-stream` returns HTTP
405 and `Allow: POST, HEAD`. Browser self-documentation and normal JSON-RPC
POST requests remain available. The server does not create a long-lived
connection for an agent that is idle between tool calls.
