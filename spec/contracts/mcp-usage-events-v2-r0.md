---
schema_version: 1
kind: contract
id: MCP_USAGE_EVENTS
scope: product
version: 2
revision: 0
compatibility: backward-compatible
design: design:mcp-monitoring-dashboard
producer: future MCP v2 and v3 event emitters
consumers:
  - redesigned monitoring aggregator
requirements:
  - MONITORING_SHOWS_AGENT_FAMILIES
  - MONITORING_SHOWS_API_VERSIONS
  - MONITORING_SHOWS_MCP_OPERATIONS
  - PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA
  - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
  - LEGACY_USAGE_EVENTS_REMAIN_READABLE
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_v3.py
  - scripts/v8std_mcp_monitoring.py
conformance:
  module: tests.test_v8std_mcp_monitoring
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring.MonitoringEventV2Tests -v
required_when: implemented
supersedes: []
deprecates: []
---

# MCP usage events v2.0

## Envelope

Каждый JSONL event содержит `schema_version: 2`, ISO 8601 `ts`, `api` (`v2` или
`v3`), `kind`, `method`, `outcome`, нормализованный `agent_family` и
`agent_source`. Один JSON-RPC request создаёт не более одного usage event.

`kind` ограничен `initialize`, `mcp_operation`, `content_usage`; `outcome` —
`success`, `client_error`, `server_error`. Неизвестные method/agent
нормализуются в `other`/`unknown`, а не создают новую категорию.

Tool event может содержать только опубликованное имя `tool`, но не arguments.
Resource read может хранить тип и идентификаторы уже публичной страницы, но не
Markdown. Resource list хранит `page_size`, `result_count` и факт наличия
cursor, но не cursor и не состав страницы.

Исходные clientInfo, user-agent, IP, request ID и query text не записываются в
usage event. Search feedback хранится отдельным restricted потоком вне web root.

## Совместимость

Aggregator v2 читает одновременно v1 и v2. Сохранение v1 reader обязательно;
v2 не требует переписывать исторические JSONL-файлы.
