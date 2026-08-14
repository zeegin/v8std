---
schema_version: 1
kind: invariant
id: METRICS_LABEL_CARDINALITY_IS_BOUNDED
scope: product
introduced_by: adr:LOCAL_OPENMETRICS_EXPOSITION
requirements: [METRICS_EXCLUDE_HIGH_CARDINALITY_LABELS]
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

# Metric label cardinality is bounded

Labels выбираются из конечных нормализованных множеств и не содержат IP,
user-agent, request ID, cursor, URI или query text. Неограниченный label
опровергает безопасность и эксплуатационную пригодность OpenMetrics contract.
