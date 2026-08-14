---
schema_version: 1
kind: contract
id: MCP_API
scope: product
version: 2
revision: 0
compatibility: backward-compatible
design: design:mcp-v3-resource-contract
producer: MCP v2 /mcp
consumers:
  - existing MCP clients
requirements:
  - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
  - MCP_VERSIONS_FAIL_INDEPENDENTLY
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_index.py
conformance:
  module: tests.test_v8std_mcp_server
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_mcp_index -v
required_when: accepted
supersedes: []
deprecates: []
---

# MCP API v2.0

## Endpoint и возможности

Streamable HTTP endpoint `/mcp` остаётся stateless и предоставляет tools
`v8std_search`, `v8std_get_page`, `v8std_get_related`,
`v8std_explain_snippet`, `v8std_explain_diagnostics`. Он также сохраняет
агрегированные Resources `llms.txt`, `llms-full.txt` и `pages.jsonl`.

MCP v3 не меняет tool names, input schemas, result shapes, endpoint или
refresh-поведение v2. Ошибка отдельного v3 process не является допустимой
причиной недоступности `/mcp`.

## Совместимость

Добавление необязательных полей, принимаемых существующими клиентами, требует
новой revision. Удаление `v8std_get_page`, смена endpoint или несовместимое
изменение схемы требует новой major-версии и не выполняется в этом контракте.
