---
schema_version: 1
kind: invariant
id: METRICS_ENDPOINTS_ARE_LOOPBACK_ONLY
scope: product
introduced_by: adr:LOCAL_OPENMETRICS_EXPOSITION
requirements: [METRICS_ENDPOINTS_USE_LOOPBACK]
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_metrics.py
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_v3.py
check:
  module: tests.test_v8std_mcp_metrics
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_metrics -v
required_when: implemented
---

# Metrics endpoints bind only to loopback

OpenMetrics exposition слушает loopback и не маршрутизируется публичным proxy.
Внешний bind или публикация `/metrics` опровергает решение о локальной
генерации.
