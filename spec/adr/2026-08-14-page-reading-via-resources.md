---
schema_version: 1
kind: adr
id: PAGE_READING_VIA_RESOURCES
scope: product
design: design:mcp-v3-resource-contract
requirements:
  - MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES
  - MCP_RESOURCE_VERSION_HAS_ONE_PRIMARY_PAGE_READER
aliases: [ADR-0004]
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MCP_RESOURCE_VERSION_PAGE_READING_VIA_RESOURCES
    - invariant:MCP_RESOURCE_LINKS_ARE_LISTABLE
  preserves: []
  replaces: {}
  cancels: []
contracts:
  introduces: []
  preserves: [contract:MCP_API@3.0]
  replaces: {}
  cancels: []
---

# Чтение страниц MCP v3 через Resources

## Входные требования

- `MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES`;
- `MCP_RESOURCE_VERSION_HAS_ONE_PRIMARY_PAGE_READER`.

## Решение

В MCP v3 читать страницы через `resources/list` и `resources/read`.
`v8std_get_page` не включать в v3, чтобы не поддерживать два равноправных
механизма чтения одного содержания.

## Влияние на инварианты

Вводятся `MCP_RESOURCE_VERSION_PAGE_READING_VIA_RESOURCES` и
`MCP_RESOURCE_LINKS_ARE_LISTABLE`.

## Влияние на контракты

Решение конкретизирует и сохраняет `contract:MCP_API@3.0`: page content,
pagination, cursor и resource links описываются в этом контракте.

## Отклонённые альтернативы

Сохранение `v8std_get_page` рядом с Resources отклонено из-за дублирования
семантики. Перевод MCP v2 на Resources не входит в решение.
