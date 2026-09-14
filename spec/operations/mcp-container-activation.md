# Controlled initial activation of container delivery

**Status (2026-09-15):** ordinary controller implemented for scoped review;
first-bootstrap implementation and native rehearsal are still pending.
Local disposable evidence is not a live installation, CI activation, published
image proof, or target-host capacity guarantee. This runbook authorizes none of
those operations. The current external scope remains image-only.

## Authority and stop conditions

Initial activation requires an explicit operational request for the exact
verified main SHA and published image digest. Until then, leave production,
secrets, branch rules, environment settings and unrelated hosted services alone.
The ordinary automatic path starts only after initial rollback has been proven.

Stop before any switch if the backup cannot be restored, the source manifest
is not reachable, the image/provenance/configuration is unverified, capacity is
insufficient, the predecessor is missing, or the restricted controller cannot
reconcile a crash. A healthy systemd wrapper is not application readiness.

## Host inventory and backup gate

- Refresh the actual target host identity, OS, CPU/RAM/swap, available disk,
  file descriptors, network budget, running services, containers and listeners.
  Prior incident measurements are historical, not current capacity evidence.
- Identify the precise nginx virtual hosts, includes, default server, certificate
  paths and renewal hooks. Ensure the ai.v8std.ru TLS endpoint and renewal no
  longer depend on an old site's configuration before any cleanup.
- Preserve SSH access, monitoring, fail2ban and certificate renewal. Removing an
  old website is not permission to remove unrelated operating services.
- Back up the existing Python runtime, environment/dependencies, unit/drop-ins,
  nginx configuration, working corpus/cache and certificate configuration to
  protected off-host storage. Keep secrets out of repository and public logs.
- Restore into a disposable environment and exercise the old endpoint. Record
  exact cleanup targets and recovery instructions; obtain the operational
  approval before removing or disabling them. Prefer recoverable moves.

## CI and restricted-host gate

- Protect main and require the actual validation checks used by this workflow.
  Audit bypass permissions; a branch name alone is not an authorization check.
- Restrict the production environment to verified main releases. PRs, forks,
  tags, untrusted inputs and stale runs must not obtain host credentials.
- Establish a restricted release identity and a separately constrained static
  artifact publisher. Neither credential grants arbitrary shell commands,
  arbitrary paths/environment variables, root login or Docker group access.
- Install and verify the trusted host controller, its fixed configuration,
  attestation verifier, bounded job supervision and durable journal/recovery.
  Ordinary release envelopes cannot replace their own trust policy.
- Keep automatic runtime switching disabled until the initial published-image
  cutover and predecessor recovery are demonstrated. Test the kill switch: it
  blocks new releases without interrupting an in-flight rollback.

## Artifact and bootstrap ordering gate

Use the same published runtime digest later supplied to local users and the
Catalog. Do not rebuild a special production image on the server.

1. Verify the main source SHA, published multi-platform index digest,
   host-platform child membership, publisher identity and configuration digest.
2. Install the independent nginx index store and publish the verified immutable
   archive under its hash before publishing a manifest that references it.
3. Publish the site's manifest and verify its actual public source URL and
   archive bytes. A successful Pages job alone is insufficient to prove freshness.
4. Verify the public-default thin image against that manifest before stable
   promotion or the first container switch. Before this bootstrap, candidate
   builds are not a usable public-default release.
5. Exercise the candidate on its private loopback port, with exact runtime SHA
   and corpus ID, real MCP calls and static downloads while the runtime stops.
6. Perform the initial controlled cutover while retaining the tested Python
   predecessor. Do not manufacture a Docker predecessor or claim rollback from
   an empty release history. Establish the first verified container predecessor
   before enabling ordinary automated transactions.

## Capacity and acceptance gate

For ordinary deployment, measure old runtime + candidate + snapshot preparation together, including
Docker/OS overhead and static index traffic. Verify memory, disk staging and
pins, descriptors, CPU and bandwidth before switching. Raise capacity or change
the accepted rollout design if the measured host cannot accommodate overlap;
do not silently kill the predecessor to make room.

