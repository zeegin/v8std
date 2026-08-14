---
schema_version: 1
kind: contract
id: MCP_MONITORING_PROJECTION
scope: product
version: 2
revision: 0
compatibility: breaking
design: design:mcp-monitoring-dashboard
producer: redesigned monitoring aggregator
consumers:
  - public monitoring dashboard
  - local SSH operator view
requirements:
  - MONITORING_SHOWS_AGENT_FAMILIES
  - MONITORING_SHOWS_API_VERSIONS
  - MONITORING_SHOWS_MCP_OPERATIONS
  - PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA
  - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
  - MONITORING_REMAINS_PUBLIC
governs:
  - scripts/v8std_mcp_monitoring.py
conformance:
  module: tests.test_v8std_mcp_monitoring
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring.MonitoringProjectionV2Tests -v
required_when: implemented
supersedes: []
deprecates: []
---

# MCP monitoring projection v2.0

## Публичная проекция

`/monitoring/` показывает агрегаты за фиксированные окна: семейства агентов,
API v2/v3, классы MCP operations, нормализованные tool names, outcomes и
популярность публичных материалов. Unknown остаётся явной категорией.

Публичные JSON/HTML не содержат IP, raw user-agent/clientInfo, request ID,
cursor, query text, tool arguments, произвольный resource URI или группы ниже
порогов раскрытия. Генератор атомарно заменяет только успешно построенный
artifact; при ошибке Nginx отдаёт предыдущую исправную версию.

## Операторская проекция

Расширенный отчёт и raw/restricted inputs находятся вне web root с правами не
шире `0640`. Внешний HTTP route для них отсутствует; получение выполняется
оператором через SSH/SCP.

Версия 2 breaking по JSON/data model относительно legacy projection, но не
удаляет v1 artifact до отдельного rollout и подтверждённого rollback path.
