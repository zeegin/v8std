---
schema_version: 1
kind: invariant
id: MCP_VERSION_ISOLATION
scope: product
introduced_by: adr:MCP_VERSION_ENDPOINT_ISOLATION
requirements: [MCP_VERSIONS_FAIL_INDEPENDENTLY]
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_v3.py
check:
  module: tests.test_v8std_mcp_versions
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_versions -v
required_when: implemented
---

# MCP versions fail independently

Отказ запуска, маршрутизации или каталога `/v3/mcp` не изменяет доступность
`/mcp`. Общий failure domain, из-за которого новая версия останавливает legacy
endpoint, опровергает решение `MCP_VERSION_ENDPOINT_ISOLATION`.
