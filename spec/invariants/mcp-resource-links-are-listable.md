---
schema_version: 1
kind: invariant
id: MCP_RESOURCE_LINKS_ARE_LISTABLE
scope: product
introduced_by: adr:PAGE_READING_VIA_RESOURCES
requirements:
  - MCP_RESOURCE_LINKS_RESOLVE_TO_LISTED_RESOURCES
  - MCP_RESOURCE_CATALOG_IS_PAGINATED
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_v3.py
  - scripts/v8std_mcp_resources.py
check:
  module: tests.test_v8std_mcp_v3
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_v3 -v
required_when: implemented
---

# Resource links belong to the listable catalog

Каждый URI, возвращаемый tool как resource link, присутствует в стабильном
пагинируемом snapshot и читается через `resources/read`. Скрытая или
неразрешимая ссылка опровергает выбранный resource-first contract.
