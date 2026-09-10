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
   apply only the two reviewed configuration files. The patch uses zero-context
   insertions: first compare live files byte-for-byte with the incident backups;
   do not reuse it against another host or a changed configuration.
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

## Recovery evidence

- Deployed configuration source: local main commit
  `d707daa9b6d487ae4cf9d93d6c34ff86fa6b5793`. Only the emergency nginx patch
  and map were applied. No Git push or application update occurred.
- Backup/evidence was retained in a root-only directory; its location is
  recorded privately.
- At 17:59:50, exact patch dry-run and host nginx 1.24.0 `nginx -t` passed.
  An existing OCSP warning unrelated to MCP remained.
- Restart began at 17:59:58 and completed at 18:00:08 UTC (21:00:08 MSK).
  systemd MainPID and nginx pid-file both became 643435. Two workers stuck in
  shutdown and the obsolete master were cleared by the unit restart.
- Established TCP connections dropped from 1,133 to 6 immediately, then 41
  after 33 seconds of live reconnects. Python FDs dropped from 384 to 8.
- External health, browser GET, HEAD, initialize, tools/list, search and page
  retrieval passed. Monitoring and unrelated service checks returned 200. SSE GET returned 405
  with `Allow: POST, HEAD` in 0.364 seconds.
- Real Python MCP SDK 1.27.0 completed initialize -> list five tools -> search
  with protocol 2025-11-25 and no tool error.
- An additional 30 sequential calls (10 lists, 10 searches, 10 page reads)
  all returned HTTP 200 without JSON-RPC/tool errors: p95 0.311 seconds,
  max 0.541 seconds, measured from the operator's machine. This is a smoke
  sample, not a capacity benchmark.
- Reload at 18:01:12 passed. At 18:02:08 only master 643435 and worker 643662
  remained (12/16 FDs); no old worker remained past the 30-second deadline.
- Through 18:02:08, post-recovery access logs contained zero 5xx, 134 POST 200,
  17 POST 202 and 382 deliberately rejected SSE GETs. All 15,691 earlier 500
  responses had absent/zero upstream processing time.
- Local validation: 286 tests, architecture merge-ready, diff check and strict
  site build passed. Actual nginx syntax and live lifecycle were tested on host.

Applied configuration SHA-256:

```text
7bf6520c75b8d35318acb91a52360e80324c763d8cebca5a79a48753e790ee6a  /etc/nginx/nginx.conf
288f013098b88e617e9c8920237fa6a72eab978c72378967e778b8a7bf61339d  /etc/nginx/sites-available/ai.v8std.ru
61ff46e3bb0929178410ad8dbea72b384837be8681d416389a73b2423b50d867  /etc/nginx/conf.d/v8std-mcp-emergency.conf
```

Application file SHA remained unchanged before/after:
`423017ecab0e96003dde0451fe6d5f7579d33f25b18ed52455968d22e69a968c`.

## Postmortem conclusions and release discussion

The confirmed failure was edge connection-slot exhaustion before an upstream
request could be processed. Long-lived unsolicited streams kept backend and
edge sockets occupied; the low worker limit and unreaped binary generations
amplified the problem. The application was alive throughout our investigation.
Initial successful probes did not disprove the intermittent failure.

A prior local merge was incorrectly easy to read as an operational fix; it
had no production effect. Future completion reports must name the deployed
component, checksum/SHA and observed post-deploy behavior. The emergency repair
now has those observations. The proposed 100k topology remains unmeasured.

For the next discussion: first agree the public tools-only contract and the
compatibility cost of Resource removal; then measure request CPU, refresh
blocking, response bytes and concurrency limits. Add a small set of operational
signals (real tool probes, connections/FDs, 5xx/429, p95, memory), review nginx
templates with a real parser, and benchmark before sizing horizontal replicas.
Resources, the old v3 design, monitoring redesign and the architecture-process
bootstrap are not prerequisites for this emergency recovery.
