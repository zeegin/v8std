---
schema_version: 1
kind: adr
id: LOCAL_OPENMETRICS_EXPOSITION
scope: product
design: design:mcp-openmetrics-generation
requirements:
  - OPENMETRICS_IS_GENERATED_LOCALLY
  - PROMETHEUS_INTEGRATION_IS_DEFERRED
  - METRICS_ENDPOINTS_USE_LOOPBACK
aliases: [ADR-0003]
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:METRICS_ENDPOINTS_ARE_LOOPBACK_ONLY
    - invariant:METRICS_LABEL_CARDINALITY_IS_BOUNDED
  preserves: []
  replaces: {}
  cancels: []
contracts:
  introduces: [contract:MCP_OPENMETRICS@1.0]
  preserves: []
  replaces: {}
  cancels: []
---

# Локальная генерация OpenMetrics

## Входные требования

- `OPENMETRICS_IS_GENERATED_LOCALLY`;
- `PROMETHEUS_INTEGRATION_IS_DEFERRED`;
- `METRICS_ENDPOINTS_USE_LOOPBACK`.

## Решение

Генерировать OpenMetrics внутри MCP v2/v3 и отдавать exposition только через
loopback. Подключение к единому Prometheus вынести в отдельное последующее
решение.

## Влияние на инварианты

Вводятся `METRICS_ENDPOINTS_ARE_LOOPBACK_ONLY` и
`METRICS_LABEL_CARDINALITY_IS_BOUNDED`.

## Влияние на контракты

Вводится `contract:MCP_OPENMETRICS@1.0`; имена метрик, labels и семантика
значений становятся наблюдаемым versioned boundary.

## Отклонённые альтернативы

Немедленная production-интеграция с Prometheus отклонена как отдельный объём.
Публичный `/metrics` отклонён из-за ненужной внешней поверхности доступа.
