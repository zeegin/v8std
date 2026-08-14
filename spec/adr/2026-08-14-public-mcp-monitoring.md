---
schema_version: 1
kind: adr
id: PUBLIC_MCP_MONITORING
scope: product
design: design:mcp-monitoring-dashboard
requirements:
  - MONITORING_SHOWS_AGENT_FAMILIES
  - MONITORING_SHOWS_API_VERSIONS
  - MONITORING_SHOWS_MCP_OPERATIONS
  - PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA
  - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
  - MONITORING_REMAINS_PUBLIC
aliases: [ADR-0002]
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA
    - invariant:OPERATOR_DATA_STAYS_OUTSIDE_WEB_ROOT
  preserves: []
  replaces: {}
  cancels: []
contracts:
  introduces:
    - contract:MCP_USAGE_EVENTS@2.0
    - contract:MCP_MONITORING_PROJECTION@2.0
  preserves:
    - contract:MCP_USAGE_EVENTS@1.0
    - contract:MCP_MONITORING_PROJECTION@1.0
  replaces: {}
  cancels: []
---

# Публичный агрегированный мониторинг MCP

## Входные требования

- `MONITORING_SHOWS_AGENT_FAMILIES`;
- `MONITORING_SHOWS_API_VERSIONS`;
- `MONITORING_SHOWS_MCP_OPERATIONS`;
- `PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA`;
- `OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT`;
- `MONITORING_REMAINS_PUBLIC`.

## Решение

Оставить `/monitoring/` публичной безопасной агрегированной проекцией. Детальные
операторские данные хранить вне web root и получать через SSH, без добавления
аутентификации к публичной странице.

## Влияние на инварианты

Вводятся `PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA` и
`OPERATOR_DATA_STAYS_OUTSIDE_WEB_ROOT`. Публикация сырого события нарушает
решение независимо от удобства dashboard.

## Влияние на контракты

Legacy contracts `MCP_USAGE_EVENTS@1.0` и `MCP_MONITORING_PROJECTION@1.0`
сохраняются для чтения истории. Новые события и проекции оформляются версиями
`2.0`.

## Отклонённые альтернативы

Полное закрытие страницы аутентификацией отклонено как ненужное. Публикация
детального отчёта отклонена из-за утечки чувствительных и высококардинальных
значений.