Only the separately authorized first migration may use stop-legacy/start-new
inside a scheduled window of at most two hours if overlap cannot fit. That
exception does not weaken the ordinary automatic gate, establish single-runtime
capacity, or authorize stopping production now. Prepare and verify the backup,
immutable artifacts and independent recovery guard before the window. Mint the
300-second execution envelope just before each attempt, not before lengthy
preparation. Stop new attempts at least 30 minutes before the window ends;
reserve more time if the measured legacy restoration needs it. Already-started
recovery remains necessary after the window expires. `bootstrap`,
`bootstrap-recover` and `bootstrap-status` are **not implemented in this slice**;
the restricted SSH entry rejects them. Do not manufacture `active.json`.

Exercise initialized idle agents, normal POST tool calls, reconnects, shared NAT,
snapshot refresh and concurrent archive downloads. Record the actual mix,
duration, error rate and latency. Neither worker_connections nor idle TCP count
proves support for 100,000 coding agents.

Record the initial release journal, exact SHA/digests/corpus/configuration,
public MCP/TLS and static delivery results, failure/rollback rehearsal and
monitoring checks in the verification record. External Catalog acceptance and
closure of the alternative PR remain separate delivery outcomes.

## Read-only legacy observations, not restoration proof

The coordinating owner recorded the following on 2026-09-15. Refresh before an
authorized migration; corpus files can change. No local test configured this
host. Full private evidence is in the Task5 handoff's
`legacy-preflight-2026-09-15.md`.

- `/etc/systemd/system/v8std-mcp.service` is enabled/active; no drop-ins or
  EnvironmentFiles. Unit SHA256:
  `072bd0e8ee1d2b24012085a4d7563f60ab5103fcef41de41a8ca9afb95df84ab`.
- WorkingDirectory `/opt/v8std-mcp`, User/Group `v8std-mcp`;
  `/opt/v8std-mcp/venv/bin/python` resolves to `/usr/bin/python3.12`.
  ExecStart runs `/opt/v8std-mcp/scripts/v8std_mcp_server.py` with
  `--index-url https://v8std.ru/ai/pages.jsonl --vectors-url https://v8std.ru/ai/search-vectors.jsonl --cache-dir /var/lib/v8std-mcp --host 127.0.0.1 --port 8765 --mcp-path /mcp --max-snippet-chars 4000 --usage-log /var/lib/v8std-mcp/tool-usage.jsonl`.
- A protected backup must establish trusted ownership and complete source/venv
  identity; do not infer these from a few matching source hashes.
- Preserve `/var/lib/v8std-mcp/{pages.jsonl,search-vectors.jsonl,llms.txt,llms-full.txt}`.
  Separately preserve private usage logs; never print their raw contents or use
  changing usage logs as corpus identity.
- Native legacy health is HTTP200 with 1423 pages/3281 vectors. Compare its
  `sha256` = `4876122c8f2fa3c25c49afc0c986a72a976d4466e9b654041729ab42a634f4e4`
  and `vectors.sha256` = `7713439da96757be4cf786d303e1cfb4b7e336ca8ec54a28a722701f6ef6c3c8`.
  It does **not** expose the new runtime/corpus/hold identity fields.
- Refresh the private resource inventory before migration. Neither overlap
  nor single-container preparation is proven to fit.
- Check the MCP certificate and any dependencies on other virtual hosts
  before changing TLS. No unrelated service deletion is authorized.
  Preserve SSH, HTTP/HTTPS, loopback8765 until cutover, renewal and
  monitoring. Record the remaining private inventory outside Git.

Before migration, inventory and hash the entire saved code, dependency lock and
installed venv/interpreter, unit/configuration and coherent data set; protect
the backup off-host, restore it in disposable Linux, and measure return time.
The ordinary controller does not restore this legacy Python deployment; that
is the pending bootstrap slice. Do not stop the still-enabled legacy unit until
that slice proves preaccept restoration and postaccept reboot ownership.

## Reviewed host installation boundary (future operator action)

Installation is separate from release envelopes. Install only an independently
reviewed, verified main revision; update trust/controller only under a separate
operator authorization. No release input can replace them.

