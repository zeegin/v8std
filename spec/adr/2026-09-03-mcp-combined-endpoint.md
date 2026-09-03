---
schema_version: 1
kind: adr
id: MCP_COMBINED_ENDPOINT
scope: product
design: design:mcp-combined-endpoint
requirements:
  - MCP_COMBINED_ENDPOINT_CAPABILITIES
  - MCP_COMBINED_PAGE_READING_COMPATIBLE
aliases: []
supersedes:
  - adr:MCP_VERSION_ENDPOINT_ISOLATION
  - adr:PAGE_READING_VIA_RESOURCES
cancels: []
invariants:
  introduces:
    - invariant:MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME
  preserves:
    - invariant:MCP_LEGACY_ENDPOINT_STABILITY
    - invariant:MCP_RESOURCE_LINKS_ARE_LISTABLE
  replaces:
    invariant:MCP_VERSION_ISOLATION: invariant:MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME
    invariant:MCP_RESOURCE_VERSION_PAGE_READING_VIA_RESOURCES: invariant:MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME
  cancels: []
contracts:
  introduces:
    - contract:MCP_API@2.2
  preserves:
    - contract:MCP_API@2.0
    - contract:MCP_API@2.1
  replaces:
    contract:MCP_API@3.0: contract:MCP_API@2.2
  cancels: []
---

# Один комбинированный MCP runtime

## Входные требования

- `MCP_COMBINED_ENDPOINT_CAPABILITIES`;
- `MCP_COMBINED_PAGE_READING_COMPATIBLE`.

## Решение

Оставить единственный `/mcp` и единственный `v8std-mcp.service`. Текущие v2
tools и будущий additive Resources-профиль регистрируются в одном
`v8std_mcp_server.py`; отдельные `/v3/mcp`, порт и процесс не создаются.

`v8std_get_page` не удаляется. Клиенты с поддержкой Resources получают новый
способ чтения страниц, а старые tool-only клиенты продолжают работать.

## Влияние на инварианты

Решение заменяет изоляцию версий инвариантом единственного runtime и сохраняет
стабильность legacy endpoint. Ошибка или незавершённость будущего Resources
слоя не должна требовать второго публичного сервиса.

## Влияние на контракты

Вводится backward-compatible `MCP_API@2.2`, который сохраняет v2 surface и
добавляет capability profile. Старый design-only `MCP_API@3.0` больше не
рассматривается как отдельный публичный endpoint-контракт.

## Отклонённые альтернативы

- `/v3/mcp` и отдельный процесс;
- breaking removal `v8std_get_page`;
- эвристическое negotiation по имени клиента.
