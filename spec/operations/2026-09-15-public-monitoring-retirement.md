# Public monitoring retirement — production evidence

## Authority and outcome

On2026-09-15 the user explicitly requested complete public-monitoring removal
and confirmed the scope including production, closed archival,410 responses,
producer removal and preservation of MCP/private logs. Approved package:
`eca506a`, `design:mcp-public-monitoring-retirement`.

Only the monitoring publication chain was retired. This is **not** an MCP
runtime/container deployment, image publication, main push, capacity proof or
permission to remove other websites/services.

## Resolved targets and protected archive

Host: SSH alias `ai.v8std.ru`. Enabled nginx symlink resolves to
`/etc/nginx/sites-available/ai.v8std.ru`. On2026-09-15 at12:28UTC its exact
monitoring locations were replaced and nginx gracefully reloaded.

Closed archive on the server: owner `root:root`, mode0700; its location
is recorded privately. Archived, not destroyed:

- original nginx vhost plus installed candidate;
- `v8std-mcp-monitoring.timer` and `.service`, including service drop-in
  `10-read-nginx-log.conf` (`SupplementaryGroups=adm`);
- `/var/www/ai.v8std.ru-monitoring/`, containing `index.html` and `stats.json`;
- `/opt/v8std-mcp/scripts/v8std_mcp_monitoring.py` and its exact Python3.12 pyc;
- twelve identified historical backup files: eleven renderer copies dated
  April28 and one monitoring-unit backup. No unrelated backups were moved.

Neither `www-data` nor `v8std-mcp` could read the archived JSON when checked
with `runuser -- test -r`. No archived payload was printed or copied into the
repository. This is a same-host recovery archive, not an off-host disaster backup.

Config SHA256 before:
`288f013098b88e617e9c8920237fa6a72eab978c72378967e778b8a7bf61339d`.
After:
`943575822dc516d56852cd226ab423ee308a4f47da97a5c29f23e280e6690230`.
Diff changes only two monitoring locations and the final newline. MCP/TLS,
rate limits, upstreams and other vhosts were not changed.

## Execution details and verification

1. Confirmed previous public JSON200, active/enabled timer, healthy MCP.
   Validated nginx before changes and checked exact original checksum again
   immediately before replacement. Created archive via root `mktemp`/umask077.
2. `systemctl disable --now v8std-mcp-monitoring.timer`, then stopped its
   service. The running oneshot exited on SIGTERM (`Result=signal`, status15).
   A strict inactive guard correctly stopped the first archive attempt because
   systemd reported `failed`, not `inactive`. Verified MainPID0 and terminal
   state before proceeding, then cleared only this unit's failed state.
3. Installed scoped nginx candidate; `nginx -t` passed, then
   `systemctl reload nginx`. An immediate same-second request still reached an
   old worker and returned200; subsequent fresh requests returned410. There
   was no restart or live worker kill. Both pre/post `nginx -t` reported the
   existing unrelated certificate OCSP warning; syntax checks passed.
4. Moved the exact retired files into the closed archive. Ran daemon-reload
   and masked both unit names to `/dev/null`. Final state for both:
   `LoadState=masked`, `ActiveState=inactive`, `UnitFileState=masked`.
   `list-timers --all v8std-mcp-monitoring.timer` listed zero timers.
5. Public output directory, active renderer/pyc and timer enablement link are
   absent. Regular-file reference scan over nginx/systemd/cron directories and
   active scripts found no remaining publication configuration after archival.
   Root crontab contained no matching monitoring command. Unrelated pre-existing
   broken ModemManager/udisks symlinks encountered by an earlier grep were not
   altered; the final scan deliberately examined regular files.
6. Externally checked GET and HEAD for `/monitoring`, `/monitoring/`,
   `/monitoring/stats.json`, `/monitoring/stats.json?retired=1`,
   `/monitoring/unknown`, `/%6donitoring/stats.json`: all12 passed410 with
   `Cache-Control: no-store`; GET body was only nginx's136-byte410 page;
   HEAD body empty. No dashboard fields were returned.
7. Rechecked at12:35:20UTC, more than one former five-minute timer period after
   reload: both units still masked/inactive, public output/renderer still absent,
   JSON still410/no-store, MCP still the same active PID/start time.

## MCP and private data preserved

- MCP MainPID before/after: **673384**; ActiveEnterTimestamp unchanged:
  `Thu 2026-09-10 09:47:05 UTC`. Active throughout checked boundaries.
- MCP unit SHA256 unchanged:
  `072bd0e8ee1d2b24012085a4d7563f60ab5103fcef41de41a8ca9afb95df84ab`.
