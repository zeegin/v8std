---
schema_version: 1
kind: invariant
id: PRIVATE_OPERATIONAL_DATA_IS_NOT_PUBLISHED
scope: product
introduced_by: adr:RETIRE_PUBLIC_MCP_MONITORING
requirements:
  - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
  - PRIVATE_USAGE_HISTORY_IS_PRESERVED
governs:
  - deploy/container/edge-locations.conf
  - scripts/v8std_mcp_server.py
check:
  module: tests.test_v8std_mcp_monitoring_retirement
  command: V8STD_MONITORING_RETIREMENT_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring_retirement tests.test_v8std_mcp_server -v
required_when: implemented
---

# Операционные данные остаются закрытыми без dashboard

Raw logs и архив вне публикуемого дерева; ни root archive, ни usage log не
имеют HTTP alias. Retired routes не отдают существовавшие HTML/JSON даже при
случайном возврате старых файлов. Проверка host ACL и отсутствия alias
фиксируется в operations evidence; logger conformance остаётся отдельной.
