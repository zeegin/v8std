---
schema_version: 1
kind: plan
id: mcp-container-distribution
design: design:mcp-container-distribution
implements:
  - adr:MCP_PUBLISHED_COMBINED_RUNTIME
  - adr:MCP_ATOMIC_SITE_SNAPSHOTS
  - contract:MCP_API@2.4
  - contract:MCP_CORPUS_SNAPSHOT@1.0
  - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
requirements:
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_RUNTIME_AND_CORPUS_RELEASE_INDEPENDENTLY
  - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
  - MCP_SNAPSHOT_LOAD_IS_ATOMIC
  - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
  - MCP_SNAPSHOT_IO_IS_BOUNDED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
  - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
  - MCP_RELEASE_SWITCH_IS_REVERSIBLE
  - MCP_SHARED_HOST_LOAD_IS_MEASURED
  - MCP_OFFLINE_USES_VERIFIED_CACHE
  - MCP_DISTRIBUTION_PROVENANCE_IS_VERIFIABLE
---

# MCP Container Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать единый контейнерный MCP с безопасной доставкой corpus и проверяемой автоматической поставкой, не активируя production в ходе локальной разработки.

**Architecture:** Подготовленный snapshot загружается фоном в отдельное поколение индекса. Запрос удерживает готовое поколение, а ссылки преобразуются только на границе ответа. Один опубликованный runtime image используется всеми каналами; отдельный статический сайт и host-controller обеспечивают локальную установку и обратимый rollout.

**Tech Stack:** Python 3.12+, существующий mcp==1.27.0/FastMCP, unittest, Docker/Compose, nginx, GitHub Actions. Формат snapshot — deterministic tar.gz, SHA-256, JSON/JSONL.

**Spec:** [Продуктовый design](../designs/2026-09-10-mcp-container-distribution-design.md), [процессный design](../designs/2026-09-10-mcp-ci-deployment-policy-design.md), [snapshot contract](../contracts/mcp-corpus-snapshot-v1-r0.md), [API contract](../contracts/mcp-api-v2-r4.md), [distribution contract](../contracts/mcp-distribution-v1-r0.md), [release contract](../contracts/mcp-release-runtime-v1-r0.md).

## Global Constraints

- Один `/mcp`, пять существующих tools, три существующих bulk Resources; никакого `/v3/mcp` или нового bulk discovery.
- Единственная публичная настройка — `V8STD_MCP_SITE_URL`, по умолчанию `https://v8std.ru/`; CLI `--site-url` имеет приоритет. Второй public-base URL не вводится.
- Snapshot schema major 1, model `v8std-hash-embeddings-v1`, dim 256; допустимые размеры/схемы/URL определены snapshot contract и не ослабляются ради fixture.
- Snippet: 4000 default, 32000 maximum; query 500, preview 1000, tokens 80 и суммарно 4000; один hybrid search, прежний ranking и отсутствие raw procedure в usage logs.
- Tool/resource request не скачивает данные и не ждёт refresh; одновременно видит одно валидное поколение.
- Один multi-platform image на версию, `linux/amd64` и `linux/arm64`; catalog review может отставать, но не создаёт другую сборку той же версии.
- Local site и MCP не делают background public egress. Cold-offline thin image без cache не готов; warm-offline с проверенным cache работает.
- Основной checkout, существующая ветка `codex/mcp-container-distribution-design`; не создавать worktree, не менять main, не пушить и не деплоить во время реализации.
- TDD и focused tests для каждого поведения. Strict build выполняется **до** полного suite: tests читают `site/LICENSES`, параллельная пересборка разрушает их вход.
- Утверждение о 100 000 подключений запрещено без production-like mixed-load evidence.

## Scope and acceptance boundaries

Это один связанный release-пакет с шестью проверяемыми задачами в трёх блоках:
corpus/runtime (1–3), container distribution (4), delivery (5–6). Их interfaces
зафиксированы ниже. Запуск CI, registry publication, production setup/cleanup,
первичный rollout и внешний Docker Catalog PR — последующие операции интеграции,
не checkboxes этого plan.

`implements` намеренно не включает весь design, distribution/release contracts
и инварианты, требующие внешнего artifact/digest/host evidence. Эти артефакты
остаются принятым намерением до отдельного evidence-backed plan. Завершение
кода release-controller само по себе не доказывает rollout на целевом сервере или 100k.
Процессная реализация получает отдельный process plan, чтобы product plan
не объявлял Git policy продуктовым инвариантом.

## File ownership and interfaces

