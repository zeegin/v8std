# Incident: intermittent MCP nginx 500, 2026-09-09

## Initial evidence (UTC)

- At 17:54 health and initialize both returned 200 publicly and directly.
- Access log contained 15,691 HTTP 500 responses today, from 06:17:39 to
  15:23:55. Error log contained 19,730 connection-exhaustion alerts today.
- Error: `768 worker_connections are not enough while connecting to upstream`.
- Host: 1 vCPU, 961 MiB RAM, 344 MiB available; disk 23% used.
- Python PID 718 has run since July 10; health reports 1,423 pages / 3,281 vectors.
- Active nginx worker PID 485410 held 730 FDs (limit 1024); two shutting-down
  workers and two masters remained after the August 21 binary upgrade.
- systemd MainPID=444817, `/run/nginx.pid`=444841, `.oldbin` PID file present.
- Existing nginx config still had 768 connections, no shutdown deadline,
  and 3600-second proxy idle timeout. SSE heartbeat traffic can keep such a
  stream open indefinitely. The earlier local fixes had not been deployed.
- Total established TCP sockets: 1,133. Python had 384 FDs. These are connection
  observations, not unique agent counts.

## Emergency action and authority

User explicitly requested emergency investigation and production repair, with
broader architecture discussion afterwards. Apply the already approved
POST-only SSE policy at nginx and restore a clean nginx process tree.
No application release, Resource removal, topology expansion or website push
is part of this emergency action.

The reviewed patch changes nginx's main-context worker FD limit to 8192,
worker connection slots to 4096, and worker shutdown deadline to 30 seconds.
The ai.v8std.ru vhost rejects GET offering text/event-stream with 405 and
Allow, uses 30-second client keepalive, and labels its existing rate limiter
429 with Retry-After. Existing rate, TLS, monitoring, upstream and other
vhost configuration are preserved. This is not a 100k-capacity claim.

## Application procedure

1. Save exact nginx.conf, ai.v8std.ru vhost, service/PID state and logs in a
   private timestamped incident directory on the host.
2. Check the exact patch with `patch --dry-run`; install the HTTP map and
   apply only the two reviewed configuration hunks.
3. Run `nginx -t`. Restore saved files if validation fails; leave active
   workers untouched on this path.
4. Restart nginx once to clear old binary generations and stale SSE sockets.
   This briefly reconnects clients of the shared nginx host.
5. Verify public initialize, tools/list, search, page retrieval, health,
   browser GET, HEAD, SSE 405, monitoring and the other vhost; inspect fresh
   errors, FDs and process tree. Confirm reload leaves no stale workers.

## Rollback

Restore the two backed-up configuration files and remove only the newly added
HTTP map from the include directory (move it into the incident backup).
Run `nginx -t` before restarting. Rollback reinstates the known connection
exhaustion risk and is only for a regression of this hotfix.

## Follow-up discussion

- Earlier deployment examples require correction before use:
  worker_rlimit_nofile belongs in main, not http; limit_conn counts active
  requests after headers, not all idle TCP connections. String assertions
  did not validate nginx syntax or prove a 40k-socket admission ceiling.
- Live payload/byte budgets, sync tool/refresh work, MCP FD limits, and retry
  storms need separate measurements. Successful health alone is insufficient.
- Resource removal is an API change and not established as this incident's
  cause. Keep it for the planned tools-only release discussion.
- Separate 403 errors show an unapproved browser-extension Origin; do not
  weaken Origin validation as an outage workaround.
- Design acceptance, local merge and deployment are distinct; require a
  deployed SHA/config checksum and post-deploy behavior proof in release reports.

References: [nginx core directives](https://nginx.org/en/docs/ngx_core_module.html),
[limit_conn semantics](https://nginx.org/en/docs/http/ngx_http_limit_conn_module.html),
[MCP GET SSE transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).
