# Tools-only local candidate verification

Executed 2026-09-16 (Europe/Moscow), on an arm64 Mac with Docker Desktop
linux/aarch64. This is local candidate evidence for the approved tools-only
design. It does not claim amd64 verification, production capacity, publication,
deployment, or completion of the older container/CI plans.

## Source and artifacts

Base: `dd5898244cd48ad1f10893d22fc618953c9e2156`.
Code was committed **before** building images:
`c4c0878a3c5e12323358f139e070253bd9e8ac5a`
(`test(mcp): verify tools-only container and load acceptance`).
Branch: `codex/mcp-container-distribution-design`, original checkout.
This operation report is a subsequent evidence-only change.

| Artifact | Local tag | Inspected image ID |
|---|---|---|
| MCP | `v8std-tools-only-mcp:c4c0878` | `sha256:5dcb8e1b92ee7e6375981b91b6a206918540aad75e93b2be809c9cabe2b612ef` |
| Site | `v8std-tools-only-site:c4c0878` | `sha256:3554824dcda8cc99ff57d6371c5fab186e00e21a93860eb88c75ac43d4ada4d2` |

Both images: `linux/arm64`, configured user `10001:10001`, OCI revision exactly
the code SHA above. Every Dockerfile.mcp COPY input (16 files, including lock,
runtime sources, retrieval rules and licenses) was read from the image and
SHA256-compared with `git show <code-sha>:<path>` and the checkout. All matched.
The source-proof container used network none, read-only rootfs, dropped all
capabilities, no-new-privileges and no mounts; it exited and was removed.

Committed input identities from `publish_mcp_artifacts.input_identities`:

- Runtime: `9f580a029745e00395e4a49b1e79c9f1d4ee0f9f6c583d614f5ac02abfa1e35a`.
- Corpus: `021a01ae0e5c06eac49f1625c9a3b06b5e3619535f9f1f1216f3059e49a14f08`.

Both match `aa124faedd482c0bca105f87ea0437ba0e72cc1e`. Consequently the parent's
fresh canonical tree `/tmp/v8std-tools-only-corpus.MdTmMw` was reused without
repeating its preparation. Its source was mounted read-only. The retained old
site `601ee3a` had corpus identity
`a9aa5a82c850f5cd4a0830b680c28047a3959f91b17d68b19992de9cacd97ef8`; it was not used.

Pinned builder `v8std-final-ci:108b91f`, image ID
`sha256:cffef3a1b208b462e5f2ca4b9266b1d6ca2c99e031d0170b2c04f1398583a722`, was reused
only after checking Dockerfile.ci/requirements-build.lock equality. Local site
build ran network none, user 501:20, and completed with `No issues found` in
11.85 seconds. This isolated local build does not replace the parent's final
checkout strict build.

The fresh site's verified five-file snapshot has 1423 pages, source SHA equal
to the code SHA, corpus ID
`8344fb35dd182da20962a69c14e0fa78b9b51a5ec4965a8adc9768eb0146658f`, archive SHA256
`d5ffd4b6e214be8de1fe193a0e729cbde78a8789194d67c0a637bf22d8577006`.

## Commands and retained evidence

All commands ran from the repository root.
Local logs, raw profile and fixture/source-proof program are retained in
`/tmp/v8std-tools-only-task3.xuV330/`. They are local temporary evidence, not
published artifacts; key results are recorded here durably.

```sh
docker buildx build --platform linux/arm64 --build-arg SOURCE_SHA=c4c0878a3c5e12323358f139e070253bd9e8ac5a --load -f Dockerfile.mcp -t v8std-tools-only-mcp:c4c0878 .

docker run --rm --name v8std-task3-local-site-xuV330 --platform linux/arm64 --network none --user 501:20 --cap-drop ALL --security-opt no-new-privileges --mount type=bind,source=/tmp/v8std-tools-only-corpus.MdTmMw,target=/docs,readonly --mount type=bind,source=/tmp/v8std-tools-only-task3.xuV330,target=/output --entrypoint python v8std-final-ci:108b91f scripts/build_local_site.py --root /docs --output /output/local-site --site-url http://v8std.localhost:18765/ --source-sha c4c0878a3c5e12323358f139e070253bd9e8ac5a

docker buildx build --platform linux/arm64 --build-arg SOURCE_SHA=c4c0878a3c5e12323358f139e070253bd9e8ac5a --build-context local-site=/tmp/v8std-tools-only-task3.xuV330/local-site --load -f Dockerfile.site -t v8std-tools-only-site:c4c0878 .

/tmp/v8std-final-gates.e7aqas/venv/bin/python /tmp/v8std-tools-only-task3.xuV330/prove_candidate.py image
/tmp/v8std-final-gates.e7aqas/venv/bin/python /tmp/v8std-tools-only-task3.xuV330/prove_candidate.py fixtures

/tmp/v8std-final-gates.e7aqas/venv/bin/python scripts/check_mcp_container.py --mcp-image v8std-tools-only-mcp:c4c0878 --site-image v8std-tools-only-site:c4c0878 --platform linux/arm64 --chrome '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' --node /opt/homebrew/bin/node --host-gateway

/tmp/v8std-final-gates.e7aqas/venv/bin/python scripts/check_mcp_load.py --mcp-image v8std-tools-only-mcp:c4c0878 --site-image v8std-tools-only-site:c4c0878 --source-sha c4c0878a3c5e12323358f139e070253bd9e8ac5a --snapshot /tmp/v8std-tools-only-task3.xuV330/synthetic-A --refresh-snapshot /tmp/v8std-tools-only-task3.xuV330/synthetic-B --output /tmp/v8std-tools-only-task3.xuV330/load.json --seconds 60 --clients 8 --idle 64 --burst 600
```

