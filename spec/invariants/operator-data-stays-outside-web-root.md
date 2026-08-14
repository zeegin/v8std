---
schema_version: 1
kind: invariant
id: OPERATOR_DATA_STAYS_OUTSIDE_WEB_ROOT
scope: product
introduced_by: adr:PUBLIC_MCP_MONITORING
requirements: [OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT]
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_monitoring.py
check:
  module: tests.test_v8std_mcp_monitoring
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring -v
required_when: implemented
---

# Operator detail never enters the web root

Сырые события и детальные operator-only отчёты записываются вне публикуемого
дерева с ограниченными правами. Копирование этих данных в static site или
доступный Nginx path опровергает границу публичного monitoring.
