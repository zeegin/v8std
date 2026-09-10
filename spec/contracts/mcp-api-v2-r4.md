---
schema_version: 1
kind: contract
id: MCP_API
scope: product
version: 2
revision: 4
compatibility: backward-compatible
design: design:mcp-container-distribution
producer: one combined MCP runtime over Streamable HTTP or stdio
consumers:
  - existing MCP v2 clients
  - coding agents using tools and Resources
  - local container and Docker Gateway clients
  - runtime readiness probes
requirements:
  - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_COMBINED_PAGE_READING_COMPATIBLE
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
  - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
  - MCP_SNIPPET_ACCEPTED_INPUT_IS_SCANNED
  - MCP_SNIPPET_TARGETS_SURVIVE_QUERY_BUDGET
  - MCP_SNIPPET_INSTANCE_LIMIT_IS_DISCOVERABLE
  - MCP_SNIPPET_RETRIEVAL_WORK_IS_BOUNDED
  - MCP_SNIPPET_RESPONSE_STAYS_COMPACT
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_index.py
  - scripts/v8std_retrieval_rules.py
  - scripts/run_v8std_mcp.sh
  - deploy/nginx/server-v8std-mcp.conf
  - deploy/systemd/v8std-mcp.service
  - docker-compose/docker-compose.yml
  - docs/mcp.md
  - docs/support.md
  - tests/test_v8std_mcp_server.py
  - tests/test_v8std_mcp_index.py
  - tests/test_v8std_mcp_snippet.py
  - tests/test_v8std_mcp_combined.py
  - tests/test_v8std_mcp_distribution.py
conformance:
  module: tests.test_v8std_mcp_distribution
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_distribution tests.test_v8std_mcp_snippet tests.test_v8std_mcp_server tests.test_v8std_mcp_index tests.test_v8std_mcp_combined -v
required_when: implemented
supersedes:
  - contract:MCP_API@2.3
deprecates: []
---

# MCP API v2.4: поставка и lifecycle

## Совместимость

Нормативно сохраняется [API 2.3](mcp-api-v2-r3.md) целиком, кроме способа
инициализации/обновления index и буквальной привязки к одному process/unit.
Ни версия MCP protocol, ни application API version в `/version` не становятся
`2.4` из-за номера этого внутреннего контракта. Нет `/v3/mcp`, новых обязательных
tool arguments, эвристики по имени агента или удаления `v8std_get_page`.

Сохраняются пять tools и три текущих bulk Resources, без нового bulk discovery.
Результаты, ошибки ввода, лимиты snippet 4000 по умолчанию / 32000 максимум,
search query 500, preview 1000, tokens 80 и суммарно 4000, один hybrid search
и compact top-K нормативно наследуются. Refresh не меняет ranking model.

## Транспорт и жизненный цикл

HTTP — stateless Streamable HTTP с JSON-ответами и текущей POST-only политикой
edge. Долгоживущий GET/SSE для уведомлений не появляется. Stdio запускает тот
же набор tools/Resources; stdout только MCP, журналы в stderr. SIGTERM и EOF
ограниченно завершают процессы/задачи, без orphan refresh worker.

Initialize и discovery не ждут сети: schema и допустимые лимиты известны из
конфигурации. До первого валидного snapshot обращения, которым нужны данные,
получают MCP tool/resource error с кодом в тексте `INDEX_NOT_READY` и указанием
повторить позже; SDK-обёртка не фиксируется. Не выдаются пустые успешные результаты
и не запускается синхронная загрузка от этого обращения. Ошибки ввода проверяются
до готовности данных там, где проверка не требует corpus.

Существующий HTTP `/healthz` возвращает 200 только при готовом active snapshot,
иначе 503. Additive `/livez` проверяет жизнь runtime, не сеть.
Freshness отдельно от readiness: валидный stale snapshot остаётся готовым.
Health/version metadata добавляют runtime SHA, corpus ID, время последней
успешной проверки и компактную категорию refresh error; secrets, raw code,
локальные filesystem paths и содержимое corpus туда не попадают.

Каждый data request захватывает одну ссылку на immutable snapshot. Поиск,
сигналы, страницы и Resources внутри запроса не смешивают поколения. Внешний
I/O отсутствует на request path; подготовка следующего index не держит query
lock. Параметры refresh и source берутся при запуске, не из tool input.

## Проверки

Нужны wire tests stdio/HTTP, initialize до доступности источника, два агента,
warm/cold startup, clean EOF/SIGTERM, совместимость прежних tools/Resources
и ответы во время медленного/повреждённого refresh. Новый conformance module
является задачей реализации, а не существующим доказательством.
