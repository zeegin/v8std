---
schema_version: 1
kind: adr
id: RETIRE_PUBLIC_MCP_MONITORING
scope: product
design: design:mcp-public-monitoring-retirement
requirements:
  - PUBLIC_MONITORING_IS_RETIRED
  - PRIVATE_USAGE_HISTORY_IS_PRESERVED
  - MONITORING_RETIREMENT_PRESERVES_MCP
  - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
aliases: []
supersedes: [adr:PUBLIC_MCP_MONITORING]
cancels: [adr:MCP_PRIVATE_CONTAINER_MONITOR_INPUT]
invariants:
  introduces:
    - invariant:PUBLIC_MONITORING_ROUTES_ARE_GONE
    - invariant:PRIVATE_OPERATIONAL_DATA_IS_NOT_PUBLISHED
  preserves: [invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR]
  replaces:
    invariant:PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA: invariant:PUBLIC_MONITORING_ROUTES_ARE_GONE
    invariant:OPERATOR_DATA_STAYS_OUTSIDE_WEB_ROOT: invariant:PRIVATE_OPERATIONAL_DATA_IS_NOT_PUBLISHED
  cancels: [invariant:MCP_MONITOR_STATE_TRUST_IS_BOUNDED]
contracts:
  introduces:
    - contract:MCP_MONITORING_PROJECTION@3.0
    - contract:MCP_USAGE_EVENTS@1.1
  preserves: [contract:MCP_RELEASE_RUNTIME@1.0]
  replaces:
    contract:MCP_MONITORING_PROJECTION@1.0: contract:MCP_MONITORING_PROJECTION@3.0
    contract:MCP_MONITORING_PROJECTION@2.0: contract:MCP_MONITORING_PROJECTION@3.0
    contract:MCP_USAGE_EVENTS@1.0: contract:MCP_USAGE_EVENTS@1.1
  cancels:
    - contract:MCP_USAGE_EVENTS@2.0
    - contract:MCP_CONTAINER_MONITOR_INPUT@1.0
---

# Прекратить публичную публикацию мониторинга

## Входные требования

Основание — согласованное удаление публичной проекции при сохранении private
usage history, закрытой границы операционных данных и работающего MCP.

## Решение

Пользователь отменил публичный dashboard целиком. Останавливаем и маскируем
его job, удаляем publication code и alias, оставляем HTTP410 tombstones.
Root-only архив обеспечивает восстановимость без сохранения публичного доступа.
Ни аутентифицированный dashboard, ни новый sampler взамен не создаются.

## Влияние на инварианты

Безопасность публичных агрегатов заменена отсутствием публичной выдачи.
Закрытость операторских данных сохраняется без зависимости от renderer.
Доверенная сводка monitor-state отменена; recoverable predecessor остаётся.

## Влияние на контракты

Legacy и future projection заменены breaking HTTP410 boundary. Совместимая
ревизия legacy usage events сохраняет текущий writer для оператора.
Dashboard-specific future events и monitor-input больше не реализуются.
Существующие private logs, их формат/rotation и MCP readiness остаются.
Ненужное сохранение public projection исключается из container release;
постоянство закрытых usage events нового runtime остаётся release-обязательством.
Локальные OpenMetrics — независимое от этого решения принятое намерение.

## Отклонённые альтернативы

Скрытие ссылки, noindex, удаление только HTML либо пароль перед старым
генератором оставляют ненужную цепочку публикации и противоречат полному
удалению. Безвозвратное уничтожение истории не требуется: архив закрыт.
