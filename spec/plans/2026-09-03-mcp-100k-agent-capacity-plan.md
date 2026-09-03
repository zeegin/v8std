---
schema_version: 1
kind: plan
id: mcp-100k-agent-capacity
design: design:mcp-100k-agent-capacity
implements:
  - design:mcp-100k-agent-capacity
  - adr:MCP_POST_ONLY_EDGE_DRAIN
  - invariant:MCP_POST_ONLY_TRANSPORT
  - invariant:MCP_EDGE_DRAIN_IS_BOUNDED
  - invariant:MCP_OVERLOAD_IS_RETRYABLE
  - contract:MCP_API@2.1
---

# MCP capacity implementation plan

**Goal:** remove unbounded idle SSE streams from the stateless v2 path and
publish reproducible edge/service limits suitable for a later 100,000-agent
load proof.

**Constraints:** preserve v2 POST tools and resources; do not deploy the MCP
server; do not claim 100,000 capacity without the declared load test.

- [x] Add the POST-only event-stream response and focused ASGI compatibility tests.
- [x] Add nginx and systemd capacity fragments with bounded worker drain,
  explicit file-descriptor limits, request-scoped upstream timeouts, and 429
  admission status.
- [x] Add configuration/invariant tests for the deployment fragments and
  contract tests for plain GET, event-stream GET, initialize POST, and retryable
  overload policy.
- [x] Run architecture impact and merge-ready validation, the full unittest
  suite, `git diff --check`, and strict documentation build.
- [x] Record the remaining production gate: multi-node load test with 100,000
  synthetic agent connections, realistic coding-agent POST bursts, reload,
  one edge-node failure, and zero connection-exhaustion 500 responses.
