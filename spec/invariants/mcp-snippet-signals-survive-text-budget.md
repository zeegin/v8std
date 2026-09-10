---
schema_version: 1
kind: invariant
id: MCP_SNIPPET_SIGNALS_SURVIVE_TEXT_BUDGET
scope: product
introduced_by: adr:SNIPPET_SIGNALS_OUTSIDE_TEXT_QUERY
requirements:
  - MCP_SNIPPET_ACCEPTED_INPUT_IS_SCANNED
  - MCP_SNIPPET_TARGETS_SURVIVE_QUERY_BUDGET
  - MCP_SNIPPET_RETRIEVAL_WORK_IS_BOUNDED
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_index.py
  - scripts/v8std_retrieval_rules.py
  - tests/test_v8std_mcp_index.py
  - tests/test_v8std_mcp_snippet.py
check:
  module: tests.test_v8std_mcp_snippet
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_snippet -v
required_when: implemented
---

# Сигналы процедуры не теряются из-за бюджета текстового поиска

Принятый snippet полностью поступает в распознавание. Существующая в индексе
первичная цель найденного признака участвует в приоритетном ранжировании
независимо от позиции в snippet и попадания в 500-символьный контекст.
Если K не меньше числа уникальных существующих первичных целей, каждая
присутствует в общем top-K. Если K меньше — применяется определённая design
детерминированная сортировка, без обещания выдать больше K.

Длина кода и количество признаков не увеличивают число вызовов гибридного
поиска выше одного. Повторение одинакового признака не увеличивает его вес.
Fitness включает позиции начала/середины/конца, 4k/32k, конфликт с высоким
текстовым score, повторы и малый K, а не только отсутствие исключений.

Декларация fitness сама по себе не является результатом теста или
свидетельством IMPLEMENTED. Выполненные проверки модуля и остальных gates
зафиксированы в [verification evidence](../operations/2026-09-10-mcp-snippet-verification.md).