| Task | Write scope | Responsibility |
|---|---|---|
| 1 | `scripts/v8std_mcp_snapshot_format.py`, `scripts/generate_mcp_snapshot.py`, `tests/test_v8std_mcp_snapshot_format.py`, `tests/mcp_snapshot_fixtures.py` | Pure format validation, deterministic producer; no network/index refresh. |
| 2 | `scripts/v8std_mcp_snapshots.py`, `tests/test_v8std_mcp_snapshots.py` | URL trust boundary, HTTP/cache transaction, background coordinator. |
| 3 | `scripts/v8std_mcp_runtime.py`, `scripts/v8std_mcp_presentation.py`, `scripts/v8std_mcp_index.py`, `scripts/v8std_mcp_server.py`, runtime tests | Frozen generation construction, request facade, stdio/HTTP lifecycle. |
| 4 | Dockerfiles/Compose/lock, local-profile script, tests, docs | Build and exercise the two images and local site. |
| 5 | `deploy/container/`, `scripts/v8std_mcp_release.py`, `tests/test_v8std_mcp_release.py` | Typed host transaction, nginx index store and recovery. |
| 6 | workflows, publication scripts, architecture policy/test references, docs/operations | Fail-closed CI delivery, process v2 synchronization, integration evidence. |

### Task 1: Deterministic corpus format and producer

**Files:** create format/producer/fixture/test files listed in ownership table.
Read the full snapshot contract and existing `generate_search_vectors.py`;
do not change the ranking or introduce a runtime dependency on docs builders.

**Interfaces produced:**

```python
class SnapshotError(ValueError):
    # str(error) is a bounded stable category, never untrusted payload.
    code: str

@dataclass(frozen=True)
class VerifiedSnapshot:
    metadata: dict
    files: dict[str, bytes]
    archive_sha256: str

def normalize_site_url(value: str) -> str: ...
def validate_manifest(payload: bytes) -> dict: ...
def verify_archive(payload: bytes, manifest: dict) -> VerifiedSnapshot: ...
def build_snapshot(docs_dir: Path, source_sha: str, canonical_site_url: str) -> tuple[bytes, dict]: ...
def publish_snapshot(docs_dir: Path, output_dir: Path, source_sha: str,
                     canonical_site_url: str, *, public_delivery: bool = False) -> Path: ...
```

The ellipses above describe signatures, not implementation steps. Keep format
validation in one module so network/cache code reuses exactly the same checks.
Producer converts canonical page URLs into additional `site_path`/`markdown_path`
without rewriting canonical body text; generated vectors and text hashes remain
valid. Site-level generator outputs currently consumed elsewhere stay intact.

- [ ] **RED:** Add behavior tests with hand-authored one-page docs and independently
  constructed hostile tar members. The first test asserts the producer module
  exists using `importlib.util.find_spec`, then execute the producer twice and
  require exact archive byte equality. Example expected path is literal:

```python
self.assertEqual(page["site_path"], "std/437/")
self.assertEqual(page["markdown_path"], "std/437.md")
self.assertEqual(verified.metadata["vector_dim"], 256)
with self.assertRaisesRegex(SnapshotError, "archive_member"):
    verify_archive(archive_with_symlink, matching_manifest)
```

  Run `.venv/bin/python -m unittest tests.test_v8std_mcp_snapshot_format -v`;
  missing implementation must fail before production code is written.
- [ ] **GREEN format:** Implement strict JSON with duplicate-key/depth/type
  guards; exact five regular members; deterministic gzip/tar; independent
  descriptor/archive hashes; compressed/decompressed/member/row/line bounds;
  no symlink, trailing gzip data, PAX, duplicate or traversal member. Count all
  decompressed bytes including tar framing, not only declared member sizes.
  Validate page/vector IDs, finite components, model/dim and chunk text hashes
  against the existing chunk rules. Reuse those pure rules without importing
  docs/Pillow. Normalize site URL and preserve base prefix.
- [ ] **GREEN producer:** CLI accepts `--docs`, `--output`, `--source-sha`,
  `--site-url`, `--public-delivery`; publishes immutable hash directory first,
  manifest last with atomic write. In local mode archive path is relative;
  public mode uses the fixed ai delivery origin. Existing same-hash bytes are
  verified, never overwritten with different contents.
- [ ] **Verify:** Real current docs corpus round-trip, deterministic rebuild,
  bad vectors/schema/count/hash and all archive budget cases pass. Record exact
  focused command and results, run existing vector/index tests, self-review,
  then commit only this task's files and submit for spec+quality review.