| Fixed host target | Owner / access / contents |
|---|---|
| `/opt/v8std-release/scripts/` | root, not group/world writable; `v8std_mcp_release.py`, `v8std_mcp_snapshot_format.py`, `v8std_mcp_chunks.py` from the same reviewed revision; stdlib-only host dependency chain |
| `/opt/v8std-release/release-entry.py` | root0755, installed from `deploy/container/release-entry.py`; parent chain root-owned |
| `/etc/v8std-release/policy.json` | root0600, parent root0755, installed from the disabled example and explicitly configured; no symlinks/writable parents |
| `/var/lib/v8std-release` | root0700; journals, durable inbox, receipts, trusted manifests, references, pins, slots and verifier configuration; never writable by CI |
| `/srv/v8std-indexes` and `/srv/v8std-indexes/v1` | precreate root0755 for nginx traversal; publisher alone writes, nginx only reads; objects directories0755/files0644; staging0700 |
| `/etc/nginx/v8std-release/upstream.conf` | root-owned managed include, initially created only by the approved bootstrap; not an arbitrary caller path |
| systemd recovery units / sudoers | exact reviewed files from `deploy/container/`; validate locally on native Linux before enabling |

The installed controller runs `/usr/bin/python3 -I`; it adds only its own
root-owned module directory to imports. Provision the fixed trusted executable
PATH (`/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`), `gh`, Docker/buildx and
nginx as operator-owned dependencies. Test actual `gh attestation verify`
capability/read access using the intended root service context: child commands
receive only that PATH and `HOME=/var/lib/v8std-release`, not CI environment
variables, user Docker config, proxy settings or a caller's token. Do not copy
the developer's credentials or change their Docker socket/privileges.

The publisher account `v8std-publisher` has no Docker group, general sudo, root
SSH, SCP/SFTP or writable controller/policy/store paths. Install the exact
`release.sudoers` only after `visudo -cf` succeeds. The authorized key entry
must use `restrict,command="/opt/v8std-release/release-entry.py"` and an approved
public key, with no PTY/agent/port/X11 forwarding and no alternative shell/key
entry. Confirm this through an actual restricted-account native test before
issuing a CI secret. SSH host key pinning is mandatory; do not use accept-new or
disable StrictHostKeyChecking in CI.

`release-policy.example.json` is intentionally unusable by default:

- `enabled:false` disables all stateful public host commands, including status;
  syntax-only `validate-envelope` remains available. Leave it false until the
  restricted entry, durable recovery and store have passed their own gate.
- `enabled:true,runtime_enabled:false` permits static publish/reference and
  structured status/recovery with empty runtime configs and no capacity proof.
  This is the static-only setup: it does not require a Docker cutover. Image
  publication in GitHub is independent of either host switch.
- Ordinary runtime deploy requires **both** host flags true, a real accepted
  predecessor, trusted configuration and capacity evidence, plus independently
  enabled/protected runtime deployment in future CI. Image/corpus publication
  must not implicitly enable that CI job. Disabling `runtime_enabled` blocks
  new runtime jobs, not cleanup/recovery already owed to accepted work.
- Do not set `enabled:false` as an in-flight kill switch: it also blocks the
  recovery service. Keep recovery enabled until all accepted work is reconciled.

Each allowed config digest is SHA256 of canonical JSON with exactly `site_url`
(`https://v8std.ru/`), `refresh_seconds`, `max_snippet_chars`, `memory_bytes`,
`cpus`. Keep the existing strict/direct runtime profile unchanged. No second
source URL, image tag, mount, arbitrary file, shell or env appears in an envelope.
Policy `platform` is explicitly `linux/amd64` or `linux/arm64`, not inferred from
Docker `.Id`. Verify the attested index, child mediaType/platform membership and
config descriptor: `.Id` can be index, child or config in the verified mapping.

Runtime activation requires root-reviewed native mixed-load evidence at
`/var/lib/v8std-release/capacity/<sha256>.json`; policy binds its byte hash.
The hash is an operator approval binding, not automatic interpretation or proof
of its measurement content. Set policy disk/MemAvailable/FD thresholds from the
rehearsal; memory reserve must be at least candidate memory cap +128MiB, measured
while the old service is running. Controller checks live disk, MemAvailable,
RLIMIT_NOFILE and the evidence hash before runtime effects. Example thresholds
are not target-host recommendations.

