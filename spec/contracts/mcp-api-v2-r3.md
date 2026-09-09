---
schema_version: 1
kind: contract
id: MCP_API
scope: product
version: 2
revision: 3
compatibility: backward-compatible
design: design:mcp-large-procedure-retrieval
producer: MCP combined runtime /mcp
consumers:
  - existing MCP v2 clients
  - coding agents using tools/list and tools/call
  - operators of local Python and Docker MCP instances
  - resource-capable MCP clients
requirements:
  - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
  - MCP_COMBINED_ENDPOINT_CAPABILITIES
  - MCP_COMBINED_PAGE_READING_COMPATIBLE
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
  - docker-compose/docker-compose.yml
  - deploy/nginx/server-v8std-mcp.conf
  - deploy/systemd/v8std-mcp.service
  - docs/mcp.md
  - tests/test_v8std_mcp_server.py
  - tests/test_v8std_mcp_index.py
  - tests/test_v8std_mcp_snippet.py
  - tests/test_v8std_mcp_combined.py
conformance:
  module: tests.test_v8std_mcp_snippet
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_snippet tests.test_v8std_mcp_server tests.test_v8std_mcp_index tests.test_v8std_mcp_combined -v
required_when: implemented
supersedes:
  - contract:MCP_API@2.2
deprecates:
  - contract:MCP_API@3.0
---

# MCP API v2.3: bounded snippet retrieval

## Сохранённая граница

Один `/mcp`, прежние пять tool names, обязательные аргументы и типы полей
ответов сохраняются, в том числе `v8std_get_page`. Additive Resources-профиль
из v2.2 не удаляется и не расширяется этим уточнением; второй `/v3/mcp` не
появляется. Номер этого внутреннего contract не меняет MCP protocol negotiation
или строку application API version в `/version`.

## Ввод и discovery

`v8std_explain_snippet.snippet` по умолчанию допускает до 4000 символов исходной
декодированной строки; локальный экземпляр может быть явно настроен до 32000.
Предел фиксируется при запуске, указан в `tools/list` как `maxLength` и в
описании инструмента и совпадает с фактической проверкой индекса. Внешний
текстовый `v8std_search.query` сохраняет предел 500.

Правила разрешения CLI/env, диапазон, ошибки конфигурации и способы запуска
нормативно заданы в `design:mcp-large-procedure-retrieval`. Превышение размера
даёт MCP tool error с эффективным пределом без исходного текста; direct index
даёт ValueError. Точная SDK-обёртка сообщения не фиксируется. Невалидный ввод не
обрезается до допустимого; транспортный byte-limit является отдельной границей.

## Результат

Сохраняются поля `language`, `normalized_text`, `tokens`, `signals`,
`diagnostics`, `standards`, `confidence`. Preview ограничен 1000 символами;
уникальные токены — 80 элементами и суммарно 4000 символами без подрезки
отдельного токена. Идентичные сигналы выдаются один раз, не как счётчик
повторений; различные сигналы сохраняются.

Распознанные первичные цели имеют приоритет над дополнительными и текстовыми
рекомендациями. Общий top-K делится на прежние два массива; сумма их длин
не превышает `limit` с прежними default 10 и maximum 50. Место каждой цели
гарантируется только когда K вмещает все существующие первичные цели.
Порядок/score snippet-рекомендаций может измениться как исправление retrieval;
новый числовой `score_details.snippet_signal` и `match_reasons` объясняют вклад.
Обычный поиск и его ранжирование от настройки snippet не меняются.

`confidence` остаётся ограниченной 0..1 эвристикой, не вероятностью нарушения.
Ответ не включает новые полные статьи или полный исходный код. Usage-лог не
получает исходную процедуру, литералы или полный tool error с входным payload.

## Совместимость и доказательства

Revision совместима по действующим tool arguments/result shape и сохраняет
прежний допустимый default-ввод; расширение окна только явное. Новое schema
ограничение описывает уже существующую runtime-границу. Удаление повторов
SDBL уточняет set-like семантику `signals`, уже применявшуюся к вызовам; ни
позиции, ни кратность нарушения этот API не обещает.

Wire conformance проверяет discovery и вызовы одного и того же экземпляра
для default/override, ошибки, оба JSON-представления Unicode и неизменные
legacy tools. Полная матрица приёмки находится в design. На этапе candidate
новая conformance-декларация не свидетельствует о выполненной реализации.
