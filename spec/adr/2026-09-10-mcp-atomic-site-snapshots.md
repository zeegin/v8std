---
schema_version: 1
kind: adr
id: MCP_ATOMIC_SITE_SNAPSHOTS
scope: product
design: design:mcp-container-distribution
requirements:
  - MCP_RUNTIME_AND_CORPUS_RELEASE_INDEPENDENTLY
  - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
  - MCP_SNAPSHOT_LOAD_IS_ATOMIC
  - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
  - MCP_SNAPSHOT_IO_IS_BOUNDED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
  - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
  - MCP_OFFLINE_USES_VERIFIED_CACHE
aliases: []
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
    - invariant:MCP_SITE_OVERRIDE_HAS_NO_PUBLIC_FALLBACK
  preserves: []
  replaces: {}
  cancels: []
contracts:
  introduces:
    - contract:MCP_CORPUS_SNAPSHOT@1.0
  preserves:
    - contract:MCP_API@2.4
  replaces: {}
  cancels: []
---

# Атомарные snapshots от выбранного сайта

## Входные требования

Независимый выпуск данных, единственная настройка источника и адресов,
ограниченный background I/O, целостность поколения и локальная автономность.

## Решение

Выбранный сайт публикует manifest одного неизменяемого snapshot. Runtime
скачивает, проверяет и подготавливает его вне request path; одним коротким
переключением ссылки активирует готовый immutable index. Каждый запрос
удерживает свою ссылку до завершения. Cache разделён по нормализованному сайту
и schema; активная и предыдущая копии сохраняются для offline/recovery.

Публичный manifest явно ссылается на nginx `ai.v8std.ru/indexes/`, локальный —
на файл своего сайта. Второй source/base URL не вводится. Доставка файлов
отделена от вычислительного MCP, но не является вторым MCP-сервисом.

## Влияние на инварианты

Вводятся полнота active snapshot и запрет скрытого public fallback при site
override. Последняя рабочая копия важнее свежести: transient source failure
не делает готовый runtime неготовым. Смена источника не наследует чужой cache.

## Влияние на контракты

Snapshot 1.0 определяет manifest/archive, URL trust boundary, hash и resource
budgets. API 2.4 использует одно поколение для поиска и чтения, сохраняя текущий
surface; неподготовленный instance сообщает явную неготовность.

## Отклонённые альтернативы

- Обход сайта или скачивание данных при каждом tool call.
- Независимые mutable pages/vectors с записью в рабочий cache до проверки.
- Второй environment variable для ссылок или неявный fallback на v8std.ru.
- Python endpoint для статических индексов: связывает доступность с runtime.
- Обязательное скачивание corpus при каждом старте агента без persistent cache.