Use `edge-http.conf` once in nginx `http{}`, and `edge-locations.conf` only in
the inventoried ai TLS server. Preserve existing TLS/default-vhost ownership.
Set native main-context `worker_shutdown_timeout 30s`; rehearse worker/FD,
client-header and idle keep-alive bounds with the existing configuration.
The sample has shared active8/download2 admission, upstream keepalive2,
download1MiB/s and retryable429/503+Retry-After1. These are local test settings,
not permission to apply them on the 961MiB host. On any nginx syntax error the
old include must be restored with no reload. Public TLS smoke must succeed
without insecure TLS options before acceptance.

Install/enable recovery timer only after native `systemd-analyze verify` and
fault rehearsal. Services are `Type=exec` with `RuntimeMaxSec=300s`,
`TimeoutStopSec=5s`, `KillMode=control-group`. Do not substitute `Type=oneshot`:
RuntimeMaxSec does not bound its execution. The timer runs on boot+15s and
30s after completion; SSH scheduling uses fixed detached `v8std-release-job`,
not `--pipe`/live stdin. A queued receipt survives scheduling failure, SSH loss
and CI cancellation and is picked up by recovery.

## Task6 restricted wire interface and exact acknowledgements

The only public forced commands are `validate-envelope`, `deploy`, `recover`,
`status`, `publish-index`, with **no arguments**. The examples below describe
future CI invocations, not commands executed against production in Task5.
`release_host` must come from the separately approved, pinned SSH setup.

`validate-envelope` and `deploy` consume one compact JSON line (at most8192
bytes) followed by EOF. Schema is `deploy/container/release.schema.json`.
`deadline` is UTC epoch seconds, future and at most300s away; an ordinary deploy
also requires more than180s left for rollback reserve. Runtime source SHA,
corpus manifest source SHA and triggering workflow SHA are independent. Never
label a reused image with a new content SHA. Bind image/artifact attestations
to `zeegin/v8std/.github/workflows/ci.yml`, source-ref `refs/heads/main`, exact
source digest and GitHub issuer; self-hosted attestations are denied. Chosen
runtime/corpus and trigger commits must belong to current authorized main
history. A reusable/different signing workflow requires separately reviewed
host trust changes, not an envelope field.

`publish-index` consumes a JSON header line (at most65536 bytes), then exactly
`manifest.archive.bytes` raw archive bytes, then EOF. The header has exactly:

```json
{"schema_version":1,"publication_id":"content-run-123","sequence":123,"trigger_sha":"<40 lowercase hex>","manifest":{},"deadline":0,"action":"publish"}
```

Replace the placeholders with the validated snapshot manifest and fresh
deadline. `manifest.archive.path` must be exactly
`https://ai.v8std.ru/indexes/v1/<archive-sha256>/snapshot.tar.gz`.
Compressed archive cap16MiB, unpacked cap64MiB; existing snapshot member/row
validation applies. Upload gets30s total, each fd wait at most20s. Extra/truncated
bytes, hash mismatch, arbitrary path/env/shell fields or missing EOF fail closed.
The host derives staging/final paths itself. CI never supplies a preexisting
host path and never needs unrestricted file transfer.

With `upload-header.json` compact and `snapshot.tar.gz` from the CI artifact
workspace, one concrete invocation is:

```sh
python3 -c 'import json,sys; h=json.load(open("upload-header.json")); sys.stdout.buffer.write(json.dumps(h,separators=(",",":")).encode()+b"\n"); sys.stdout.buffer.flush(); import shutil; shutil.copyfileobj(open("snapshot.tar.gz","rb"),sys.stdout.buffer)' | ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes "$release_host" publish-index
printf '%s\n' '{"schema_version":1,"kind":"publication","id":"content-run-123"}' | ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes "$release_host" status
```

