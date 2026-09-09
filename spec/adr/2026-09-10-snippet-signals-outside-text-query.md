---
schema_version: 1
kind: adr
id: SNIPPET_SIGNALS_OUTSIDE_TEXT_QUERY
scope: product
design: design:mcp-large-procedure-retrieval
requirements:
  - MCP_SNIPPET_ACCEPTED_INPUT_IS_SCANNED
  - MCP_SNIPPET_TARGETS_SURVIVE_QUERY_BUDGET
  - MCP_SNIPPET_INSTANCE_LIMIT_IS_DISCOVERABLE
  - MCP_SNIPPET_RETRIEVAL_WORK_IS_BOUNDED
  - MCP_SNIPPET_RESPONSE_STAYS_COMPACT
aliases: []
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MCP_SNIPPET_SIGNALS_SURVIVE_TEXT_BUDGET
  preserves:
    - invariant:MCP_LEGACY_ENDPOINT_STABILITY
    - invariant:MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME
  replaces: {}
  cancels: []
contracts:
  introduces:
    - contract:MCP_API@2.3
  preserves: []
  replaces:
    contract:MCP_API@2.2: contract:MCP_API@2.3
  cancels: []
---

# Структурные признаки snippet вне текстового поискового запроса

## Решение

Не использовать строку обычного поиска как единственный канал передачи
результатов анализа кода. По полному принятому snippet извлекаются признаки;
их цели разрешаются непосредственно в индексе и имеют отдельный приоритет
перед общим top-K. Одновременно выполняется не более одного гибридного поиска
по контексту не длиннее 500 символов. Слияние принадлежит `explain_snippet`,
а не меняет публичный ранжировщик `search`.

Такой выбор позволяет расширять локальное окно кода в явно ограниченном
диапазоне, не расширяя текстовый запрос и число поисковых проходов. Настройка
экземпляра, согласованная tool schema и компактный ответ — условия применения
этого решения, подробно определённые в связанном design и контракте.

## Альтернативы и последствия

Обрезать единую строку проще, но это теряет распознанные цели. Располагать их
в начале строки недостаточно: число целей и их суммарная длина могут превысить
бюджет, а текстовое ранжирование всё равно не гарантирует место прямой цели.
Поиск по блокам/по каждому сигналу увеличивает число проходов; увеличение
общего лимита query меняет чужой публичный контракт.

Выбранный вариант явно меняет ранжирование только рекомендаций snippet.
Результат top-K не гарантирует выдачу всех целей, если их больше K, и не
означает доказанного нарушения: распознаватели остаются эвристическими.
Единый runtime, legacy tools, формат ответов и POST-only transport сохраняются.
