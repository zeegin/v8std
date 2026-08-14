---
schema_version: 1
kind: contract
id: STANDARD_SOURCE_REGISTRY
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:english-standard-sources
producer: data/standard-english-sources.json maintainers
consumers:
  - scripts/standard_sources.py
  - source validation tests
  - documentation and AI artifact generators
requirements:
  - ENGLISH_STANDARD_LINKS_REQUIRE_VERIFICATION
  - RUSSIAN_STANDARD_SOURCE_REMAINS_PRIMARY
  - STANDARD_SOURCE_REGISTRY_IS_DETERMINISTIC
  - STANDARD_SOURCE_VALIDATION_IS_OFFLINE
governs:
  - data/standard-english-sources.json
  - scripts/standard_sources.py
  - docs/std/
conformance:
  module: tests.test_standard_sources
  command: .venv/bin/python -m unittest tests.test_standard_sources -v
required_when: implemented
supersedes: []
deprecates: []
---

# Реестр источников стандартов, версия 1.0

## Наблюдаемая граница

Реестр является отсортированным отображением канонического ID страницы
стандарта в проверенный англоязычный HTTPS URL 1Ci. ID обязан разрешаться в
существующий `docs/std/<id>.md`, а страница обязана сохранять соответствующий
русский ITS URL первым источником.

Одна страница и один URL не могут иметь противоречащие записи. Отсутствие
проверенного английского соответствия допустимо и не создаёт placeholder.
Проверка схемы, уникальности и синхронизации Markdown выполняется офлайн;
повторная запись не изменяет файлы.

## Совместимость

Добавление новой проверенной пары обратно совместимо. Изменение смысла ключа,
разрешение неподтверждённых URL или удаление обязательного русского источника
требует новой major-версии.
