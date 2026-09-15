# MCP container delivery — verification record

This is implementation evidence, not authorization to publish or activate a host.
The accepted design and contracts remain authoritative. Unfinished or external
checks below must not be reported as passed.

**2026-09-15 direction update:** public monitoring preservation and the proposed
private monitor-state bridge are superseded by the approved retirement design.
Production410, masked units and closed archive are recorded separately in
[retirement evidence](2026-09-15-public-monitoring-retirement.md). Earlier dated
measurements and design-pause text below describe history, not current tasks.
Private container logging, CI and the other Task6 gates remain incomplete.

## Scope and baseline

- Main baseline: `b7bef11e145a188b30e7a7b17df2be4cb1acbd0c`.
- Approved design package: `537fe79`; implementation plan: `a3b2474`, with later
  recorded interface refinements on the same feature branch.
- Working branch: `codex/mcp-container-distribution-design`, primary checkout.
- No container host installation, image publication, Catalog submission, PR
  closure or container activation are established by this record. The separately
  authorized public-monitoring retirement is the only later live change here.
- Capacity of 100,000 coding agents is a target, **not a measured result**.

## Completed local evidence

### Deterministic corpus format and producer

Implementation: `7255a93b818005a5290eb941ac74c5cccb579afa`.
Reviewed correction: `821d1700786e36d2f719b67a9d1ac323fa1266f0`.
Independent task review and scoped re-review completed without open findings.

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshot_format tests.test_v8std_mcp_index tests.test_v8std_search_features -v
```

Result after correction: **65 tests passed** (35 snapshot tests and 30 existing
index/search tests). Initial implementation additionally passed the then-current
399-test full suite; this is not a substitute for the final suite after all
runtime, container and CI changes.

The real corpus contained 1,423 pages and 3,281 vectors. Repeated snapshot builds
produced identical compressed bytes, original page fields were preserved, and
full vector regeneration matched the existing vector file byte for byte.
The generator and reader now share the unchanged dependency-free chunk helper.
The standalone producer also ran with Python `-S`.

Hostile archive cases include invalid members, framing, paths, gzip payload,
JSON structure, vector identity/hash/data, size limits and missing corpus rows.
Publication fault injection covers seven distinct fsync stages. Failure after
manifest rename leaves the **new valid manifest visible**, while its durability
is unconfirmed; it does not prove the previous manifest remains selected.
The old immutable archive remains intact. These tests are fault injection,
not a real machine power-loss experiment.

### Bounded source, cache and background coordinator

Implementation: `ecc946c`, streaming staging correction: `005ba5d`, reviewed
pointer/lifetime fixes: `427aaf7cde5f288f980b335442c368dd1a28f081`.
Independent task review and scoped re-review completed without open findings.

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots -v
```

Final result: **48 tests passed in 35.869 seconds**. The unchanged 35 format
tests passed during the combined pre-fix run. Coverage includes real local HTTP
sources, redirects, 304, corrupt data, slow DNS/headers/body, partial IPC,
process termination, private streaming staging, shared-volume locks/budget,
pins, fsync/crash recovery and responsive current-generation access.

Review corrections reject pointer records that cannot later be canonically
committed, and release unused same-hash generation results before idle waits.
Parent-side production-index reconstruction, real refresh memory/latency and
the host release hold remain integration gates. Cache pins retain disk archives;
they do not freeze the running generation or prove release rollback behavior.

An isolated pre-runtime-change probe of the real index, excluding only its
process-local lock, measured 21,714,441 serialized bytes and 318,029,824 bytes
peak RSS while retaining original, serialized and reconstructed state. Encoding
took 0.102 s and decoding 0.0772 s on this Mac. This excludes new runtime
resources, spawn/staging and host overlap; it is not the final RAM budget.

### Frozen runtime — reviewed task evidence

Implementation: `b8656c1c238969d996e24f323333a925df9c5b87`.
Reviewed correction: `49e8b525c370a7f69f9681b3e1d695ee3e3b150f`.
Initial findings covered stdout backpressure, Markdown classification/escaping
and cache/port configuration. Scoped re-review confirmed all five addressed.
One pre-existing image-alt HTML protection edge case remains assigned to final
integration review; task acceptance is not final release acceptance.

Current equivalent regression command (the historical189-test run included the
now-retired dashboard tests):

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshot_format tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_presentation tests.test_v8std_mcp_runtime tests.test_v8std_mcp_index tests.test_v8std_mcp_snippet tests.test_v8std_mcp_server tests.test_v8std_mcp_combined tests.test_v8std_mcp_capacity
V8STD_MONITORING_RETIREMENT_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring_retirement -v
.venv/bin/python -m tests.mcp_runtime_benchmark
```

Combined result: **189 tests passed in 63.620 seconds**. Actual subprocess tests
exercise clean stdio, discovery before readiness, EOF/SIGTERM worker cleanup,
and loopback HTTP with two agents and the existing Resources. The existing
Starlette/httpx deprecation warning remains recorded, not suppressed.

The 256-case comparison kept all ranks/IDs identical and MRR 0.9939759036;
sampled score dictionaries were also identical. Desktop p95 was 46.570 ms before
and 49.018 ms after. These timings are not a stable production latency estimate.

The first implementation's real-corpus benchmark included spawn/import, source
download and verification, streaming staging, Resource presentation, trusted
IPC and parent reconstruction. A 40 ms sampler included the fixture server,
old generation, worker, transfer/reconstruction buffers and allocator retention:

| Operation | Wall time | Sampled process-tree peak RSS | Query p95 during operation |
| --- | --- | --- | --- |
| Cold download/build | 2.903 s | 487,636,992 bytes | Not measured |
| Warm build while old data serves | 3.084 s | 567,066,624 bytes | 56.05 ms |
| Unchanged refresh, before optimization | 3.537 s | 665,911,296 bytes | 65.21 ms |
| New generation while old data serves | 3.606 s | 610,746,368 bytes | 71.05 ms |
| Source headers delayed two seconds | 4.919 s | 647,069,696 bytes | 64.21 ms |

Observed parent reconstruction was 93–179 ms; transferred prepared state was
32,663,778 bytes. Peaks are samples, not upper bounds or cgroup limits. Warm
build here deliberately retained a serving generation, not an empty-process
offline startup. Runtime overlap on the target host has not been measured.

This exposed unnecessary reconstruction of an unchanged generation, including
duplicate archive verification. These baseline numbers must not be reported as
the optimized release. Resource presentation was moved into background build;
wire encoding of bulk responses still has a cost.

### Unchanged-refresh correction — reviewed local evidence

Implementation: `68902446bbb69df8e50eadb7be74b5c5d07521c4`; independent scoped
spec/quality review approved without findings. The ready coordinator
supplies its accepted archive identity. The worker still validates same-source
cached bytes and manifest consistency, but an unchanged result carries only
verified metadata. Cold/warm bootstrap, a different or repaired corrupt archive
retain full construction. Pointer/validator durability precedes success.

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_runtime.RuntimeTests tests.test_v8std_mcp_runtime.WireTests
.venv/bin/python -m tests.mcp_runtime_benchmark
```

