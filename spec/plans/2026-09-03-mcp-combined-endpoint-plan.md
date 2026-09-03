---
schema_version: 1
kind: plan
id: mcp-combined-endpoint
design: design:mcp-combined-endpoint
implements:
  - design:mcp-combined-endpoint
  - adr:MCP_COMBINED_ENDPOINT
  - invariant:MCP_COMBINED_ENDPOINT_IS_SINGLE_RUNTIME
  - contract:MCP_API@2.2
---

# Plan: combined MCP endpoint

**Goal:** retire the unused v3 endpoint/process split and make the existing
`/mcp` runtime the sole home for legacy tools and future additive Resources.

**Constraint:** do not claim the full resource catalog is implemented; this
plan changes the boundary and metadata only. Resource catalog functionality
requires a later vertical implementation slice.

- [x] Write the combined endpoint successor design, ADR, invariant, contract,
  and this plan.
- [x] Keep the existing v2 server/service/deployment as the only runtime and
  expose an additive capability profile without removing `v8std_get_page`.
- [x] Add regression tests proving there is no `/v3/mcp` route or v3 service and
  that the combined runtime metadata is explicit.
- [x] Run impact, merge-ready validation, declared fitness checks, full tests,
  diff check, and strict documentation build.
