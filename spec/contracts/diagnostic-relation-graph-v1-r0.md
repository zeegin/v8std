---
schema_version: 1
kind: contract
id: DIAGNOSTIC_RELATION_GRAPH
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:diagnostics-by-standard-clause
producer: reviewed relation registries and relationship generator
consumers:
  - standard pages
  - diagnostic pages
  - diagnostic registry
requirements:
  - DIAGNOSTICS_GROUP_BY_STANDARD_CLAUSE
  - EMPTY_DIAGNOSTIC_CLAUSES_ARE_OPT_IN
  - DIAGNOSTIC_REGISTRY_WORKS_WITHOUT_JAVASCRIPT
  - CONFIRMED_DIAGNOSTIC_RELATIONS_ARE_LOSSLESS
  - DIAGNOSTIC_CLAUSE_TEXT_IS_DERIVED
governs:
  - data/diagnostic-standard-links.json
  - scripts/generate_diagnostic_standard_links.py
  - docs/diagnostics/
conformance:
  module: tests.test_diagnostic_standard_links
  command: .venv/bin/python -m unittest tests.test_diagnostic_standard_links -v
required_when: implemented
supersedes: []
deprecates: []
---

# Граф связей диагностик и стандартов, версия 1.0

## Наблюдаемая граница

Реестры подтверждённых связей и генератор формируют один детерминированный
граф. Каждое ребро связывает канонический идентификатор диагностики с
существующей страницей и пунктом стандарта. Прямая проекция используется на
страницах диагностик, обратная — на страницах стандартов и в реестре.

Порядок страниц, пунктов и диагностик стабилен. Краткий текст пункта извлекается
из канонического Markdown. Неизвестная страница, отсутствующий пункт,
противоречащая дублирующая запись или потеря подтверждённого ребра являются
ошибкой генерации, а не поводом молча пропустить данные.

## Совместимость

Добавление нового подтверждённого ребра или необязательного производного поля
обратно совместимо. Переименование ключей, изменение идентичности ребра или
удаление подтверждённой связи требует новой major-версии контракта.