- `/healthz` HTTP200, `ok:true`,1423 pages,3281 vectors; corpus hash unchanged:
  `4876122c8f2fa3c25c49afc0c986a72a976d4466e9b654041729ab42a634f4e4`.
- Real JSON-RPC `initialize` returned200/result and negotiated2024-11-05;
  `tools/list` returned the five existing tools with no JSON-RPC error.
- `/var/lib/v8std-mcp/tool-usage.jsonl` remains0640 `v8std-mcp:v8std-mcp`;
  nginx access log0640 `www-data:adm`. Contents were not rewritten or dumped.
- `/etc/logrotate.d/v8std-mcp-usage` remains0644 root-owned and retains
  daily/rotate365/compress/copytruncate, su/create0640 v8std-mcp.
- No server package installation, Docker setup, SSH/renewal/fail2ban changes,
  other-vhost cleanup or raw-log deletion was performed.

## Recovery and future deployment

Original paths are listed above; restore file owner/mode from archived metadata
if an explicitly approved future recovery needs them. Re-publication requires
new user authority; do not automatically restore old alias or unmask timer
during container rollback. For nginx repair, preserve410 boundary and validate
before reload. Previously downloaded client copies cannot be revoked.

Shipped edge config and real local nginx conformance belong to the retirement
implementation. Keep future legacy backups post-retirement so rollback cannot
reintroduce removed generator/job. Persistent private usage logging of the
future container remains a separate unfinished Task6 gate; no private sampler
or public dashboard is needed to satisfy it.

## Local implementation checks

Implementation commit `5bfd76b70f3fed1a5c8d774cc37f14278945053e` removes the
1075-line generator and281-line dedicated tests, adds shipped410 locations and
real nginx conformance. With the pinned local nginx image
`sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c`:

- RED:4 tests,21 failing method/path subtests before tombstones (301/200/404/405
  instead of410); GREEN:4 tests passed in0.441s, all21 GET/HEAD/POST cases.
- Existing stale HTML/JSON sentinel never served; root, MCP/health/version and
  static-index success/error/cache boundaries preserved with dead MCP upstream.
- Fixture used loopback-only ephemeral port, UID10001, read-only mounts/root,
  cap-dropALL, no-new-privileges,128MiB/1CPU. Exact owned containers removed and
  absence checked after both runs; no image pull, network prune or production test.
- All18 server tests passed, including private usage logger behavior. Server
  and logrotate source bytes unchanged from `eca506a`.
- Architecture focused run exposed missing explanatory section headings in two
  candidate-only ADRs (one predating retirement). Added required sections without
  changing front matter/lifecycle or weakening tests; all12 architecture
  repository tests then passed in1.619s.
- Strict build passed:3282 vectors,1430 articles,0 HTML violations and3 license
  files. Ordinary architecture validation and `git diff --check` passed.

The first full suite started before the ADR-heading fix and ended with that
single known failure:632 tests in328.641s,10 opt-in skips. A fresh complete run
after the correction passed:632 tests in336.791s,10 opt-in Docker skips.
Enabled retirement nginx conformance was separately run and passed above.
Existing Starlette deprecation warning remains recorded for release triage.

Independent Task1 code review and Task2/cross-retirement graph review approved
spec compliance and quality without blocking findings. Production assertions
were reconciled by the controller against its actual SSH/HTTP tool outputs;
reviewers did not perform another production operation.

Subsequent real merge-ready exposed a validator implementation defect: retired
contracts still required their removed Python fitness module. Corrective Task3
is limited to honoring already-computed terminal lifecycle states while keeping
all active fitness/incomplete-plan gates. It changes no product/process policy.
Its focused verification is recorded separately; the632-test run above predates
that correction. The broader container and CI plans are still incomplete.
None of these checks authorizes whole-branch integration or image release.

Validator correction `cbbbd17df13abd1e563d7a08aea59f9de6b00df2` adds two lines
only to the fitness loop and two regression tests (eight lifecycle/timing
subcases). RED produced all eight expected obsolete-evidence failures; GREEN
passed47 architecture validation/CLI/repository tests in5.244s. Active missing
fitness still fails, and retired artifacts still undergo reference validation.
Real merge-ready no longer requires removed monitoring tests; it still rejects
incomplete plans. No stub module, skipped existing test or weakened active
declaration was added to accommodate removal.

Independent final scoped follow-up approved Task3 spec compliance and quality
without findings. The retirement implementation plan is complete. Whole-branch
merge-ready still rejects only the two unfinished container/CI plans; this
work intentionally leaves main, remote branches and MCP runtime deployment alone.
