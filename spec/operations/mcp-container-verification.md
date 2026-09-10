# MCP container delivery — verification record

This is implementation evidence, not authorization to publish or activate a host.
The accepted design and contracts remain authoritative. Unfinished or external
checks below must not be reported as passed.

## Scope and baseline

- Main baseline: `b7bef11e145a188b30e7a7b17df2be4cb1acbd0c`.
- Approved design package: `537fe79`; implementation plan: `a3b2474`, with later
  recorded interface refinements on the same feature branch.
- Working branch: `codex/mcp-container-distribution-design`, primary checkout.
- No live host changes, image publication, Catalog submission, PR closure or
  production activation are established by this record.
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

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshot_format tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_presentation tests.test_v8std_mcp_runtime tests.test_v8std_mcp_index tests.test_v8std_mcp_snippet tests.test_v8std_mcp_server tests.test_v8std_mcp_combined tests.test_v8std_mcp_capacity tests.test_v8std_mcp_monitoring
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

Implementation is paused at the architecture failure-recovery gate for revised
written design/scope approval. Task4 remains incomplete; release controller and
CI Tasks5/6 have not started. Keeping full direct/Compose/production hardening
and making Gateway a separately accepted channel is a proposal, not an approved
contract change. The60s runtime bound remains unchanged, and amd64 acceptance
is not claimed. Do not merge, publish or close PR33 from this partial result.

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
| Runtime/static-site images, local request graph, Gateway sessions | Arm64/local profile and warm host Gateway pass; review requires Compose fix and explicit Gateway/gate design resolution; amd64 acceptance remains open. |
| Restricted host controller, rollback and independent index delivery | Pending. |
| Fail-closed publication, process v2 synchronization | Pending. |
| Final semantic impact, merge-ready, fitness, strict build and full suite | Pending after all changes; strict build precedes the suite. |
| Final image smoke, refresh RSS/CPU, disposable mixed load | Pending; cannot establish production 100k capacity. |

## External acceptance boundary

Registry release digests, provenance verification against those releases,
Docker Catalog acceptance, GitHub protection/environment/secrets, target-host
prerequisites and initial controlled activation require separate evidence.
The existing Python deployment remains the initial rollback path until that
activation is explicitly performed and verified. An automatically enabled
release path must not be inferred from a locally passing test or a written
workflow.