### Task 2: Bounded snapshot cache and background coordinator

**Files:** create `scripts/v8std_mcp_snapshots.py` and
`tests/test_v8std_mcp_snapshots.py`; consume Task 1 format module.

**Interfaces produced:**

```python
class SnapshotStore:
    def __init__(self, site_url: str, cache_dir: Path): ...
    def cached(self) -> VerifiedSnapshot | None: ...
    def refresh(self) -> VerifiedSnapshot: ...

class SnapshotCoordinator:
    def __init__(self, store: SnapshotStore, build, *, refresh_seconds: int = 3600): ...
    def start(self) -> None: ...
    def current(self): ...  # returns one built generation or raises INDEX_NOT_READY
    def status(self) -> dict: ...
    def close(self) -> None: ...
```

`build: Callable[[VerifiedSnapshot], Any]` constructs an immutable generation.
The coordinator owns the active reference and stores network/parse work outside
the request path. Prepare in a bounded worker with a lifecycle that is stopped
on close; no network/CPU build on the ASGI event loop. Test/store internals may
inject monotonic clock/transport at their actual dependency boundary, never
test-only methods on production classes.

- [ ] **RED:** ThreadingHTTPServer fixtures count GETs, return delayed chunks,
  corrupt archives, foreign redirects and 304. Cold failure must produce explicit
  not-ready; warm store must keep its previous corpus ID. Example contract test:

```python
before = coordinator.current()
source.begin_blocking_response()
source.wait_until_requested()
self.assertIs(coordinator.current(), before)
self.assertEqual(coordinator.current().corpus_id, "fixture-generation-a")
```

  Fixture generations in this test are small builder results independent of the
  format hash; real-format tests use actual corpus IDs. Run focused tests to RED.
- [ ] **GREEN URL/network:** Resolve manifest below selected base prefix;
  permit fixed ai archive origin only for default public site; validate every
  redirect, no downgrade, no credentials and three redirects maximum. Stream
  reads enforce byte caps plus 60s whole attempt/20s read timeout. Validate
  Content-Encoding and length; reuse ETag/Last-Modified only with a valid cache.
- [ ] **GREEN cache/lifecycle:** Namespace by normalized source/schema; verify
  cache before use; retain active+previous and pins. File lock serializes
  download/commit between processes, query never takes it. Atomic durable pointer
  update precedes in-process swap; crash, disk-full, corrupt current fall back to
  previous same-source generation. Cache total includes staging and is bounded
  at 256 MiB. One background updater, 3600s refresh ±20%, 30…3600s error backoff,
  zero disables periodic refresh after bootstrap. Close interrupts workers with
  a bounded deadline, without orphan processes/threads holding interpreter exit.
- [ ] **Verify:** Test same/different sources, prefix, zero interval, 304 without
  cache, delayed read, repeated faults, crash stages, two processes/shared volume,
  cache budget and no query blocking. Run Task 1+2 tests, record RED/GREEN and
  commit task files; request spec+quality review before integration.

### Task 3: Frozen index generations, presentation and MCP lifecycle

**Files:** create `scripts/v8std_mcp_runtime.py`,
`scripts/v8std_mcp_presentation.py`, `tests/test_v8std_mcp_runtime.py`,
`tests/test_v8std_mcp_presentation.py`; modify index/server and focused tests.

**Interfaces produced:**

```python
@dataclass(frozen=True)
class IndexGeneration:
    corpus_id: str
    index: V8StdIndex
    resources: dict[str, str]

class SnapshotIndex:
    # Same public search/page/related/explain_snippet/explain_diagnostics,
    # read_resource_text/status/max_snippet_chars boundary as V8StdIndex.
    def start(self) -> None: ...
    def close(self) -> None: ...

def build_generation(snapshot: VerifiedSnapshot, *, max_snippet_chars: int) -> IndexGeneration: ...
def present_result(value, *, canonical_site_url: str, site_url: str,
                   page_paths: dict): ...
```

Construct one V8StdIndex from already validated bytes without network. Add a
focused factory for this to existing index; retain legacy direct file entrypoints
for current tests/developer use. Never mutate this index after construction.
Facade captures coordinator.current() once per top-level call, invokes that
generation including nested snippet/search/related operations, then transforms
only presentation links on the returned copy.

- [ ] **RED:** Wire tests initialize/list tools before source readiness; valid
  call before ready is error `INDEX_NOT_READY`; `/healthz` is 503 and `/livez`
  200. Add full snippet compatibility and generation-swap tests; public source
  fetch is forbidden in callbacks. A local-prefix fixture must retain literal
  code containing a public URL while its Markdown/HTML links become local:

