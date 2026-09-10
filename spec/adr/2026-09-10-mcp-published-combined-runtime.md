---
schema_version: 1
kind: adr
id: MCP_PUBLISHED_COMBINED_RUNTIME
scope: product
design: design:mcp-container-distribution
requirements:
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_COMBINED_PAGE_READING_COMPATIBLE
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
  - MCP_DISTRIBUTION_PROVENANCE_IS_VERIFIABLE
aliases: []
supersedes:
  - adr:MCP_COMBINED_ENDPOINT
cancels: []
invariants:
  introduces:
    - invariant:MCP_PUBLISHED_RUNTIME_IS_ONE_SERVICE
  preserves:
    - invariant:MCP_LEGACY_ENDPOINT_STABILITY
    - invariant:MCP_RESOURCE_LINKS_ARE_LISTABLE
    - invariant:MCP_SNIPPET_SIGNALS_SURVIVE_TEXT_BUDGET
  replaces:
    invariant:MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME: invariant:MCP_PUBLISHED_RUNTIME_IS_ONE_SERVICE
  cancels: []
contracts:
  introduces:
    - contract:MCP_API@2.4
    - contract:MCP_DISTRIBUTION@1.0
  preserves:
    - contract:MCP_API@2.0
    - contract:MCP_API@2.1
  replaces:
    contract:MCP_API@2.2: contract:MCP_API@2.4
    contract:MCP_API@2.3: contract:MCP_API@2.4
  cancels: []
---

# Один опубликованный runtime для всех способов запуска

## Входные требования

Единый логический MCP-сервис, совместимое чтение страниц, lifecycle кодового
агента и проверяемое происхождение артефакта.

## Решение

Один multi-platform runtime image запускается в stdio либо HTTP-режиме.
Production, локальный запуск и каталог используют его опубликованный digest,
не отдельный Docker-built fork и не docs-builder. Steady state production —
один активный runtime; максимум два однотипных экземпляра при переключении,
без самостоятельного v3 endpoint. Внешняя граница остаётся `/mcp`.

Единство image/API не требует одинаковой конфигурации launchers. Production
и наши direct Docker/Compose сохраняют строгий профиль read-only/cap-drop;
Gateway использует документированный нативный профиль из distribution contract.
Этот согласованный выбор не создаёт fork, не откладывает Catalog лишь из-за
отсутствующих флагов и не разрешает privileged MCP либо Docker socket внутри него.

## Влияние на инварианты

Буквальная привязка к одному Python-процессу и старому systemd unit заменена
инвариантом одного сервиса из опубликованного образа. Legacy API, разрешимость
Resource links и работа snippet-сигналов сохранены. Исторические ссылки на
single-runtime invariant не означают запрета ограниченного overlap при rollout.

## Влияние на контракты

API 2.4 наследует 2.3, не меняет tool arguments/result shapes и дополняет
транспорты и lifecycle. Distribution 1.0 задаёт наблюдаемый интерфейс образа.
Ссылки на 2.0/2.1 сохраняют историческую совместимость, а не второй действующий
runtime. Ранее отклонённый API 3.0 не возобновляется.

## Отклонённые альтернативы

- Раздельные production/local/catalog образы: разные пути выпуска и проверки.
- Отдельный сервис v3: отсутствует необходимость в изоляции пользователей v3.
- Остановка старого до проверки нового в обычном автоматическом rollout.
  Для первой ручной миграции пользователь отдельно разрешил резервное окно
  с простоем; правила возврата определены release contract.
- Snapshot внутри runtime image: связывает выпуск статей с рестартом сервера.
