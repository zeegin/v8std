---
schema_version: 1
kind: adr
id: MCP_POST_ONLY_EDGE_DRAIN
scope: product
design: design:mcp-100k-agent-capacity
requirements:
  - MCP_POST_ONLY_AGENT_TRANSPORT
  - MCP_EDGE_CONNECTION_CAPACITY
  - MCP_WORKER_DRAIN_IS_BOUNDED
aliases: []
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MCP_POST_ONLY_TRANSPORT
    - invariant:MCP_EDGE_DRAIN_IS_BOUNDED
    - invariant:MCP_OVERLOAD_IS_RETRYABLE
  preserves:
    - invariant:MCP_LEGACY_ENDPOINT_STABILITY
  replaces: {}
  cancels: []
contracts:
  introduces:
    - contract:MCP_API@2.1
  preserves:
    - contract:MCP_API@2.0
  replaces: {}
  cancels: []
---

# POST-only MCP edge and bounded drain

## Входные требования

- `MCP_POST_ONLY_AGENT_TRANSPORT`;
- `MCP_EDGE_CONNECTION_CAPACITY`;
- `MCP_WORKER_DRAIN_IS_BOUNDED`.

## Решение

The read-only stateless MCP service does not need unsolicited server-to-client
messages. The canonical client operation is therefore request-scoped POST.
The optional GET SSE stream is rejected with 405, while tools, resources,
initialize, browser documentation, and health/version routes remain available.

Connection capacity belongs to a horizontally scaled edge fleet. Backend
replicas are stateless and are reached through bounded upstream pools. Nginx
workers have an explicit shutdown deadline so a reload cannot leave old SSE
workers consuming capacity for days.

## Влияние на инварианты

The decision introduces bounded POST-only transport and edge drain invariants,
and preserves the existing v2 endpoint tool and POST behavior.

## Влияние на контракты

This preserves the v2 tool and POST contract; the transport clarification is a
backward-compatible revision because Streamable HTTP permits a server without
an unsolicited GET SSE stream.

## Отклонённые альтернативы

- raising `worker_connections` without removing unbounded SSE streams;
- using a hard per-IP quota as the primary fairness mechanism;
- keeping one upstream socket per idle coding agent.
