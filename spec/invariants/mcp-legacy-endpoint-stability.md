---
schema_version: 1
kind: invariant
id: MCP_LEGACY_ENDPOINT_STABILITY
scope: product
introduced_by: adr:MCP_VERSION_ENDPOINT_ISOLATION
requirements: [MCP_LEGACY_VERSION_REMAINS_COMPATIBLE]
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_index.py
check:
  module: tests.test_v8std_mcp_server
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_mcp_index -v
required_when: accepted
---

# Legacy MCP endpoint remains stable

`/mcp` продолжает предоставлять действующий MCP v2 contract независимо от
наличия v3. Изменение legacy tool names, inputs или result shape как побочный
эффект v3 опровергает решение об изоляции endpoint.
