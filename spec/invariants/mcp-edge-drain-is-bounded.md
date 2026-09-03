---
schema_version: 1
kind: invariant
id: MCP_EDGE_DRAIN_IS_BOUNDED
scope: product
introduced_by: adr:MCP_POST_ONLY_EDGE_DRAIN
requirements: [MCP_WORKER_DRAIN_IS_BOUNDED]
owner: v8std maintainers
governs:
  - deploy/nginx/nginx.conf.capacity-example
  - deploy/nginx/http-v8std-mcp.conf
  - deploy/systemd/v8std-mcp.service
  - tests/test_v8std_mcp_capacity.py
check:
  module: tests.test_v8std_mcp_capacity
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_capacity -v
required_when: implemented
---

# Edge workers have a finite drain deadline

The capacity deployment sets `worker_shutdown_timeout 30s`, an effective nginx
file-descriptor limit of at least 131,072, a 40,000-connection admission cap
per edge node, and a matching MCP service limit. Existing long-lived streams
cannot keep an old worker alive indefinitely after reload.