Both checkers' current `--help` was consulted. All build/proof/acceptance
commands above exited 0. Logs: `mcp-build.log`, `local-site-build.log`,
`site-image-build.log`, `image-proof.json`, `fixture-proof.json`, `container.log`,
`load.log`, `load.json`.

## Container and lifecycle proof

All five tools returned real data: search, page, related, snippet, diagnostics.
Direct catalog contained exactly these five; Gateway's aggregate catalog was
checked separately. All four direct sessions completed canonical initialize /
initialized lifecycle; HTTP sent negotiated protocol headers and required JSON.
Resources capability was absent. `/version` reported `api: v2` and only
`legacy-tools`.

Each cold/warm stdio and online/warm-offline HTTP session rejected 14 probes:
list, templates/list, and read/subscribe/unsubscribe for the three former URIs
and an unknown URI. Total **56/56**, semantic `-32601`, matching typed IDs,
JSON-RPC 2.0, no result/data payload, bounded error text. No literal SDK message
is a release condition.

| Readiness | Seconds |
|---|---:|
| stdio cold online | 3.84 |
| stdio warm network none | 2.85 |
| HTTP cold online | 4.33 |
| HTTP warm network none | 7.91 |

Cache origin: fresh verified old-format five-file archive downloaded from the
new local site, stored in an owned persistent volume under the unchanged URL
namespace; reused with network none. UID10001 and file sizes/mtimes stayed
equal across offline restarts. stdio EOF=0, stdio SIGTERM=0, cold/online/warm
HTTP SIGTERM=143 (accepted bounded shutdown). Snippet maxLength=4000 and
configured 32000-character tail-signal check passed. Static archive hash,
immutable versus manifest cache headers, missing archive 404 and license bytes
were verified. Thin runtime dependency graph and non-root isolation passed.

Installed Chrome with Node 22.22.0 observed 18 local requests, no blocked
foreign-origin requests and no bad HTTP responses. Installed host Gateway
v0.43.3 passed two independent long-lived warm-cache sessions, network none,
same server IDs on repeated calls. Native Gateway used init, UID10001,
no-new-privileges, no privilege escalation/socket/bind mounts and exactly one
owned named cache. Native Gateway did **not** provide optional read-only rootfs
or cap-drop; the report records these accurately, without equating its profile
to the stricter direct container profile.

## Controlled content refresh

Both explicitly synthetic archives retain the fresh site's 1423 pages and
3283 vector rows. The `std437` body is 6834 characters; a literal A/B marker is
at character zero, followed by the real standard text with explicit local
fixture links. Existing `page_chunks` and `mcp_snapshot_fixtures` helpers update
the matching vector text hashes and archive metadata; vector values are copied
from the original vectors, not re-embedded for this synthetic change. `verify_archive` accepts
both archives without altered limits. The 12000-character tool default remains.

Expected hashes come directly from these explicit bodies in the verified
archives. Runtime presentation/response-hash code does not compute them.
The checker fetched std437 with `v8std_get_page` before and after refresh:

| Fixture | Expected and observed page body SHA256 |
|---|---|
| A | `ab6ca64c23bebcf6b2c6473e9c0fa5749c875275f0e3591732af863e13995355` |
| B | `30274f9d84505e7b2afa436e7e60e3ae67d702bdfd45bbfc00ad8147de647c8f` |

