---
schema_version: 1
kind: contract
id: DIAGNOSTIC_CHIP_MARKUP
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:unified-diagnostic-chips
producer: diagnostic renderers
consumers:
  - site stylesheets
  - diagnostic JavaScript
  - accessibility tools
  - human and machine readers
requirements:
  - DIAGNOSTIC_IDENTIFIERS_USE_SHARED_CHIPS
  - DIAGNOSTIC_CHIPS_ARE_ACCESSIBLE
  - GENERATED_DIAGNOSTIC_CHIPS_ARE_IDEMPOTENT
governs:
  - scripts/diagnostic_standard_links.py
  - docs/assets/
  - docs/diagnostics/
conformance:
  module: tests.test_diagnostics_registry_js
  command: .venv/bin/python -m unittest tests.test_diagnostics_registry_js -v
required_when: implemented
supersedes: []
deprecates: []
---

# Разметка diagnostic chip, версия 1.0

## Наблюдаемая граница

Видимое упоминание идентификатора диагностики оформляется ссылкой с общим
классом `.diagnostic-chip`. Ссылка ведёт на каноническую страницу диагностики,
остаётся доступной с клавиатуры и не зависит от JavaScript для навигации.

Группа обратных ссылок использует семантический контейнер с доступным именем,
но не добавляет отдельный видимый заголовок «Проверки». Генератор распознаёт
уже созданные chip-ссылки и не создаёт вложенную или повторную обёртку.

## Совместимость

Новые необязательные CSS-классы и визуальные уточнения обратно совместимы.
Изменение семантики ссылки, канонического target или обязательного базового
класса требует новой major-версии.