```python
self.assertIn("`https://v8std.ru/std/437/`", result["page"]["body_markdown"])
self.assertEqual(result["page"]["url"], "http://localhost:8080/kb/std/437/")
self.assertEqual(result["page"]["source_urls"], ["https://its.1c.ru/db/v8std/content/437/hdoc"])
```

- [ ] **GREEN presentation:** Parse Markdown link/image/reference/autolink and
  HTML attributes outside code; rewrite only known internal paths, preserve
  external provenance/query/fragment. Local URLs accepted as page lookup inputs
  resolve to canonical keys without affecting ranking. All nested result URLs
  and three legacy Resource bodies use the same policy; no global string replace.
- [ ] **GREEN runtime:** Startup chooses snapshot mode from SITE_URL/default,
  supports stdio and HTTP from same build_server. Legacy explicit files remain
  usable; ambiguous legacy URLs plus site setting fail before network. Default
  direct Python transport stays compatible; container supplies stdio explicitly.
  Initialize/schema immediate, background bootstrap, bounded EOF/SIGTERM cleanup,
  clean stdout, health/version compact additive metadata, no raw errors/data.
- [ ] **Verify:** Task 1–3 tests plus all MCP server/index/snippet/combined tests;
  real stdio subprocess and loopback HTTP smoke; before/after search benchmark
  on same corpus, slow-source requests and CPU/RAM refresh measurements. Commit
  only reviewed implementation; no changed scores or widened snippet/query limits.

### Task 4: Runtime/static images, local profile and Compose

**Files:** create `Dockerfile.mcp`, `Dockerfile.site`, `.dockerignore`,
`requirements-mcp.lock`, `compose.yaml`, `deploy/container/site.conf`,
`scripts/build_local_site.py`, `tests/test_v8std_mcp_distribution.py`,
`scripts/check_mcp_container.py`, `deploy/docker-catalog/server.yaml`;
modify `overrides/main.html`, docs and build wrapper only where profile needs it.

**Consumes:** Task 1 producer CLI and Task 3 runtime CLI. Runtime container
default CMD selects stdio; HTTP command selects host 0.0.0.0/port 8000.
Static image consumes already built local `site` and included snapshot, not
the runtime image. Keep existing source-bind Compose explicitly dev.

- [ ] **RED:** Tests execute the local-profile build into a temporary directory,
  then assert HTTP pages+manifest/archive work without external network. Container
  harness initializes stdio twice with shared volume and verifies a tool call,
  generation ID/cache reuse, EOF exit and runtime readiness:

```python
self.assertEqual(reply["result"]["serverInfo"]["name"], "v8std")
self.assertFalse(tool_reply.get("isError", False))
self.assertEqual(container_inspect["Config"]["User"], "10001:10001")
```

  Use actual current serverInfo name from build_server if it differs; this is
  a named compatibility check, not permission to rename the server.
- [ ] **GREEN images/profile:** Resolve pinned base digests and full dependency
  lock; copy only runtime modules/rules/licenses. Non-root UID/GID 10001, read-only
  root, persistent writable cache, tmpfs, cap-drop and init. Local profile disables
  analytics/recorder and external fonts/assets, preserving public profile. Same
  archive bytes are used for public/local manifests. Build on arm64 and exercise
  amd64 in available Docker emulation, noting native-CI gate separately.
- [ ] **GREEN launch/catalog:** Compose references published image coordinates
  with explicit version/digest override for local test images, loopback published
  ports, optional MCP profile, named cache and one common routable SITE_URL.
  Document/test desktop host access and Linux host-gateway. Catalog points to
  self-published image, declares site/snippet/cache and long-lived stdio behavior;
  validate against current Docker schema without submitting an external PR.
- [ ] **Verify:** Run distribution unit/integration harness, real Docker stdio/HTTP,
  non-root read-only startup, persistent cache offline restart, local site request
  graph without public egress and multi-session Gateway where locally available.
  Verify licenses/SBOM inputs. Record unavailable external catalog acceptance
  explicitly, not as a passed test. Commit task and perform review.

### Task 5: Restricted release transaction and independent index store

**Files:** create `scripts/v8std_mcp_release.py`, `tests/test_v8std_mcp_release.py`,
`deploy/container/release.schema.json`, controller/service/nginx configurations
under `deploy/container/`, `spec/operations/mcp-container-activation.md`.

**Interfaces produced:** CLI `validate-envelope`, `deploy`, `recover`, `status`,
`publish-index`; inputs are typed bounded JSON or fixed paths under configured
state/store roots. Release controller effects go through a narrow adapter to
Docker/nginx/systemd; tests use disposable processes/filesystems and record exact
calls at this external boundary, not pretend mocked return values prove health.

- [ ] **RED:** Test unknown schema, invalid digest/namespace/config path, stale or
  mutated duplicate ID, concurrent releases, failed pull/ready/switch/smoke,
  rollback failure and restart reconciliation. Example visible invariant:

```python
self.assertEqual(controller.status()["state"], "ROLLED_BACK")
self.assertEqual(edge.serving_digest(), predecessor_digest)
self.assertTrue(predecessor_snapshot_path.is_file())
```

- [ ] **GREEN controller:** Verify envelope/attestation/trusted config before
  effects, durable journal+lock, exact image digest, capacity preflight and
  predecessor pins. Prepare candidate side port, real readiness and MCP smoke,
  nginx test then atomic switch/reload, public smoke then commit/drain. Enforce
  5min transaction, 90s readiness, 30s smoke/drain, 45s final stop; loss of caller
  does not kill host recovery. Stale retry cannot supersede current sequence.
- [ ] **GREEN static store/operations:** Independent read-only nginx alias for
  `/indexes/v1/` with GET/HEAD, hash cache headers and bounded download admission;
  publisher stages/verifies/renames objects and tracks references/pins before GC.
  Activation runbook names exact backup/cleanup/TLS/default-vhost, secrets,
  protection, native capacity and initial Python rollback prerequisites. No live
  host changes occur from tests or writing the runbook.
- [ ] **Verify:** Fault matrix for each state transition with real subprocess
  cancellation/crash recovery where possible; nginx syntax and static download
  while runtime stopped in disposable containers; unprivileged controller input
  rejects shell injection. Record capacity test settings and results without
  claiming 100k. Commit and review the host code as security-sensitive code,
  not an authorization to install it on production.

### Task 6: Fail-closed publication CI, policy and final integration

**Files:** workflows under `.github/workflows/`, `scripts/publish_mcp_artifacts.py`,
`tests/test_mcp_publication.py`, process plan
`spec/plans/2026-09-10-mcp-ci-deployment-policy-plan.md`, `AGENTS.md`,
`spec/README.md`, repo skill references, architecture loader/policy tests,
`spec/operations/mcp-container-verification.md`, public installation docs.

**Consumes:** producer, image harness and typed release controller CLIs.
Publisher first places and externally verifies immutable corpus, then emits
Pages manifest. Every runtime deployment references published exact digest.

- [ ] **RED:** Test publication sequencing and early failure leaves current
  manifest unchanged; main/PR/fork/tag/stale eligibility matrix produces no host
  effects for disallowed inputs. Process loader resolves v2 with identical schema;
  frozen v1 and all accepted structured documents remain byte-identical.
- [ ] **GREEN pipeline:** PR validation without secrets; pin action SHAs, image
  bases and runtime dependencies; architecture/build/tests/bench before publish;
  buildx multiarch image, SBOM/provenance/attestation and digest smoke. Detect
  content vs runtime inputs to avoid article-triggered MCP restart. Production
  job requires verified main, restricted environment and explicit activation
  variable; `cancel-in-progress: false`, idempotent/stale host validation.
  Before activation retain working Pages delivery without publishing an ai
  manifest that points to an unavailable object. Build candidate artifacts locally;
  enabled publication either verifies the object or fails closed.
- [ ] **GREEN process:** Write separate process plan, synchronize process v2
  pointer/instructions/tests. Preserve initial manual activation and explicit
  permission for push. Align all current policy references; historic v1 and old
  structured plans stay frozen. Write reproducible commands/evidence and separate
  external gates for registry/Catalog/target-host. Do not publish internal specs.
- [ ] **Final gates:** Run semantic impact on actual paths, CLI `impact`,
  `validate --merge-ready`, all applicable fitness; strict build, then full suite;
  container smoke and shared-host mixed load on disposable local stack, review
  whole branch and repair concrete findings. Record exact SHA/results and
  unperformed external operations. No push, merge of incomplete plan, PR closure
  or production deployment inferred from these green tests.

## Evidence

Each task's implementation/review evidence is recorded during execution in its
SDD report and completion checkbox. Final durable summary goes in
`spec/operations/mcp-container-verification.md`, including commands, environment,
results and the boundary between local evidence and production acceptance.