Result: **72 tests passed in 51.553 seconds**. This does not close the separate
Task3 review findings about stdout backpressure and Markdown syntax handling.

Fresh paired unchanged-refresh measurements on the same desktop/corpus:

| Observation | Before correction | After correction |
| --- | --- | --- |
| Whole attempt | 3.704876 s | 0.742084 s |
| Received IPC payload | 32,663,778 bytes | 256 bytes |
| Parent decode | 0.157151 s | 0.002127 s |
| Sampled tree peak RSS | 627,490,816 bytes | 403,554,304 bytes |
| Query p95 during attempt | 76.368 ms (62 samples) | 48.613 ms (14 samples) |

Generation construction/encoding are skipped; strict cache verification runs
once rather than twice. Query sample counts differ because the attempt is
shorter, so no statistical significance claim is made. All 256 same-corpus
ranks/IDs and sampled score dictionaries remained equal, MRR 0.9939759036.
New generations still require full preparation; measured new-generation wall
time was 3.566641 s with sampled tree RSS 555,876,352 bytes. These are sampled
desktop observations, not memory ceilings, target-host acceptance or 100k evidence.

### Runtime correction and semantic-parser cost

The same combined MCP command at `49e8b52` passed **217 tests in 82.938 seconds**.
Regressions include drained 2 MiB frames, undrained stdout at EOF/SIGTERM,
worker cleanup, CLI/environment/default precedence, nested containers/fences,
incomplete links and titles, destination escaping, CRLF and source-map lifetime.
Runtime/build requirements pin `markdown-it-py==4.0.0`; pure format verification
remains independent of docs tooling. Canonical data/ranks were not rewritten.

The real-corpus benchmark retained all 256 ranks/IDs and sampled score
dictionaries, MRR 0.9939759036. Full-generation preparation now includes the
semantic parser/source maps: cold 5.432 s, warm-with-old 5.594 s, new-with-old
6.071 s. Corresponding sampled tree RSS was 653,115,392 / 636,731,392 /
699,695,104 bytes. Unchanged refresh remained 0.731 s with 256-byte metadata IPC;
it does not rebuild or parse Resources. New-generation concurrent query p95
was 62.55 ms across 106 samples. These desktop samples do not establish a
target-host memory ceiling or production capacity.

Final review must resolve the known case where `<code>` in image alt text can
incorrectly protect subsequent visible links from rebasing/validation. It was
reproduced in both the old scanner and the semantic-parser fix, so scoped
re-review did not extend its loop to it. This is explicitly not waived for release.

### Container implementation — partial acceptance, review pending

Scoped signed implementation: `9a3f483416484a0fe85ba55cc554df5b25e6f6c2`.
Independent task review requires fixes; this is not a completed multi-platform
or Catalog acceptance gate. Prototype images used base SHA `f5c45d2` labels while
packaging files were uncommitted, so they are test artifacts, not proof of exact
release provenance. Rebuild the final verified SHA before any release.

```sh
V8STD_TEST_LOCAL_BUILD=1 .venv/bin/python -m unittest tests.test_v8std_mcp_distribution tests.test_published_license_links -v
.venv/bin/python scripts/check_mcp_container.py --mcp-image v8std-task4-mcp:arm64 --site-image v8std-task4-site:arm64 --platform linux/arm64 --prefix /kb/ --chrome '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' --node /opt/homebrew/bin/node --host-gateway
```

Eight focused tests passed in 38.667 seconds, including isolated strict build.
Actual arm64 harness passed cold-online stdio, warm network-disabled restart,
HTTP readiness/tools, cold-offline 503, clean EOF and bounded SIGTERM. Direct
and Compose MCP used UID/GID10001, read-only root, cap-drop ALL, init,
no-new-privileges, persistent cache, 2 CPU and1536MiB memory limits. These are
test settings, not a throughput claim. Known modal-window snippet rules and
4000/32000-character configurations passed; five tools/three Resources retained.

Local profile preserved canonical archive bytes and source inputs. A fresh
Chrome151 profile observed18 unique requests over five representative pages,
including search/worker/fonts/licenses, all within the local `/kb/` origin and
prefix; no blocked public requests or bad responses. This sampled browser
request graph is not exhaustive coverage of every site page. Chrome emitted
Keychain/encryption warnings even with the isolated basic-password profile.
Manifest freshness, immutable successful archives, uncached404s and licenses
passed. Native Linux routing remains separate from Docker Desktop testing.

