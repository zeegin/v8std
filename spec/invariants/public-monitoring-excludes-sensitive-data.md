---
schema_version: 1
kind: invariant
id: PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA
scope: product
introduced_by: adr:PUBLIC_MCP_MONITORING
requirements: [PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA]
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_monitoring.py
  - docs/monitoring/
check:
  module: tests.test_v8std_mcp_monitoring
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring -v
required_when: implemented
---

# Public monitoring contains only safe aggregates

Публичная проекция не раскрывает IP, сырой user-agent, request ID, cursor, URI,
query text или идентифицируемые малые срезы. Появление любого такого значения
опровергает решение оставить monitoring публичным.
