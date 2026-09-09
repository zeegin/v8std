---
schema_version: 1
kind: invariant
id: MARKDOWN_RENDERING_PRESERVES_SOURCE_AND_CODE
scope: product
introduced_by: adr:NORMALIZE_FENCES_AT_RENDER_BOUNDARY
requirements:
  - MARKDOWN_RENDERING_PRESERVES_SOURCE_CORPUS
  - MARKDOWN_RENDERING_PRESERVES_CODE_AND_CONTEXT
owner: v8std maintainers
governs:
  - scripts/v8std_markdown.py
  - zensical.toml
  - tests/test_v8std_markdown.py
check:
  module: tests.test_v8std_markdown
  command: .venv/bin/python -m unittest tests.test_v8std_markdown -v
required_when: implemented
---

# Рендеринг сохраняет исходный корпус и код

При одинаковом входном корпусе включение нормализации fenced-блоков не меняет
исходные Markdown-файлы, provenance-маркеры, хеши managed source blocks и
данные каталога источников. Нормализованная копия не становится источником
для Markdown sidecars, AI-артефактов или MCP.

Тело каждого блока кода сохраняется без вставки/удаления строк, изменения
отступов или языка. Поведение существующего подсветчика не меняется:
копируемый код сравнивается с корректно разделённым эквивалентом, а не с
заведомо сломанной HTML-структурой.

Fitness module проверяет эти свойства на фиксированных fixtures и реальном
renderer, включая повторное применение нормализации. Перед выпуском к нему
добавляются существующая `scripts/check_diagnostic_articles.py`, проверка
неизменности исходного корпуса после сборки и браузерное копирование кода.
Декларация будущего модуля не является свидетельством готового исправления.
