---
schema_version: 1
kind: contract
id: MCP_USAGE_EVENTS
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:mcp-monitoring-dashboard
producer: current MCP logger and Nginx
consumers:
  - current monitoring aggregator
requirements: [LEGACY_USAGE_EVENTS_REMAIN_READABLE]
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_monitoring.py
conformance:
  module: tests.test_v8std_mcp_monitoring
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_mcp_monitoring -v
required_when: accepted
supersedes: []
deprecates: []
---

# MCP usage events v1.0

## Legacy event

Текущий JSONL event может не содержать `schema_version` и `api`. Наличие `tool`
идентифицирует legacy v2 tool call; `ts`, `tool`, публичный `page_id` и
агрегируемые числовые поля читаются текущим aggregator. Неизвестное или
отсутствующее новое измерение нормализуется в `unknown`, а не делает строку
нечитаемой.

Этот контракт сохраняется для исторических файлов и сквозных окон. Новые
emitters не обязаны продолжать создавать v1 после появления versioned v2 event.