Two host Gateway0.43.3 sessions passed repeated warm-offline calls with separate
long-lived MCP containers and one cache. The actual Gateway-created containers
were **not read-only and did not drop capabilities**. Its Catalog configuration
does not expose the full direct/Compose hardening profile. The containerized
Gateway local-network test stopped at Docker socket permission denial under
UID/GID501:20; no root/group/permission retry was made. Cold local Gateway
routing and full hardening are not accepted. No socket was mounted into MCP.
Source Catalog schema decoding passed against mcp-registry8c773729; external
Catalog review/publication did not occur.

Both architecture images built, and amd64 static delivery passed under QEMU.
However, supervised amd64 full-corpus startup failed with `deadline`, no OOM,
and continued503 readiness. A separate direct phase diagnostic measured
3.390s imports,0.167s download,7.465s verification and **86.912s generation**,
97.935s total. Generation alone exceeds the60s loader attempt limit. That
unsupervised diagnostic is not successful runtime acceptance. Preserve the
production cancellation bound; require native amd64 full-corpus proof before
publication, and fix preparation if the native run also fails. Warm amd64 and
full lifecycle acceptance remain incomplete.

Owned test containers/networks/volumes and temporary Gateway/browser configs
were removed; test images and temporary build evidence remain. Unrelated
containers, listeners, active Docker configuration and host DNS were preserved. No registry, GitHub settings or target-host mutation occurred.

