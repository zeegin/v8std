---
schema_version: 1
kind: contract
id: MCP_API
scope: product
version: 3
revision: 0
compatibility: breaking
design: design:mcp-v3-resource-contract
producer: future MCP v3 /v3/mcp
consumers:
  - resource-capable MCP clients
requirements:
  - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
  - MCP_VERSIONS_FAIL_INDEPENDENTLY
  - MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES
  - MCP_RESOURCE_VERSION_HAS_ONE_PRIMARY_PAGE_READER
  - MCP_RESOURCE_CATALOG_IS_PAGINATED
  - MCP_RESOURCE_LIST_USES_STABLE_SNAPSHOTS
  - MCP_RESOURCE_NOTIFICATIONS_ARE_OMITTED
  - MCP_RESOURCE_LINKS_RESOLVE_TO_LISTED_RESOURCES
  - MCP_RESOURCES_EXCLUDE_SUPPORT_PAGES
  - MCP_TEMPLATES_EXCLUDE_LANGUAGE_AND_METHOD_SOURCES
governs:
  - scripts/v8std_mcp_v3.py
  - scripts/v8std_mcp_resources.py
conformance:
  module: tests.test_v8std_mcp_v3
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_v3 -v
required_when: implemented
supersedes: []
deprecates: []
---

# MCP API v3.0

## Endpoint и tools

Streamable HTTP endpoint `/v3/mcp` запускается отдельно от `/mcp`. Он
предоставляет `v8std_search`, `v8std_get_related`, `v8std_explain_snippet` и
`v8std_explain_diagnostics`; `v8std_get_page` отсутствует. Page content
читается только через Resources.

## URI и templates

URI используют префикс `v8std://ru/`. Templates существуют только для:

```text
v8std://ru/standards/{number}
v8std://ru/diagnostics/{family}/{code}
v8std://ru/patterns/{family}
v8std://ru/patterns/{family}/{slug}
```

`lang` и конкретные страницы `metod8dev` могут быть listable Resources, но не
templates. Страницы `mcp`, `search_help` и `support` отсутствуют в list/read,
не имеют `resource_uri` и не возвращаются как resource links. Универсальный
`v8std://page/{id}` запрещён.

## List, snapshot и cursor

`resources/list` возвращает не более 200 дескрипторов, отсортированных по URI.
Первый запрос фиксирует immutable snapshot и revision, вычисленную из версии
resource schema, SHA индекса и visibility policy. Opaque Base64URL cursor
содержит только версию формата, revision и offset. Он продолжает тот же
snapshot; неверный, устаревший или относящийся к другому revision cursor
возвращает protocol error, а не начинает список заново.

Refresh создаёт новый snapshot только для нового list. Уже выданные cursors
остаются привязаны к прежнему snapshot в пределах установленного срока жизни.
Resource list-change notifications и subscriptions не объявляются.

## Read и resource links

`resources/read` принимает только canonical URI видимой страницы, возвращает
полный Markdown с `mimeType: text/markdown; charset=utf-8` и не читает support
pages. Каждый `resource_link` из tool result ссылается на URI, присутствующий в
listable snapshot и разрешимый тем же read contract.

## Совместимость

Версия 3 breaking относительно v2 из-за удаления page tool и смены resource
model, но не заменяет `MCP_API@2.0`: версии живут на разных endpoint.
