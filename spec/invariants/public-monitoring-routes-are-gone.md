---
schema_version: 1
kind: invariant
id: PUBLIC_MONITORING_ROUTES_ARE_GONE
scope: product
introduced_by: adr:RETIRE_PUBLIC_MCP_MONITORING
requirements: [PUBLIC_MONITORING_IS_RETIRED]
governs: [deploy/container/edge-locations.conf]
check:
  module: tests.test_v8std_mcp_monitoring_retirement
  command: V8STD_MONITORING_RETIREMENT_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring_retirement -v
required_when: implemented
---

# Dashboard не возвращается при следующей поставке

Точный `/monitoring` и prefix `/monitoring/` отвечают410/no-store независимо
от наличия старых файлов и доступности MCP upstream. Необходимы реальные
HTTP-проверки shipped nginx include, не поиск строки в конфигурации.