Review identified an implementation defect: Compose ignores an operator-set
`V8STD_MCP_SITE_URL`; the resumed fix must prove the same override controls
source and returned links. It also confirmed that the exercised Gateway launch
does not satisfy the accepted hardening profile. Upstream Gateway0.43.3
[`baseArgs`/`argsAndEnv`](https://github.com/docker/mcp-gateway/blob/v0.43.3/pkg/gateway/clientpool.go#L304)
adds init/no-new-privileges and configurable resource/user/network arguments,
but not read-only root, cap-drop or tmpfs. Catalog approval alone cannot correct
that mismatch. No daemon changes or privileged retry were authorized.

Initial review paused implementation at the architecture failure-recovery gate.
The subsequent user-approved360-second/Compose correction is recorded below;
Gateway profile/scope remains unresolved. Task4 remains incomplete; release
controller and CI Tasks5/6 have not started. Deferring Catalog or accepting
different launcher security profiles requires an explicit design choice, not
inference from the timeout instruction. Do not merge, publish or close PR33
from this partial result.

### Approved360-second attempt and Compose override — scoped fix

User explicitly requested «поставь 360 секунд и продолжай». Candidate
design/contract/plan refinement: `068c127`; signed code correction:
`9c1f3a72ce370fc816c32a6e0eeb2f773f23fb03`. Independent scoped re-review accepted
the timeout/Compose fixes without new critical or important findings. Runtime
now uses360seconds per attempt and20seconds per network read.
RPC/shutdown budgets are unchanged; early cancellation does not wait360seconds.
This is a changed safety budget, not a retrieval-performance improvement.

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_distribution.DistributionTests tests.test_v8std_mcp_runtime.RuntimeTests tests.test_v8std_mcp_runtime.WireTests -q
V8STD_MCP_SITE_URL=http://v8std.localhost:18765/kb/ .venv/bin/python scripts/check_mcp_container.py --mcp-image v8std-task4-mcp:fix360-9c1f3a7-amd64 --site-image sha256:78e79de36ed45fc9d620d66b8e8c4d0b673c276a867ed4d5bfe4b16e72bdcbfd --platform linux/amd64 --prefix /deliberately-unused/
```

Two focused tests first failed on60≠360 and the ignored explicit SITE_URL,
then passed. Combined **79tests passed in55.810seconds**, including accelerated
real worker timeout/reaping, close and wire lifecycle tests. The existing
Starlette warning remains recorded. Ordinary graph validation and diff checks
passed; this is not the final full suite/strict-build gate.

The runtime image was built after the scoped commit from a clean checkout,
with exact source SHA9c1f3a7. Local Engine index ID:
`sha256:0c282c458e6e19092c8d4e0db92b87eb2f8b05fa83ec6e7d5765221424579b79`;
amd64 platform manifest:
`sha256:26f35e15fd61beb5feca4a392e4701ac9757debdd43e15f15f0b4f2f1a8e15f8`.
These are local artifact identities, not a published multi-platform release.
The unchanged site prototype/corpus source SHA remainsf5c45d2; runtime and
corpus provenance are deliberately independent, not relabelled to match.

Actual supervised amd64/QEMU harness exited0:

| Scenario | Startup/polling/check duration | Result |
| --- | --- | --- |
| Cold-online stdio |118.81s| Ready, tools/Resources/snippet/links pass; EOF0 |
| Warm-offline stdio |111.58s| Verified cache and ranking preserved; EOF0 |
| Cold-online Compose HTTP |122.61s| Ready200,1423rows, exact runtimeSHA |
| Warm-offline HTTP |135.80s| Same corpus/cache, tools/links pass |

These durations are not isolated generation CPU measurements. The harness
allows390seconds only for readiness polling; individual RPC/read/stop limits
were not inflated. Cold-offline HTTP still returned live200/ready503;
HTTP SIGTERM exited143 within the bounded stop, stdio SIGTERM exited0.
An explicit `/kb/` SITE_URL worked while the computed default
`/deliberately-unused/` source returned404. Cache namespace, selected source
and returned links followed the override. No public fallback was used.

Direct/Compose non-root/read-only/cap-drop/no-new-privileges/init constraints
remain; MCP2CPU/1536MiB, site0.5CPU/128MiB. Own containers/networks/cache volumes
were removed, unrelated resources preserved, and no tests remained
running at handoff. The new image and evidence log remain for inspection.
Gateway was not changed or rerun; native amd64, registry and production evidence
are still absent. The earlier60-second failure remains valid historical evidence
and must not be rewritten as a pass.

Scoped review retains a minor harness limitation for final integration: any
differing SITE_URL override currently requires the computed default source to
return404, unnecessarily rejecting valid fixtures where both URLs exist. Keep
that assertion specific to the override regression scenario when repairing the
integration helper. This does not invalidate the saved run where default404
was intentional, and is not a runtime routing defect. Gateway remains the only
open important finding from Task4; no profile change was approved yet.

### Subsequent approved Gateway profile

The user subsequently approved launcher-owned profiles: production and our
direct Docker/Compose retain read-only/cap-drop; Gateway uses its actual native
isolation with explicitly documented differences. Missing readonly/capdrop/tmpfs
alone no longer defer Catalog. Candidate design/ADR/invariant/distribution
contract and the scoped Task4 plan were amended together. Required non-root,
init/no-new-privileges, nonprivileged mode and absence of Docker socket inside
MCP will be checked on each created Gateway server. This decision does not
claim that verification already passed or that cold routing, native amd64,
registry/Catalog acceptance or target-host deployment happened. Historical findings
above describe the contract at the time of the corresponding review.

Focused implementation now passes15tests (0.246s): required controls and exact
owned cache mount, rejection of root/privileged/missing controls/socket aliases,
DinD preflight before launch (also under Python optimization), and explicit
default404 regression mode. Generic overrides no longer require a broken
default. Compose/runtime/images were not modified by this fix.

Narrow actual verification used Gateway0.43.3 and two simultaneous warm stdio
sessions on network none; both initialized, listed/called tools, retained the
same server IDs across repeated calls and exited0 on EOF. Each server had
user10001:10001, init=true, SecurityOpt=no-new-privileges, privileged=false and
exactly the owned named cache volume, with no bind/socket. Observed readonly=false,
capdrop=null and tmpfs=null match the approved native profile. Fresh cache
preparation through the runtime took8.02s. This is launcher-profile evidence,
not a repeated full arm64/QEMU suite or cold-routing Gateway proof.

The run intentionally reused earlier local arm64 prototypes, not a new release:
MCP Engine image ID `sha256:bec25fa5b9f240225db206c5e21d35a8c28e2d4ae30b1b878d272eacd9df1031`,
site ID `sha256:ef6ceb9d711a1cd6830f3536d593fccb9c82bb0f6257a3da04c81460b785bb43`,
both labelled source`f5c45d23fc31285e96920719285b0a9253e4a6fe`.
No current-source provenance claim follows from these prototype labels.
Evidence log: `/tmp/v8std-task4-gateway.Fi3MeO/acceptance.log`.
Only owned project`v8std-task4-5137d494d1` containers/networks/cache and temporary
Gateway config were removed; unrelated containers were preserved.
Independent scoped review accepted both remaining findings: Gateway profile
conformance and the generic default404 helper defect are ADDRESSED; no new
Critical/Important breakage or out-of-scope findings. The reviewer inspected
the immutable diff, report and actual saved two-server log without rerunning
tests. Task4 local implementation/verification is complete, not published or
signed as a new commit. Commit signing was not completed at this stage. Tasks5/6 and
final release gates are still pending; signing was not bypassed.

### Local build environment

Observed 2026-09-10: Docker Desktop, Engine 29.7.2, linux/arm64; Gateway v0.43.3;
buildx v0.36.1. The installed application SDK is `mcp==1.27.0`.

Pinned multi-platform base indices:

- `python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea`
- `nginx:stable-alpine@sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c`

Both amd64 bases executed locally under emulation with read-only root, network
disabled, all capabilities dropped and no-new-privileges. Python reported
`x86_64`, `3.12.14`, zlib `1.3.1`; nginx reported `1.30.4`. This establishes
base-image emulation availability, not runtime-image or native amd64 acceptance.

### Search baseline

The pre-runtime-change desktop benchmark reported MRR 0.994 and p95 46.1 ms
on the existing benchmark corpus. Timing is environment-dependent and not a
service capacity measurement. The final comparison must use the same corpus
and query set on the implemented snapshot runtime.

## Remaining implementation and integration gates

| Area | Current evidence |
| --- | --- |
| Bounded refresh/cache, crashes, shared volume, offline recovery | Task review accepted locally; Linux/runtime integration remains. |
| Frozen generations, URL presentation, stdio/HTTP lifecycle | Task review accepted; known image-alt edge remains final release gate. |
| Runtime/static-site images, local request graph, Gateway sessions | Task4 local review accepted, including360-second QEMU/Compose fixes and native Gateway15focused tests/two warm sessions; signed handoff3165cc7 completed. Cold Gateway routing/native amd64 remain external gates. |
| Restricted host controller, rollback and independent index delivery | Task5 partial/uncommitted:29 release tests passed; regression reruns, review and first-bootstrap slice remain. |
| Fail-closed publication, process v2 synchronization | Pending. |
| Final semantic impact, merge-ready, fitness, strict build and full suite | Pending after all changes; strict build precedes the suite. |
| Final image smoke, refresh RSS/CPU, disposable mixed load | Pending; cannot establish production 100k capacity. |

## External acceptance boundary

### Refreshed release-request preflight

Normal signed commit`3165cc7e6ef2afcf12cdeca66c8070ab0737ba5b` now contains the
approved Gateway fix and candidate graph/evidence. The four reviewed packaging
files matched their immutable review snapshot before commit. Signing-pending
statements above are historical. Tasks5/6 are not completed by this commit.

Read-only checks on2026-09-10 found the public default snapshot manifest still404;
legacy `https://ai.v8std.ru/healthz` is200 with1423pages/3281vectors.
nginx syntax succeeds. Private host and TLS inventory is retained outside Git;
these observations do not establish capacity or migration readiness.
No host mutation, cleanup, tariff change or MCP cutover was performed.

GitHub main remains`b7bef11e145a188b30e7a7b17df2be4cb1acbd0c`.
Protection, environment and credential readiness require separate private checks.
An anonymous GHCR token request for`zeegin/v8std-mcp:pull` also returned403.
This establishes no public availability, not proof of package nonexistence or
of future workflow inability to publish with its own permitted GITHUB_TOKEN.

### Catalog producer round-trip gap

Docker registry remains at`8c773729f13f036da8c909be503fe433923a9aa2`.
Actual `catalog.ToTile` from that pinned upstream module was executed on the
current source entry, not a hand-built projection. It returned:

```json
{"input_long_lived":true,"output_long_lived_present":false,
 "input_defaults":{"cache_volume":"v8std-mcp-cache","max_snippet_chars":4000,"site_url":"https://v8std.ru/"},
 "output_defaults":{"cache_volume":null,"max_snippet_chars":null,"site_url":null}}
```

User/env/volume settings survive. Source `pkg/catalog/types.go` has no LongLived
field and `tile.go` cannot propagate it; the documented `cmd/catalog` uses this
conversion. Gateway0.43.3 defaults its global long-lived option to false, while
client reuse requires the server flag or global option. Therefore the earlier
explicit `--long-lived` warm harness does not prove the generated Catalog path.
No failed end-user session is claimed from this conversion-only probe; actual
generated-entry lifecycle acceptance must accompany the repair.

Probe used pinned Go1.25.11 image, non-root/read-only/cap-drop/no-new-privileges,
2CPU/768MiB,180s outer bound and no Docker socket. Final run copied go.mod to a
private non-root temp subdirectory (Go ignores a go.mod at the temp root), then
ran the exact upstream module; exit0. Source/evidence inputs remain in
`/tmp/v8std-catalog-path.r0u2kk/`. Both disposable probe containers exited and
were automatically removed; no default Catalog or user Docker settings changed.
The local GitHub license label is Other/NOASSERTION; upstream's actual license
filter rejects gpl/agpl/npl prefixes, so Other is not an automatic validator
failure. No license text or licensing terms were changed.

Limited static-index/CI setup and an upstream PR preserving LongLived require
separate authorization; local verification does not authorize those writes. Direct image publication and external Docker review
remain distinct outcomes; the server/runtime artifact contract is unchanged.

Registry release digests, provenance verification against those releases,
Docker Catalog acceptance, GitHub protection/environment/secrets, target-host
prerequisites and initial controlled activation require separate evidence.
The existing Python deployment remains the initial rollback path until that
activation is explicitly performed and verified. An automatically enabled
release path must not be inferred from a locally passing test or a written
workflow.

### Correction: test Catalog versus Docker-published Catalog, 2026-09-10

The earlier `ToTile` result is real but establishes a defect in the **local
test-catalog generator**, not loss in Docker's published catalog. Upstream
[Taskfile](https://github.com/docker/mcp-registry/blob/8c773729f13f036da8c909be503fe433923a9aa2/Taskfile.yml)
explicitly labels that command as generating a test catalog. Live GET of both
official catalogs on2026-09-10 found `longLived: true` for desktop-commander,
playwright, apify-mcp-server, inspektor-gadget and schemacrawler-ai.

| Published artifact | Entries | Remote entries | SHA256 |
|---|---:|---:|---|
| [v2](https://desktop.docker.com/mcp/catalog/v2/catalog.yaml) |270|30|`fc371f25332f1509983734c642c92b6319a0589e1c2b41edce2ad547675a9208`|
| [v3](https://desktop.docker.com/mcp/catalog/v3/catalog.yaml) |317|77|`274afe7ad34b083c3d3140664a3bc8762246f3887e840a9b4d4a3c44fce3b80a`|

Support was merged in [Gateway PR26](https://github.com/docker/mcp-gateway/pull/26).
The exact production transformation was not traced, and no v8std published
entry/default end-user session was tested. Requiring an upstream generator fix
before submitting an entry or releasing the image was an unsupported inference.
The user chose image-only publication; no upstream PR/Catalog submission occurred.
The implementation plan now separates this future channel gate from release.

### Planning handoff: first migration and remaining implementation

The planned first-migration stop/start is bounded to two hours if old/new
cannot coexist. The actual window must be separately authorized. This does not extend
loader/transaction deadlines, authorize stopping production now, or prove enough
memory for the new runtime alone. Normal automatic rollout still requires overlap.

Task5 owner paused safely on request for this planning turn; no new commits or
owned diagnostics remain. Last29 release tests passed in60.515s; earlier2 hold
tests passed before subsequent edits. The89-test snapshot/runtime run had3 failures;
the owner reports fixes, but verification has not been rerun. Security/ingress
review, Docker/nginx checks, regressions, activation runbook/report and independent
Task5 review remain. The working ordinary controller requires an existing
container `active.json`; initial Python-to-container bootstrap is a separate
unfinished slice, now explicit in the plan. No successful release is inferred.

See [the remaining-work roadmap](mcp-first-container-release-roadmap.md) for
local gates, external source/image publication, initial window, rollback reserve
and conditional activation of subsequent automated runtime updates.

### Ordinary release controller: reviewed local evidence, 2026-09-15

The user resumed the saved plan. Signed commits `1d04817a94eb087aacff2c46e43a14a93386946a`
and `5ae7588f5417deddc7af1ffc9f273d0b1dcba5af` implement the ordinary controller,
private generation hold and bounded independent index publication. A separate
review found five defects in control permissions, same-token acknowledgement,
interrupted accepted recovery, publication finalization and rejected-ID identity.
All five have RED/GREEN regressions and passed scoped re-review; no new blocking
finding remained. First-bootstrap is not yet implemented at this checkpoint.

Final commands/results:

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_release tests.test_v8std_mcp_release_hold tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_runtime -v
V8STD_TASK5_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_release_docker -v
```

148 focused tests/154.042s and one Docker/nginx integration test/9.992s passed.
The latter uses actual root-owned control under umask0077, read-only access by
UID10001 runtime, revocation/reacknowledgement, nginx syntax/invalid-switch,
static GET/HEAD/hash/cache headers while runtime is stopped, and download admission.
Eight same-NAT transfers through two nginx workers produced two200 and six429
with retry guidance. This small fixture is not a full mixed-load capacity proof.

The Docker test reuses local runtime index
`sha256:bec25fa5b9f240225db206c5e21d35a8c28e2d4ae30b1b878d272eacd9df1031`
with three current modules overlaid read-only, and pinned nginx
`sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c`.
It does not claim a newly built or published release. Native local Linuxarm64
host has14CPUs/8318976000bytesRAM; runtime limit512MiB and nginx128MiB,1CPU each.
The temporary root writer has networknone/read-only/cap-drop/no-new-privileges,
no socket and access only to its test-owned volume. All task-owned diagnostic
processes/containers/volumes/networks were removed; existing images and unrelated
containers were preserved.

Publication status now acknowledges the exact publication/reference ID, sequence,
action and identities. Archive HTTP200 alone is insufficient. Static publication
and runtime activation have separate host flags; disabling runtime updates does
not cancel owed recovery. The activation runbook records exact bounded CLI forms.
Normal recovery retains300s total/90s readiness/30s smoke/45s stop; the loader's
360s/20s budgets are unchanged. Native SSH/sudo/systemd installation, positive
published-artifact provenance, external TLS/index delivery and target capacity
still require their separately authorized acceptance.

The existing Starlette warning was traced without suppression: unchanged
`tests/test_v8std_mcp_snippet.py:23` imports `starlette.testclient`, whose
`httpx2` import falls back to `httpx` and warns. Runtime lock pins httpx0.28.1
and starlette1.3.1; those files did not change in this controller slice. This
is test-dependency debt for final integration, not pristine-output evidence.

Fresh read-only production preflight: legacy health and actual `/mcp` initialize
succeed; public snapshot manifest still404. Target-host prerequisites and
capacity remain unverified. No server operation or backup occurred. Local
actual legacy code from `b7bef11` proved that stale cache tries HTTP, whereas
restoring the same four verified cache files with fresh mtimes permits original-
configuration startup/search/three-resource reads without network. This informs
bootstrap tests; it is not an installed backup/restart or indefinite hold proof.

Ordinary architecture validation/impact and whitespace checks passed. No whole
repository suite, strict build, merge-ready, main merge/push, registry publish,
Catalog submission, server setup or production migration is claimed here.

### First migration: reviewed local implementation, 2026-09-15

Signed `fdb1d829ca9b9958ea2f3c716bafe68b7f33c58f` implements operator-only
bootstrap, a bounded hash-bound window, protected legacy restoration and an
independent recovery/boot guard. Separate review approved spec compliance and
scoped quality without Critical, Important or new Minor findings. Task5 is
complete locally, not the first live migration or whole-branch acceptance.

Verification sequence (overlapping suites are not independent coverage):

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_release tests.test_v8std_mcp_release_hold tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_runtime -v
.venv/bin/python -m unittest tests.test_v8std_mcp_release.BootstrapBoundaryTests tests.test_v8std_mcp_release.BootstrapProcessTests -v
V8STD_TASK5_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_release_docker.DockerReleaseTests.test_bootstrap_process_fault_matrix_in_restricted_linux -v
```

The first run passed182 tests in253.933s. Two subsequent bootstrap self-review
fixes close the legacy boot fence before restoration retry and make mid-copy
SIGKILL staging retryable. The amended bootstrap run passed36 tests in108.894s.
All36 cases then passed in restricted Linux containers: wrapper365.299s total,
five batches of8/8/8/8/4 cases, unittest times42.853/65.154/101.238/95.499/58.021s.
Each batch retained a240s test watchdog. Production300s transaction,90s readiness,
30s smoke,45s stop and loader360s/read20s are unchanged.

The existing local runtime image above was used with a read-only source mount
and historical code pinned to `b7bef11`; this is not a new release image build.
Each Linux batch had1CPU,768MiB memory/no extra swap,128PIDs,256MiB tmpfs,
networknone, UID10001, read-only/cap-dropALL/init/no-new-privileges. Real old/new
MCP processes, HTTP proxy, served identities and static requests were tested;
Docker/systemd/GitHub adapter effects were substituted where necessary.

Earlier failures are not erased: crash-surviving descendants held captured
stdout pipes open, so fixture capture now uses temporary files and controller
PID wait. Two unpartitioned Linux runs timed out at240s. The first batched run
then failed because a separate post-recovery health observer allowed only300ms
including Python startup; only that observer changed to2s, below production's
existing HTTP3s cap. The complete36-case Linux run covers the correction.
No production timeout was increased. The earlier combined two-test Docker run
remains failed; its nginx/hold/static test separately passed, repeating umask0077
control, same-token reack, invalid-switch restoration, static GET/HEAD after
runtime stop and two200/six429 downloads. Exact owned test resources were cleaned;
existing images and unrelated containers/services were preserved.

Acceptance is durable COMMITTED only after real local/public MCP smoke. Missing
active-pointer persistence then reconciles the accepted image; preacceptance
failure restores exact legacy source/config/cache. Tests cover SIGKILL around
side effects, caller loss, expired-window recovery, failed rollback/retry,
duplicates, capacity rejection and boot fencing. Full historical1423-page/
3281-vector startup/search/three-Resource reads retain the stale-mtime negative
control and zero-network fresh-cache restoration. Usage logs are not overwritten
or treated as corpus identity. Existing Starlette warning remains unsuppressed.

Historical requirement, superseded by the2026-09-15 retirement: Task6 was to
preserve monitoring because the then-current timer read the old unit and
flat usage log, while container launch does not yet supply new usage events.
This is an integration defect, not the deferred dashboard/OpenMetrics redesign.
The retained image-alt parser defect and warning triage remain final obligations.

Native protected backup/venv/interpreter restoration, boot ordering/return time,
single-runtime/overlap capacity, installed SSH/sudo policy, published-image
provenance and external TLS/index delivery remain prerequisites for the later
window. No window is scheduled; no host setup, main merge/push, registry publish,
CI activation,100k capacity or live migration is claimed.

### Task6 partial evidence and design pause, 2026-09-15

Task6 is **not complete**. At signed `7bf5291`, the confirmed retained dev-build
failure is repaired by explicitly including `requirements.txt` and
`requirements-mcp.txt` in the root Docker context. Actual BuildKit disproved an
earlier inspection-based claim that `hold.py` or dev scripts were excluded:
`!scripts/` already includes its descendants. Runtime COPY closure passed before
the change. Negative COPY probes for `.git/HEAD` and `spec/README.md` failed as
expected. This is not an exclusive per-script allowlist.

Two actual scratch COPY/export byte-comparison tests passed in0.477s. A fresh
runtime build/import/package test passed in243.864s, verifying Dockerfile COPY
bytes, server/hold imports, UID10001 and `pip check` under the restricted runtime
profile. Its all-zero `SOURCE_SHA` deliberately identifies a local fixture,
**not** a committed-source release candidate or a published artifact. No corpus
load, default-source activation or capacity conclusion follows from this test.

The local strict build passed with3282 vectors,1430 article checks and no article
HTML violations; all3 license texts were published locally. The subsequent full
suite passed628 tests in316.896s with6 opt-in Docker checks skipped. These results
predate the later test-harness-only review fixes; they do not establish Task6 or
whole-branch acceptance. Existing Starlette and ordinary pip build warnings were
not suppressed. No runtime dependencies were changed to hide them.

Scoped review of `203cbc0..7bf5291` approved the context correction but found two
Important defects in the new harness: surviving process-group descendants after
the Docker leader exits, and unverified daemon-container/image cleanup after a
runtime-client timeout. Their focused repair and re-review are required before
the slice can be considered complete.

Signed `08ab175c0c984929dc2bbb79fe031de936eaa47a` contains their test-only repair:
all three build paths use bounded group lifetime and file-backed capture;
named fixture containers and the exact image tag are removed and their absence
verified. Cleanup failure remains visible without replacing a primary timeout.
Six focused regressions passed in9.134s; the25-test module passed in9.184s with4
explicit opt-in skips. All3 actual Docker context/runtime checks then passed
in245.553s, using ordinary BuildKit cache and the same explicit fixture revision.
Post-run queries confirmed exact fixture removal; unrelated resources remained.
An intermediate new EPERM/ResourceWarning was reproduced by an added failing
regression and corrected before these final runs. It was not suppressed.
Independent scoped re-review of `7bf5291..08ab175` approved both fixes, with no
new Critical, Important or Minor findings. The reviewer checked the scenarios
and evidence against the fix diff without duplicating the test runs. This
completes only the context/harness repair slice, not Task6 or release acceptance.

Historical classification before retirement: preserving the existing
dashboard was required, but the approved package did not define how its
unprivileged reader obtains fresh live state from the root-owned container
controller. A durable COMMITTED receipt is not runtime liveness; the controller
unit being active is not MCP uptime; snapshot `loaded_at` is not process start.
The real monitor reader and controller-status probes reproduce these semantic
counterexamples even while the existing monitoring tests pass.

Under `v8std-architecture` failure recovery, implementation of this integration
and remaining Task6 work was paused for brainstorming and revised design/plan
approval. A bounded private atomic state file is a proposed approach, not an
implemented or accepted interface. Its producer/reader authority, identity,
freshness, error behavior and compatibility must be specified before code.
No Docker/sudo access was granted to the monitor and no public schema changed.

CI publication/classification, process-v2 integration, the retained image-alt
parser repair, committed-source candidate, mixed-load proof and final gates
remain outstanding. Production, registry, GitHub settings, `main` and the
unscheduled first-migration window were not changed by this work.

## Task6 continuation2026-09-15: retained parser finding closed

Public monitoring retirement is completed separately; see
[production retirement evidence](2026-09-15-public-monitoring-retirement.md).
The historical monitoring-preservation pause above is superseded: no dashboard,
sampler or private monitor-state bridge is being resumed. Persistent private
usage logging for the container remains a distinct Task6 gate.

Signed `034eb47268c0f2dfa3064dd06b761ed2dd397ca4` fixes the retained image-alt
defect in two files. The upstream image parser recursively parses alt children;
its instrumented HTML tags/link nodes incorrectly affected the parent document.
Collector isolation now leaves alt text alone and records the actual image
destination after child parsing. Actual code protection and canonical source
bytes/hashes remain unchanged.

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_presentation -v
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshot_format -v
```

TDD: baseline18 passed; added regressions produced12 expected assertion
failures across22 tests before the fix. Afterward presentation22/22 in0.066s
and snapshot35/35 in13.637s passed without warnings/skips. Cases include opening
and closing HTML-looking alt tags, alt attributes, unknown/unsafe following
targets, actual protected HTML, Unicode/NUL/CRLF offsets and source/hash parity.
Independent scoped review approved specification and quality with no findings.
Only this parser gate is complete; CI/process, private logging, final image/load
and whole-branch gates are not inferred from these focused tests. No publication,
push, main merge, production mutation or100000-agent capacity claim was made.

### Private runtime logging slice, 2026-09-15 (awaiting scoped review)

Implemented after signed `04a8e5c3ffe96eb34b5379c18919e26bf0b70f56`; code and
this evidence are committed together. Actual `HostAdapter.start` now provisions
the separate fixed host log (parent root:root0700, single-link regular
file10001:root0640), binds only that file RW, and supplies existing `--usage-log`.
Unsafe existing objects are rejected without rewriting history; start/reuse
profile checks do not change ownership-checked stop/recovery. Legacy history,
backup exclusions and its rotation stanza are unchanged. Direct image logging
defaults, logger/schema, CI, parser and retired monitoring were not changed.

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_logging tests.test_v8std_mcp_release tests.test_v8std_mcp_server tests.test_v8std_mcp_logging_docker.LoggingFixtureCleanupTests -v
V8STD_TASK6_LOGGING_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_logging_docker -v
```

TDD: actual-launcher RED15 assertion failures; native preparation/refusal
RED13; real rotation RED (four new MCP events remained unrotated); scoped
cleanup-failure RED1. All went GREEN after their corresponding fixes. Focused
regression run118 tests207.715s:114 passed,4 Linux-only skips on macOS. Final
opt-in run3 tests17.520s passed, including a nested native4/4 in0.003s with no
skips. Also checked ordinary architecture validation and slice impact; final
merge gates/review are not inferred from these checks.

Docker29.7.2, Linux7.0.12-linuxkit arm64; actual logrotate3.22.0 and gzip
exercised both unchanged legacy and separate new root/copytruncate stanzas.
Native UMask0077 creation/reuse and hostile file/parent cases use real launcher
code and real uid/file permissions, without a passwd entry for10001. Actual
launcher argv was executed with fixture-only image/path translation and
read-only runtime script overlays. Two non-root read-only/cap-drop containers
each used512MiB,1CPU,128pids,64MiB tmpfs,refresh0; no Docker socket or privileged
runtime. Five actual health/initialize/search/successful-page checkpoints span
old/candidate start, rotation, candidate restart and return to old. Four events
remain in the gzip archive, six subsequent events in the current log, and the
legacy event remains separately archived; inode/owner/mode are preserved.

Final fixture `v8std-task6-logging-eeb6033e246f4ca5` used the retained regression
image `sha256:bec25fa5b9f240225db206c5e21d35a8c28e2d4ae30b1b878d272eacd9df1031`,
whose observed runtime SHA remains `f5c45d23fc31285e96920719285b0a9253e4a6fe`.
This is not a new release artifact or exact-source candidate build. Corpus is
the independent synthetic one-page fixture, not a mixed-load capacity corpus.
No p95/memory/admission/100000-agent claim is made.

Earlier fixture health failures were not product RED: an internal Docker
network did not publish the loopback port despite ready native health. A helper
DNS-name attempt also failed MCP's existing host profile. The final fixture
uses its own ordinary bridge and the unmodified launcher loopback port, with
no new client/security exception. All named containers, volume, network and
helper image tags were removed and absence checked; unrelated
containers were preserved. Cleanup failures are reported without hiding the
primary test error and do not skip other owned cleanup attempts. Normal build
cache and pre-existing regression images were not pruned.

This proves bounded logging lifecycle and actual forced rotation, not complete
controller attestation, native systemd/nginx rollback, host installation/daily
scheduling or public-default image provenance. Best-effort JSONL and the known
copytruncate loss window remain explicit. Existing Starlette/pip warning history
was not suppressed or fixed; no such warning was emitted by the final focused
run. Scoped review, CI/process, final integrated build/full suite/image/load and
external activation gates remain separate. No Task6/review checkbox is closed.

### Logging review FIX1 — controlled event inventory, 2026-09-15

The scoped logging review approved ee4a5aa with no Critical/Important findings;
this resolves its Minor test-evidence gap. Only the lifecycle test assertions
change: exact tool histograms require2 search +2 page events before rotation
(the existing archive equality preserves those four), and3 search +3 page
events in the final current file. Existing marker/inode/archive checks remain.
This does not promise exactly-once logging under concurrent rotation.

Native mutation evidence: the old assertions passed17.501s with page events
removed before rotation (only2 archived events) and a duplicate search appended
afterward (7 current events). New assertions reject missing pages in10.852s
and the final duplicate independently in16.139s. Mutations touched only the
synthetic file in the exact owned helper; no production code/helper was changed.
An initial stdin-launched probe failed34.860s before assertions because spawn
could not load `<stdin>`; corrected to `python -c`, not counted as product RED.

```sh
V8STD_TASK6_LOGGING_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_logging_docker.LoggingDockerTests.test_native_mcp_restart_rollback_and_both_logrotate_stanzas -v
```

Unmodified native lifecycle:1 test16.853s **OK**, no skips/warnings. Exact4/6
event inventories, MCP responses, actual logrotate and prior lifecycle checks
passed. Last fixture `v8std-task6-logging-eb971cce81a64287`; all owned containers,
volume, network and helper tags were removed and absence checked. Unrelated
containers remain running; no global Docker cleanup. No full suite,
CI, process/plan, runtime/logger or rotation-policy changes were made in FIX1.

Independent logging re-review approved FIX1 at ea786b2: exact inventories and
mutation evidence address the sole Minor finding; no new breakage. The bounded
private-operations gate is complete. Separate production410/no-store evidence
is in `2026-09-15-public-monitoring-retirement.md`; it is not a claim that this
new logger has been installed there. Full controller/systemd/nginx acceptance,
final exact-source artifact/load checks and external activation remain distinct.
