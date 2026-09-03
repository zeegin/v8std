---
schema_version: 1
kind: invariant
id: MCP_OVERLOAD_IS_RETRYABLE
scope: product
introduced_by: adr:MCP_POST_ONLY_EDGE_DRAIN
requirements: [MCP_OVERLOAD_RETURNS_RETRYABLE_STATUS]
owner: v8std maintainers
governs:
  - deploy/nginx/server-v8std-mcp.conf
  - spec/contracts/mcp-api-v2-r1.md
  - tests/test_v8std_mcp_capacity.py
check:
  module: tests.test_v8std_mcp_capacity
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_capacity -v
required_when: implemented
---

# Admission failures are explicit and retryable

Request-rate admission returns 429; connection admission and backend
unavailability return 503. Upstream 502/504 failures are normalized to 503 at
the edge. Connection exhaustion must not be surfaced as a generic nginx 500.
The edge uses `Retry-After` policy at the deployment boundary and keeps
overload observable in metrics and access logs.
