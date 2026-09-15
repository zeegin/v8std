---
schema_version: 1
kind: contract
id: MCP_USAGE_EVENTS
scope: product
version: 1
revision: 1
compatibility: backward-compatible
design: design:mcp-public-monitoring-retirement
producer: current MCP logger and nginx
consumers: [private operator diagnostics]
requirements: [PRIVATE_USAGE_HISTORY_IS_PRESERVED]
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_usage.logrotate
conformance:
  module: tests.test_v8std_mcp_server
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_server -v
required_when: accepted
supersedes: [contract:MCP_USAGE_EVENTS@1.0]
deprecates: []
---

# Private legacy usage events

Существующий JSONL формат с `ts`/`tool` и необязательными metadata не меняется.
Отсутствие `schema_version` и `api` остаётся допустимым. Существующие файлы,
rotation и текущие writer settings не переписываются при retirement.
Потребитель теперь только операторская диагностика; публичный aggregator
удалён. Эта совместимая ревизия переносит conformance на действующий logger,
не обещает новую схему, reader либо exactly-once запись.
