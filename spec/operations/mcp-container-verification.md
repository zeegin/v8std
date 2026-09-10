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
| Bounded refresh/cache, crashes, shared volume, offline recovery | In progress; not yet accepted. |
| Frozen generations, URL presentation, stdio/HTTP lifecycle | Pending. |
| Runtime/static-site images, local request graph, Gateway sessions | Pending. |
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