A corpus: `1ac864feb02fce7be00fe8f01b03bdb429cb3fe9774931f5597e7c68417cd49d`;
archive: `4ab72de8ed91a2d2fea83334a2c095315909881bd7344a8b36cab24fb421042b`.
B corpus: `8ef29c1e616e876f9f2df54d7d093ffed3be8ee73a59913c1e84ba9f51ab8ad1`;
archive: `4700fc0979c95ed19f7f690a3ada79e382b83029afa803ff4496f54d2bd96b44`.
An identity-only change cannot satisfy the distinct body-hash gate.

## Mixed load, private logs and resource samples

Configured 60 seconds, 8 active clients, 64 maintained idle connections, burst
600. Measured duration including final sampling: 62.349251s. Maximum inflight
tool calls=8, final idle=64, idle reconnections=64, connection-close requests=216.
Manifest switched at 20.006s; nginx validated/reloaded to the second process
of the **same image** at 40.113s. Final health showed B corpus and exact runtime
SHA. This is a local HTTP switch, not the production release controller.

| Traffic | Success/requests | Unexpected errors | Retryable 429/503 | Success p95 / p99, ms | Successful RPS |
|---|---:|---:|---:|---:|---:|
| Tool data | 2383/2383 | 0 | 0 | 224.968 / 267.050 | 38.220 |
| Static archives | 522/522 | 0 | 0 | 20.623 / 64.870 | 8.372 |
| Discovery initialize burst | 600/600 | 0 | 0 | 900.580 / 1416.372 | 212.579 |

All statuses were 200. Tool successes by kind: search 836, page 595, snippet
357, diagnostics 240, related 355. The retained 20-slot mix is 7/5/3/2/3.
Separate initialized lifecycle and **28/28 rejected Resource probes** are not
part of tool throughput or latency; their unexpected errors=0. No successful
resource throughput is reported. Static downloads transferred 1,497,498,462
bytes; tool responses transferred 39,741,833 bytes. No SSE reply was accepted.

Limits stayed unchanged: each runtime 1536 MiB/2 CPU; static site 128 MiB/0.5
CPU; edge 128 MiB/1 CPU; owned log preparer 64 MiB/0.25 CPU. There were 19 samples
with Docker CPU/RAM stats and runtime cgroups/FD counts. Final cgroup peaks:

| Runtime | Memory peak, bytes | Max sampled current, bytes | Max sampled FDs | CPU usage, seconds | Throttled periods / seconds |
|---|---:|---:|---:|---:|---:|
| A | 425779200 | 353943552 | 38 | 57.389795 | 22 / 0.336411 |
| B | 424804352 | 364756992 | 37 | 36.958490 | 1 / 0.001735 |

No memory max/OOM/oom_kill events or Docker OOMKilled. Private usage log:
307204 bytes, uid=10001, gid=0, mode=0640; counts search=836, page=597 (including
the two hash probes), related=355, snippet=357, diagnostics=240. Resource
denials did not become successful tool log events. The bounded root preparer
had only CHOWN on its own new log volume; runtimes received one log file bind,
no Docker socket or privileged mode.

## Tests, RED to GREEN and limitations

Pinned Python `/tmp/v8std-final-gates.e7aqas/venv/bin/python`, MCP 1.27.0;
project `.venv` unchanged. RED before implementation:

```text
python -m unittest tests.test_v8std_mcp_distribution.AcceptanceHelperTests tests.test_v8std_mcp_load -v
Ran 18 tests in 1.026s
FAILED (failures=11, errors=1)
```

Failures caught obsolete resource mix/bulk hash, SSE and wrong typed ID counted
as successes, related rejected, missing stdio error path and resource content
accepted. The error was the existing helper indexing `result` on the actual
tools-only `resources/list` error envelope. Benchmark RED independently reached
`AttributeError: 'SnapshotIndex' object has no attribute 'read_resource_text'`.

Focused GREEN, exit 0 (`focused-green.log`):

```text
python -m unittest tests.test_v8std_mcp_distribution tests.test_v8std_mcp_load tests.test_v8std_mcp_tools_only -v
Ran 49 tests in 13.704s
OK (skipped=5)
```

44 passed, five opt-in skips: three image-context checks, local-build check and
pinned-builder check. These skips remain skips; the actual candidate build,
16-file equality and fresh-site proof above are separate evidence.
`python -m tests.mcp_runtime_benchmark` subsequently exited 0: all 256 ranked
cases, identical ranks/scores and all cold/warm/same-hash/new/slow phases passed;
MRR=0.9939759036144579 both sides, p95 45.438/51.237ms. Actual page/snippet checks
and per-case ranking bounds were retained; all five retained tools returned
data. Peak observed process-tree RSS=649953280 bytes. No comparative performance
claim is made: focused tests and this diagnostic benchmark overlapped in time.

