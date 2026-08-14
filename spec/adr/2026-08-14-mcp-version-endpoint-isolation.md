---
schema_version: 1
kind: adr
id: MCP_VERSION_ENDPOINT_ISOLATION
scope: product
design: design:mcp-v3-resource-contract
requirements:
  - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
  - MCP_VERSIONS_FAIL_INDEPENDENTLY
aliases: [ADR-0001]
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MCP_VERSION_ISOLATION
    - invariant:MCP_LEGACY_ENDPOINT_STABILITY
  preserves: []
  replaces: {}
  cancels: []
contracts:
  introduces: [contract:MCP_API@3.0]
  preserves: [contract:MCP_API@2.0]
  replaces: {}
  cancels: []
---

# Изоляция endpoint версий MCP

## Входные требования

- `MCP_LEGACY_VERSION_REMAINS_COMPATIBLE`;
- `MCP_VERSIONS_FAIL_INDEPENDENTLY`.

## Решение

Разместить MCP v3 на отдельном endpoint `/v3/mcp`. Существующий `/mcp`
продолжает обслуживать MCP v2 без согласования версии внутри одного endpoint.

## Влияние на инварианты

Решение вводит `MCP_VERSION_ISOLATION` и
`MCP_LEGACY_ENDPOINT_STABILITY`. Смешанная маршрутизация версий опровергает
решение.

## Влияние на контракты

`contract:MCP_API@2.0` сохраняется, а breaking-контракт
`contract:MCP_API@3.0` вводится независимо.

## Отклонённые альтернативы

Изменение `/mcp` на месте и version negotiation отклонены: они связывают
release, отказ и rollback новой версии с действующими клиентами.