Use pipeline failure propagation (`set -o pipefail`) in CI. Poll the exact typed
status query with bounded retry/backoff. Accept only the expected
`publication_id`, `sequence`, `action`, `trigger_sha`, `corpus_source_sha`,
`corpus_id`, `archive_sha256`, **state COMMITTED and no error_code**. `QUEUED`,
`RECEIVED`, `VERIFIED`, `RECOVERY_REQUIRED`, `FAILED`, `NOT_FOUND`, an SSH exit0,
or an already-existing immutable HTTP200 is not publication acknowledgement.
The receipt is durable before enqueue; recovery reconstructs a missing inbox.
COMMITTED means verification, retention bookkeeping and immutable visibility
have completed, not that Pages has published a new manifest.

After that receipt, verify public archive hash/GET/HEAD, publish Pages, verify
the public manifest and its target bytes, then send a **new** publication ID
with `action:"reference"`, the same verified manifest, a fresh deadline and a
monotonically increasing reference sequence. It sends only the header line
and EOF, **no archive bytes**. For example:

```sh
python3 -c 'import json; print(json.dumps(json.load(open("reference-header.json")),separators=(",",":")))' | ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes "$release_host" publish-index
printf '%s\n' '{"schema_version":1,"kind":"publication","id":"reference-run-123"}' | ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes "$release_host" status
```

Reference verification also binds corpus/trigger authority. Its exact COMMITTED
receipt proves `current-index.json` and old/new reference timestamps were
durably updated; it does not independently attest the Pages job. Failed Pages
publication must not send this acknowledgement. Failed/unreferenced objects
remain retained for at least seven days. Stale reference sequences cannot undo
a newer current reference. Immutable publication IDs and release IDs cannot be
mutated: retry the exact original header/envelope, including its deadline, or
create a new ID/sequence for a new attempt. A terminal FAILED ID stays failed.

Runtime status query is the same bounded shape with `kind:"release"` and the
exact release ID. `status` with EOF and no JSON returns the latest release only;
use `ssh -n ... status` for that form, not for queries/uploads. Output is bounded
structured identity/status, not raw command output/secrets. Runtime acceptance
is COMMITTED; require `cleanup_complete:true`, no error and actual health for
an operationally complete deployment. COMMITTED with cleanup pending is already
accepted and recovery must finish it, never undo it. `recover` queues independent
reconciliation and does not mean rollback has already succeeded.

## Runtime recovery and retention semantics

Each attempt keeps300s total /90s readiness /30s smoke and drain /45s stop.
The forward phase conservatively reserves180s for rollback, so verification,
pull/readiness/switch share at most120s (less envelope transport time). No phase
borrows from rollback; an over-budget candidate is cancelled. The runtime loader
retains its360s attempt/20s read configuration. Detached recovery has a separate
bounded300s to restore owed state, not to extend candidate acceptance authority.

Host pins retain archives; they do not select a runtime. The private read-only
`/run/v8std-release/control.json` mount commands hold/capture or selected manifest.
The coordinator cancels preparation, loads/verifies selected bytes and emits an
actual hold token with archive/corpus/runtime identity. Hold is not an MCP tool
or public source setting. Runtime cache `runtime-pin.json` retains its actual
accepted generation even if a worker changed the disk pointer but died before
the process accepted it. Source movement cannot silently change the selected
candidate or rollback corpus; resume explicitly acknowledges normal refresh.

Before acceptance, recovery reconciles deterministic owned objects, restores
the selected predecessor/upstream, checks real public MCP/static results, then
stops the candidate. Failure is RECOVERY_REQUIRED, never successful rollback.
After COMMITTED, recovery starts/reselects the accepted candidate if necessary,
finishes active/predecessor persistence, drain and resume. A later stopped
accepted process is restarted from the accepted record. Monitor both receipt
errors and live readiness; historical COMMITTED alone is not current liveness.

Retain at least one successfully served predecessor image/config/corpus and all
in-flight pins. Stopped containers and dedicated caches are intentionally kept;
there is no automatic Docker prune. Static GC is internal operator maintenance,
not a public CLI verb: it checks exact immutable layout/hash, current reference,
all pins/pending work and seven-day last-reference age before removing anything.
Without valid pin/current-reference evidence GC refuses to run. Review exact
owned targets before later cleanup; preserve recovery records. No legacy/old
vhost cleanup is bundled with a successful container release.
