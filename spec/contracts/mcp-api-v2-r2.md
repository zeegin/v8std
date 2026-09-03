---
schema_version: 1
kind: contract
id: MCP_API
scope: product
version: 2
revision: 2
compatibility: backward-compatible
design: design:mcp-combined-endpoint
producer: MCP combined runtime /mcp
consumers:
  - existing MCP v2 clients
  - resource-capable MCP clients
requirements:
  - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
  - MCP_COMBINED_ENDPOINT_CAPABILITIES
  - MCP_COMBINED_PAGE_READING_COMPATIBLE
governs:
  - scripts/v8std_mcp_server.py
  - deploy/nginx/server-v8std-mcp.conf
  - deploy/systemd/v8std-mcp.service
  - docs/mcp.md
  - tests/test_v8std_mcp_server.py
  - tests/test_v8std_mcp_combined.py
conformance:
  module: tests.test_v8std_mcp_combined
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_mcp_combined -v
required_when: implemented
supersedes:
  - contract:MCP_API@2.1
deprecates:
  - contract:MCP_API@3.0
---

# MCP API v2.2 combined profile

The public contract has one endpoint, `/mcp`, and one runtime. The five v2
tools, their names, inputs, results, and `v8std_get_page` remain available.

MCP Resources are an additive capability profile on the same endpoint. A
resource-capable client may use `resources/list` and `resources/read`; a
tool-only v2 client continues to use `v8std_get_page`. No application-version
negotiation or client metadata heuristic changes the tool catalog.

The separate future `/v3/mcp` contract is deprecated before implementation and
must not be deployed.
