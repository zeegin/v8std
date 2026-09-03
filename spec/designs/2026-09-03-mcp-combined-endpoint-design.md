---
schema_version: 1
kind: design
id: mcp-combined-endpoint
scope: product
requirements:
  introduces:
    - MCP_COMBINED_ENDPOINT_CAPABILITIES
    - MCP_COMBINED_PAGE_READING_COMPATIBLE
  uses:
    - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
    - MCP_POST_ONLY_AGENT_TRANSPORT
    - MCP_EDGE_CONNECTION_CAPACITY
    - MCP_AGENT_REQUESTS_SCALE_HORIZONTALLY
    - MCP_OVERLOAD_RETURNS_RETRYABLE_STATUS
    - MCP_WORKER_DRAIN_IS_BOUNDED
    - MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES
    - MCP_RESOURCE_CATALOG_IS_PAGINATED
    - MCP_RESOURCE_LIST_USES_STABLE_SNAPSHOTS
    - MCP_RESOURCE_NOTIFICATIONS_ARE_OMITTED
    - MCP_RESOURCE_LINKS_RESOLVE_TO_LISTED_RESOURCES
    - MCP_RESOURCES_EXCLUDE_SUPPORT_PAGES
    - MCP_TEMPLATES_EXCLUDE_LANGUAGE_AND_METHOD_SOURCES
  replaces:
    MCP_VERSIONS_FAIL_INDEPENDENTLY: MCP_COMBINED_ENDPOINT_CAPABILITIES
    MCP_RESOURCE_VERSION_HAS_ONE_PRIMARY_PAGE_READER: MCP_COMBINED_PAGE_READING_COMPATIBLE
  cancels: []
decisions:
  - adr:MCP_COMBINED_ENDPOINT
invariants:
  - invariant:MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME
contracts:
  - contract:MCP_API@2.2
supersedes:
  - design:mcp-v3-resource-contract
  - design:mcp-100k-agent-capacity
cancels: []
---

# Combined MCP endpoint

## Требования

### MCP_COMBINED_ENDPOINT_CAPABILITIES

MCP v2 tools and the future resource-first capability profile are served by one
public `/mcp` endpoint and one horizontally scalable runtime. There is no
`/v3/mcp`, second MCP process, second systemd unit, or version-specific failure
domain.

### MCP_COMBINED_PAGE_READING_COMPATIBLE

The existing `v8std_get_page` tool remains available to v2 clients. Resources
are an additive page-reading surface for clients that support them; they do not
replace or hide the legacy tool. The server must not branch the tool catalog by
an application-version guess made from client metadata.

## Решение

The repository currently contains a working v2 server and only design-only v3
artifacts. The v3 endpoint/process split is therefore retired before any v3
runtime is built. Future resource catalog, templates, `resources/list`, and
`resources/read` functionality is added to `build_server()` in
`scripts/v8std_mcp_server.py` and deployed through the existing
`v8std-mcp.service`.

The single endpoint exposes a superset capability surface: legacy tools remain
stable, while MCP `Resources` are advertised and used by capable clients. MCP
capabilities, not `clientInfo`, User-Agent, or a guessed application version,
determine which operation a client uses.

The capacity and POST-only connection policy from
`design:mcp-100k-agent-capacity` applies to this combined runtime without a
second listener or upstream pool.

## Почему это не «v2 и v3 на одном endpoint с negotiation»

MCP protocol negotiation is not an application API-version selector. A single
endpoint must therefore publish one stable tool catalog. Calling the additive
Resources profile `MCP_API@3.0` while removing `v8std_get_page` would make the
same endpoint incompatible with existing clients. The combined contract keeps
the legacy tool and treats Resources as an additive capability instead.

## Не входит в эту реализацию

The full resource catalog implementation remains a separate vertical slice:
URI policy, stable snapshots, pagination, templates, links, and page-content
limits must be implemented and tested before the additive profile is advertised
as complete. This decision changes its runtime boundary now; it does not claim
that the unimplemented v3 resource catalog already exists.

## Отклонённые альтернативы

- separate `/v3/mcp` process and systemd unit;
- remove `v8std_get_page` from the shared endpoint;
- select application API versions from `clientInfo` or User-Agent;
- run two FastMCP servers behind one nginx location without a single combined
  capability contract.