Semantic self-review found the intended API-governed acceptance change only;
no design contradiction, snapshot format change, producer change or new
authority was needed. Final branch impact/merge-ready, declared fitness, strict
checkout build, full suite and independent review belong to the parent.
No new branch/worktree/PR, merge, push, publication or production action occurred.
Unperformed: amd64, production/TLS/capacity, containerized Gateway network
topology, explicit alternate-source/default-404 profile. They are incomplete,
not passes, and are not substituted for the completed native local profile.

## Cleanup

Container project: `v8std-task4-3b55959628`.
Load ownership label: `pro.v8std.load=v8std-load-993d53085aad4906`.
Both checks exited 0. Exact owned containers, networks, caches and private log
volume were removed; the load harness verified each removal. Independent
post-check inventories returned no matching resources or Gateway servers.
Browser/catalog/source temporary directories were cleaned by their owners.
Pre-existing unrelated containers retained their original IDs and
uptimes. Only new local image tags and the dedicated evidence directory remain
intentionally available for review; no unrelated image/cache/container was pruned.

## Controller final gates — 2026-09-16

The three implementation tasks passed independent spec/quality review. The
release-smoke review found an unsupported literal SDK error-message comparison;
commit `9f812d8` replaced it with semantic code/identity/payload/size checks,
13 covering tests passed, and scoped re-review accepted the fix. Historical
`legacy_check` remains unchanged because it verifies the pinned old runtime.
Adding that distinct release-smoke task closed an omission in the initial
plan: the old acceptance would reject every valid tools-only release.

Task 3 has one deferred nonblocking coverage improvement: the mixed profile
checks B's page body after nginx switches processes. It therefore proves
endpoint content changed, not independently that process A refreshed before
the switch. A bounded pre-switch page probe would separate those observations.
Task 1 separately covers actual in-process successful/corrupt refresh. Carry
this limitation into the eventual whole-branch integration review.

Final checkout strict build used the pinned builder, network none and host
UID/GID, then exited 0: 3283 vectors, build 15.42s, 1430 articles with zero
violations, 1049 sitemap additions with zero duplicates, three license texts.
The full suite ran afterwards, with no concurrent generation:

```sh
docker run --rm --name v8std-tools-only-final-strict-20260916 --network none --user 501:20 -v "$PWD:/docs" v8std-final-ci:108b91f build --strict
V8STD_MONITORING_RETIREMENT_DOCKER=1 /tmp/v8std-final-gates.e7aqas/venv/bin/python -m unittest discover -s tests -v
```

Tested HEAD: `1786e5122b2d705ac1b9487d29ff4e406d7518af`. Exact final summary:

```text
Ran 727 tests in 362.665s
OK (skipped=13)
```

714 passed, zero failures/errors/warnings. The 13 skips are five opt-in
builder/image tests, four native-root logging cases, two native logging-Docker
cases and two release-Docker cases. They are not passes; the fresh image and
native container/load evidence above is separate. All four real nginx
monitoring-retirement tests passed. The complete suite includes every module
declared by API 4.0, snapshot 1.1 and the tools-only invariant; the only skips
among those modules are the five explicitly opt-in distribution cases.

CLI impact was run both for this implementation range and against main.
Ordinary architecture validation against main and both scoped/main diff checks
passed. The manual seven-question recheck confirms the approved breaking
Resource boundary and compatible snapshot clarification; no new design
contradiction, tool callback/transport setting or corpus-producer change.
Frozen structured documents from main remain unchanged.

After completing this plan, `validate --merge-ready --base-ref main` exits 1
with exactly the two pre-existing incomplete plans:

```text
INCOMPLETE_PLAN spec/plans/2026-09-10-mcp-ci-deployment-policy-plan.md: plan is not complete
INCOMPLETE_PLAN spec/plans/2026-09-10-mcp-container-distribution-plan.md: plan is not complete
```

Those plans and their outstanding CI/publication findings are not marked done.
This is completed tools-only implementation and local verification, not a
whole-branch approval. Broad integration review/merge remain blocked by that
earlier work. No main merge, push, image publication or production deployment.
The plan-owned review workspace is preserved for continuation, not deleted.

Parent logs: `/tmp/v8std-tools-only-gates.bdZxkK/strict-build.log`,
`full-suite.log`, `impact-tools-only.log`, `impact-main.log`, `merge-ready.log`.
Final running-container inventory contains only the pre-existing unrelated
containers; the strict-builder and monitoring test fixtures were cleaned up.
