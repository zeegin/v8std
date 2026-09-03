# MCP capacity deployment

The public MCP is a read-only, stateless request service. Coding agents send
JSON-RPC messages with `POST`; the service deliberately rejects unsolicited
`GET` SSE streams with HTTP 405. This keeps agent connections at the edge and
prevents one idle stream from consuming one Python and one nginx connection.

There is one combined runtime and one public `/mcp` endpoint. Do not add a
`/v3/mcp` listener or a second systemd service when the Resources profile grows.

The nginx fragments in `deploy/nginx/` reject the optional event-stream GET at
the edge before opening an upstream connection and are intended for every edge node. The
capacity example assumes four or more edge nodes, each admitting at most
40,000 client connections, so that one node can fail without reducing the
100,000-connection target below capacity. Backends remain stateless and are
scaled from measured POST RPS rather than from client connection count.

Before activation:

1. Set `LimitNOFILE` for nginx and the MCP service, and verify the effective
   limits after restart.
2. Set `worker_processes auto`, `worker_connections 65536`, and
   `worker_shutdown_timeout 30s` on each edge node.
3. Deploy the MCP application and verify `GET /mcp` with an event-stream
   Accept header returns 405 while JSON-RPC POST initialize returns 200.
4. Drain the old nginx generations. A graceful drain must be bounded by the
   30-second worker shutdown timeout.
5. Run the 100,000-agent load profile before claiming capacity. The profile
   must include initialize, tools/list, realistic tool bursts, reload, and one
   edge-node failure.

The current service has no trusted client identity. Do not use
`clientInfo.name`, User-Agent, or IP as authentication. Add tenant/API-key
quotas before offering guaranteed per-customer capacity; IP rate limiting is
only an overload guard because many coding agents can share one NAT address.
