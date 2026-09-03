---
schema_version: 1
kind: design
id: mcp-100k-agent-capacity
scope: product
requirements:
  introduces:
    - MCP_POST_ONLY_AGENT_TRANSPORT
    - MCP_EDGE_CONNECTION_CAPACITY
    - MCP_AGENT_REQUESTS_SCALE_HORIZONTALLY
    - MCP_OVERLOAD_RETURNS_RETRYABLE_STATUS
    - MCP_WORKER_DRAIN_IS_BOUNDED
  uses:
    - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
    - MCP_VERSIONS_FAIL_INDEPENDENTLY
  replaces: {}
  cancels: []
decisions:
  - adr:MCP_POST_ONLY_EDGE_DRAIN
invariants:
  - invariant:MCP_POST_ONLY_TRANSPORT
  - invariant:MCP_EDGE_DRAIN_IS_BOUNDED
  - invariant:MCP_OVERLOAD_IS_RETRYABLE
contracts:
  - contract:MCP_API@2.1
supersedes: []
cancels: []
---

# Capacity design for 100,000 coding-agent connections

## Scope and capacity envelope

The target is 100,000 simultaneously connected coding agents, not an
unstated 100,000 requests per second. The initial measurable envelope is:

- 100,000 client connections at the edge;
- 10,000 MCP POST requests per second at peak;
- 20,000 requests per second for a 30-second burst;
- p95 ordinary tool response below 500 ms and p99 below 1 second;
- one edge node may fail without losing service;
- reload and drain do not produce nginx 500 responses or leave workers alive
  indefinitely.

The POST-RPS and latency figures are sizing assumptions. The implementation
must replace them with measured per-replica capacity before production capacity
is claimed.

## Требования

### MCP_POST_ONLY_AGENT_TRANSPORT

The stateless v2 endpoint serves coding-agent JSON-RPC through POST. An
unsolicited event-stream GET returns 405, so idle agents do not hold an MCP
SSE stream.

### MCP_EDGE_CONNECTION_CAPACITY

The deployment has enough independent edge capacity for 100,000 simultaneous
client connections with one edge node unavailable.

### MCP_AGENT_REQUESTS_SCALE_HORIZONTALLY

MCP request processing is stateless and can scale by adding replicas without
session affinity or shared client state.

### MCP_OVERLOAD_RETURNS_RETRYABLE_STATUS

Admission and backend capacity failures are exposed as retryable 429 or 503
responses with retry guidance, not as generic nginx 500 responses.

### MCP_WORKER_DRAIN_IS_BOUNDED

Edge worker shutdown and service termination have explicit finite deadlines so
long-lived connections cannot retain obsolete workers indefinitely.

## Decisions

### POST-only MCP request path

The service is read-only and uses `stateless_http=True`, `json_response=True`.
It does not send unsolicited server-to-client messages. Therefore an
unsolicited Streamable HTTP GET SSE stream has no product value and is the
wrong resource boundary for a large agent fleet.

`POST /mcp` remains the canonical path. `GET /mcp` with
`text/event-stream` is answered with `405 Method Not Allowed` and
`Allow: POST, HEAD`. Plain browser GET and HEAD self-documentation remain
available. This is compatible with the Streamable HTTP transport, which allows
the server to return 405 when it does not offer an SSE stream.

### Edge connection plane

The edge terminates TLS and owns client connection capacity. Four or more edge
nodes provide N+1 capacity; each node is sized for 40,000 client connections,
leaving 120,000 capacity after one node fails. The edge uses event-driven
workers, a 65,536 connection limit per worker, a 131,072 file-descriptor
limit, 30-second client keepalive, and a 30-second worker shutdown timeout.

The edge uses a bounded upstream keepalive pool. It does not maintain one
upstream socket for every idle agent. `proxy_read_timeout` is 35 seconds for
request-scoped POST operations; it is not used as the primary control for SSE.
Each edge server admits at most 40,000 MCP connections; four nodes therefore
retain 120,000 admission capacity after one node fails.

### Stateless request plane

MCP replicas share no client session state and require no session affinity.
Replica count is calculated from measured POST capacity:

```text
ceil(peak_post_rps / measured_replica_rps * 1.5)
```

The index is an immutable, versioned snapshot loaded by each replica. Large
static AI artifacts are served from CDN/object storage where possible. Search
and tool calls remain bounded, read-only operations.

### Overload and identity

The edge returns 429 for request-rate admission failures; connection admission
and unavailable backend capacity return 503 with `Retry-After`. Upstream 502/504
failures are normalized to 503 at this boundary. Neither overload condition is
represented as an nginx-generated 500. Coding agents must use exponential
backoff with jitter for retryable failures.

The current public endpoint has no trusted identity. User-Agent, clientInfo,
and IP are not authentication. IP limits are only a coarse emergency guard;
tenant/API-key quotas are required for guaranteed customer-specific capacity,
because multiple agents commonly share a NAT address.

## Agent lifecycle

Agents initialize once per process and then issue short POST requests for
tools. A client may attempt the optional GET stream, but receives a definitive
405 and must continue with POST. There is no automatic GET reconnect loop to
recreate the exhausted connection pool. A deploy drain closes only existing
legacy streams; active POST requests are allowed to finish within the request
deadline.

## Failure handling

The old single-host configuration is not a 100,000-connection production
topology. It has one edge node, one Python process, and a low file-descriptor
limit. The new deployment fragments are reproducible examples, not proof of
capacity. Proof requires a load test with realistic Codex/Claude Code/Cursor
request sequences, 100,000 open edge connections, request bursts, graceful
reload, one node failure, and verification that no 500 is caused by connection
exhaustion.

## Rejected alternatives

- Raising `worker_connections` alone: it postpones exhaustion while leaving
  unbounded SSE streams and stale workers in place.
- A hard per-IP connection quota as the main policy: coding agents share NAT
  addresses and would be unfairly rejected.
- Keeping one backend socket per agent: it duplicates the edge connection
  plane and makes horizontal scaling proportional to idle clients.
- Requiring clientInfo or User-Agent for authorization: both are untrusted and
  spoofable.
