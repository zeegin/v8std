---
schema_version: 1
kind: adr
id: MCP_PRIVATE_CONTAINER_MONITOR_INPUT
scope: product
design: design:mcp-container-monitor-input
requirements:
  - MCP_MONITOR_STATE_HAS_BOUNDED_FRESHNESS
  - MCP_MONITOR_OBSERVES_SERVING_RUNTIME
  - MCP_MONITOR_RETAINS_UNPRIVILEGED_READER
  - MCP_CONTAINER_USAGE_SURVIVES_RELEASE
aliases: []
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MCP_MONITOR_STATE_TRUST_IS_BOUNDED
  preserves:
    - invariant:OPERATOR_DATA_STAYS_OUTSIDE_WEB_ROOT
    - invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
  replaces: {}
  cancels: []
contracts:
  introduces:
    - contract:MCP_CONTAINER_MONITOR_INPUT@1.0
  preserves:
    - contract:MCP_MONITORING_PROJECTION@1.0
    - contract:MCP_USAGE_EVENTS@1.0
    - contract:MCP_RELEASE_RUNTIME@1.0
  replaces: {}
  cancels: []
---

# Закрытый вход непривилегированного мониторинга

## Входные требования

Основание исходного решения — свежесть наблюдения serving runtime,
непривилегированный reader и сохранение usage history при container release.

## Решение

Root-owned sampler перед существующим batch job собирает действительное
состояние serving runtime и атомарно пишет маленький private JSON. Агрегатор
может только читать его; не получает полномочий Docker или release-controller.
История usage отдельно остаётся persistent private data, а не частью cache.

## Влияние на инварианты

Свежесть, boot identity и проверка serving identity ограничивают доверие к
сводке. Ошибка или переход означает unknown. Квитанция COMMITTED, active
controller и загрузка нового corpus не заменяют процессные наблюдения.

## Влияние на контракты

Решение сохраняет старые readers и public fields. `restarts:null` для container
честно обозначает отсутствие сопоставимого общего счётчика. Private details не
расширяют публичную схему; общий редизайн/privacy-remediation сюда не включены.
Это дополнение к release ADR, не его замена и не изменение release budgets.

## Отклонённые альтернативы

Socket/group у reader отвергнуты из-за избыточной власти; фиксированный sudo RPC
избыточен для чтения batch-сводки; отдельный daemon не требуется. Цена файла —
явное истечение срока доверия и необходимость тестировать invalidation/races.
