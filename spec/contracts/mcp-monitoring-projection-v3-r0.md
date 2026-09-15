---
schema_version: 1
kind: contract
id: MCP_MONITORING_PROJECTION
scope: product
version: 3
revision: 0
compatibility: breaking
design: design:mcp-public-monitoring-retirement
producer: nginx edge
consumers: [former public monitoring clients]
requirements: [PUBLIC_MONITORING_IS_RETIRED]
governs: [deploy/container/edge-locations.conf]
conformance:
  module: tests.test_v8std_mcp_monitoring_retirement
  command: V8STD_MONITORING_RETIREMENT_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring_retirement -v
required_when: implemented
supersedes:
  - contract:MCP_MONITORING_PROJECTION@1.0
  - contract:MCP_MONITORING_PROJECTION@2.0
deprecates: []
---

# Retired monitoring HTTP boundary

HTTPS GET/HEAD `/monitoring`, `/monitoring/` и любой дочерний path отвечают410
с `Cache-Control: no-store`. Query parameters не меняют результат.
Тело не содержит dashboard data; HEAD без тела. Другие методы также не
возвращают старые данные. HTTP может пройти существующий TLS redirect.
Публичного JSON и заменяющего его отчёта больше нет.
