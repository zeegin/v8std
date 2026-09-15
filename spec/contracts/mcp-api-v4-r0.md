---
schema_version: 1
kind: contract
id: MCP_API
scope: product
version: 4
revision: 0
compatibility: breaking
design: design:mcp-tools-only
producer: one published tools-only MCP runtime over Streamable HTTP or stdio
consumers:
  - coding agents using the five existing tools
  - former resource-capable MCP clients migrating to tools
  - local Python, Docker, Compose and Gateway clients
  - runtime readiness probes
requirements:
  - MCP_RESOURCES_ARE_DISABLED
  - MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE
  - MCP_RESOURCE_PRESENTATION_IS_NOT_BUILT
  - MCP_RESOURCE_REMOVAL_PRESERVES_CORPUS_DELIVERY
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
  - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
  - MCP_SNIPPET_ACCEPTED_INPUT_IS_SCANNED
  - MCP_SNIPPET_TARGETS_SURVIVE_QUERY_BUDGET
  - MCP_SNIPPET_INSTANCE_LIMIT_IS_DISCOVERABLE
  - MCP_SNIPPET_RETRIEVAL_WORK_IS_BOUNDED
  - MCP_SNIPPET_RESPONSE_STAYS_COMPACT
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_runtime.py
  - scripts/v8std_mcp_index.py
  - scripts/v8std_retrieval_rules.py
  - scripts/run_v8std_mcp.sh
  - scripts/check_mcp_container.py
  - scripts/check_mcp_load.py
  - deploy/nginx/server-v8std-mcp.conf
  - deploy/systemd/v8std-mcp.service
  - docker-compose/docker-compose.yml
  - docs/mcp.md
  - docs/container-installation.md
  - docs/support.md
  - tests/test_v8std_mcp_tools_only.py
  - tests/test_v8std_mcp_server.py
  - tests/test_v8std_mcp_index.py
  - tests/test_v8std_mcp_runtime.py
  - tests/test_v8std_mcp_snippet.py
  - tests/test_v8std_mcp_combined.py
  - tests/test_v8std_mcp_distribution.py
  - tests/test_v8std_mcp_load.py
conformance:
  module: tests.test_v8std_mcp_tools_only
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_tools_only tests.test_v8std_mcp_server tests.test_v8std_mcp_index tests.test_v8std_mcp_runtime tests.test_v8std_mcp_snippet tests.test_v8std_mcp_combined tests.test_v8std_mcp_distribution tests.test_v8std_mcp_load -v
required_when: implemented
supersedes:
  - contract:MCP_API@2.0
  - contract:MCP_API@2.1
  - contract:MCP_API@2.4
deprecates: []
---

# MCP API 4.0: прежние инструменты без Resources

## Совместимость и идентичность

Нормативно наследуется [API 2.4](mcp-api-v2-r4.md), кроме Resources,
их discovery/read/notifications, resource-specific errors и их объявления
в metadata. Для прежних tool-клиентов не меняются пять имён, schemas,
defaults, input limits, формы результатов, retrieval и ошибки.
Resource-only потребителю нужен переход на существующие tools.

`/mcp`, `api: v2`, protocol negotiation и site setting остаются прежними.
`api_profiles` равен `["legacy-tools"]`. Внутренний номер 4.0 обозначает
breaking removal, а не новую endpoint-версию или возобновление API 3.0.

## Ресурсная граница

Initialize не включает ключ `resources` в capabilities. При корректном MCP
lifecycle и валидном JSON-RPC request методы ниже возвращают error code
`-32601`, сохраняют request ID и не возвращают успешного `result`:

- `resources/list`;
- `resources/templates/list`;
- `resources/read`;
- `resources/subscribe`;
- `resources/unsubscribe`.

Текст ошибки компактный, не содержит corpus. Нет I/O или обращения к data
facade. Поведение одинаково при ready/not-ready/refresh, для старых
`v8std://llms.txt`, `v8std://llms-full.txt`, `v8std://ai/pages.jsonl`
и неизвестного URI. Невалидные JSON, protocol headers и параметры продолжают
подчиняться обычной транспортной/SDK-валидации, не маскируются под успешный отказ.

Нет templates, ResourceLink/embedded Resource в tool content, resource
notifications или переключателя включения. Обычные web URLs в прежних полях
tools остаются допустимыми. Prompts и другие незатронутые capabilities не
удаляются этим контрактом.

## Транспорт и данные

HTTP по-прежнему использует stateless POST с JSON; GET/SSE отклоняется.
Stdio использует тот же server без отдельного API-профиля; stdout только MCP.
Initialize/tools discovery не ждут сети. Data tools при cold bootstrap
возвращают прежний `INDEX_NOT_READY`; warm/offline и slow/corrupt refresh
не лишают их валидного поколения. Resource requests всегда отклоняются до
data path, поэтому `INDEX_NOT_READY` для Resources больше не существует.

Каждый tool удерживает одно immutable index generation. Дополнительная
полнотекстовая resource presentation не строится. Кеш поиска, background
coordinator, budgets, URL rebasing, health/liveness, private usage events и
bounded EOF/SIGTERM/drain сохраняются. Архив/статическая доставка определяются
snapshot 1.1; сам факт наличия llms в архиве не включает MCP Resources.

## Conformance

Будущий module проверяет фактические JSON-RPC frames HTTP и stdio, отсутствие
capability и handlers, сохранение пяти schemas и успешных tool responses,
все корректные resource methods и отсутствие side effects у отказа. Отдельно
проверяются warm cache от прежнего формата, cold source failure, refresh,
local-prefix URLs и shutdown. Container/load tests используют новый артефакт;
старые успешные resource tests не переименовываются в доказательство отключения.
