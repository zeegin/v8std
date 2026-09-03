---
schema_version: 1
kind: invariant
id: MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME
scope: product
introduced_by: adr:MCP_COMBINED_ENDPOINT
requirements:
  - MCP_COMBINED_ENDPOINT_CAPABILITIES
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_server.py
  - deploy/nginx/server-v8std-mcp.conf
  - deploy/systemd/v8std-mcp.service
  - tests/test_v8std_mcp_combined.py
check:
  module: tests.test_v8std_mcp_combined
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_combined -v
required_when: implemented
---

# MCP uses one combined runtime

`/mcp` is served by one `v8std_mcp_server.py` runtime and the existing
`v8std-mcp.service`. No `/v3/mcp`, v3-specific listener, or v3-specific unit is
part of the deployable topology. Future Resources are additive capabilities of
the same runtime.
