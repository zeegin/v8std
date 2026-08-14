---
schema_version: 1
kind: invariant
id: MCP_RESOURCE_VERSION_PAGE_READING_VIA_RESOURCES
scope: product
introduced_by: adr:PAGE_READING_VIA_RESOURCES
requirements:
  - MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES
  - MCP_RESOURCE_VERSION_HAS_ONE_PRIMARY_PAGE_READER
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_v3.py
  - scripts/v8std_mcp_resources.py
check:
  module: tests.test_v8std_mcp_v3
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_v3 -v
required_when: implemented
---

# MCP v3 reads pages only through Resources

В MCP v3 page content читается `resources/read`, а отдельный
`v8std_get_page` отсутствует. Второй равноправный page reader или отсутствие
resource reading опровергает `PAGE_READING_VIA_RESOURCES`.
