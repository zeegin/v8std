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
- Production/наш direct Docker/Compose сохраняют read-only rootfs, cap-drop ALL, no-new-privileges, init и bounded tmpfs. Gateway использует нативный профиль: non-root/init/no-new-privileges, без privileged MCP и Docker socket; отсутствующие readonly/capdrop/tmpfs документируются, не блокируя Catalog сами по себе.
- Local site и MCP не делают background public egress. Cold-offline thin image без cache не готов; warm-offline с проверенным cache работает.
- Основной checkout, существующая ветка `codex/mcp-container-distribution-design`; не создавать worktree, не менять main, не пушить и не деплоить во время реализации.
- TDD и focused tests для каждого поведения. Strict build выполняется **до** полного suite: tests читают `site/LICENSES`, параллельная пересборка разрушает их вход.
- Утверждение о 100 000 подключений запрещено без production-like mixed-load evidence.
- Первый выпуск — опубликованный Docker image; Docker Catalog и upstream PR
  отложены отдельным решением пользователя и не являются блокерами этого выпуска.
- Первичная ручная миграция может использовать назначенное пользователем окно
  до двух часов без old/new overlap; автоматический rollout сохраняет overlap gate.
  Дата окна ещё не назначена. Согласование plan не разрешает остановку production.

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
| 1 | `scripts/v8std_mcp_snapshot_format.py`, `scripts/generate_mcp_snapshot.py`, `scripts/v8std_mcp_chunks.py`, `scripts/generate_search_vectors.py`, `tests/test_v8std_mcp_snapshot_format.py`, `tests/mcp_snapshot_fixtures.py` | Pure format validation, deterministic producer and shared unchanged chunk rules; no network/index refresh. |
| 2 | `scripts/v8std_mcp_snapshots.py`, `tests/test_v8std_mcp_snapshots.py` | URL trust boundary, HTTP/cache transaction, background coordinator. |
| 3 | `scripts/v8std_mcp_runtime.py`, `scripts/v8std_mcp_presentation.py`, `scripts/v8std_mcp_index.py`, `scripts/v8std_mcp_server.py`, runtime tests | Frozen generation construction, request facade, stdio/HTTP lifecycle. |
| 4 | Dockerfiles/Compose/lock, local-profile script, tests, docs | Build and exercise the two images and local site. |
| 5 | `deploy/container/`, `scripts/v8std_mcp_release.py`, release tests; snapshot/runtime integration and focused tests | Typed host transaction, nginx index store, fixed release generation and recovery. |
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

- [x] **RED:** Add behavior tests with hand-authored one-page docs and independently
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
- [x] **GREEN format:** Implement strict JSON with duplicate-key/depth/type
  guards; exact five regular members; deterministic gzip/tar; independent
  descriptor/archive hashes; compressed/decompressed/member/row/line bounds;
  no symlink, trailing gzip data, PAX, duplicate or traversal member. Count all
  decompressed bytes including tar framing, not only declared member sizes.
  Validate page/vector IDs, finite components, model/dim and chunk text hashes
  against the existing chunk rules. Reuse those pure rules without importing
  docs/Pillow. Normalize site URL and preserve base prefix.
- [x] **GREEN producer:** CLI accepts `--docs`, `--output`, `--source-sha`,
  `--site-url`, `--public-delivery`; publishes immutable hash directory first,
  manifest last with atomic write. In local mode archive path is relative;
  public mode uses the fixed ai delivery origin. Existing same-hash bytes are
  verified, never overwritten with different contents.
- [x] **Verify:** Real current docs corpus round-trip, deterministic rebuild,
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
    def refresh(self, *, prepare=None): ...

class SnapshotCoordinator:
    def __init__(self, store: SnapshotStore, build, *, refresh_seconds: int = 3600): ...
    def start(self) -> None: ...
    def current(self): ...  # returns one built generation or raises INDEX_NOT_READY
    def status(self) -> dict: ...
    def close(self) -> None: ...
```

`build: Callable[[VerifiedSnapshot], Any]` constructs an immutable generation.
`SnapshotStore.refresh(prepare=build)` invokes build before the durable cache
commit and returns its result; without prepare it returns VerifiedSnapshot.
Preparation failure preserves the former disk pointer as well as process state.
The coordinator owns the active reference and stores network/parse work outside
the request path. A supervised `multiprocessing` worker using the `spawn` start
method owns blocking source I/O, validation, generation preparation and cache
commit. The parent enforces the whole-attempt deadline and terminates/reaps the
worker on timeout or close; a daemon thread alone is not cancellation. Internal
builder callables and their results must support this trusted process boundary.
Only IPC from the application's own worker may carry serialized Python objects;
never load pickle from downloaded data or a persistent/shared cache. Task 3 adds
the minimal frozen-index serialization hook to reconstruct its process-local
lock. Measure transfer/startup/staging RSS and query latency during integration.
No network/CPU build runs on the ASGI event loop. Test/store internals may
inject monotonic clock/transport at their actual dependency boundary, never
test-only methods on production classes.

- [x] **RED:** ThreadingHTTPServer fixtures count GETs, return delayed chunks,
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
- [x] **GREEN URL/network:** Resolve manifest below selected base prefix;
  permit fixed ai archive origin only for default public site; validate every
  redirect, no downgrade, no credentials and three redirects maximum. Stream
  reads enforce byte caps plus 360s whole attempt/20s read timeout. Validate
  Content-Encoding and length; reuse ETag/Last-Modified only with a valid cache.
- [x] **GREEN cache/lifecycle:** Namespace by normalized source/schema; verify
  cache before use; retain active+previous and pins. File lock serializes
  download/commit between processes, query never takes it. Atomic durable pointer
  update precedes in-process swap; crash, disk-full, corrupt current fall back to
  previous same-source generation. Cache total includes staging and is bounded
  at 256 MiB. One background updater, 3600s refresh ±20%, 30…3600s error backoff,
  zero disables periodic refresh after bootstrap. Close interrupts workers with
  a bounded deadline, without orphan processes/threads holding interpreter exit.
- [x] **Verify:** Test same/different sources, prefix, zero interval, 304 without
  cache, delayed read, repeated faults, crash stages, two processes/shared volume,
  cache budget and no query blocking. Run Task 1+2 tests, record RED/GREEN and
  commit task files; request spec+quality review before integration.

### Task 3: Frozen index generations, presentation and MCP lifecycle

**Files:** create `scripts/v8std_mcp_runtime.py`,
`scripts/v8std_mcp_presentation.py`, `tests/test_v8std_mcp_runtime.py`,
`tests/test_v8std_mcp_presentation.py`; modify index/server and focused tests.
Integrate publisher-side link validation in `generate_mcp_snapshot.py` and its
focused tests, reusing the presentation parser/catalog rather than a second
link grammar. Treat the three Resources and published license paths as explicit
auxiliary catalog entries, not corpus pages or arbitrary allowed paths.
If reliable source-preserving parsing needs a small parser dependency, include
its pinned runtime/build requirement and focused dependency-boundary tests in
this task. The producer must not import a docs builder; standalone Python `-S`
was an implementation check, not an approved prohibition on parser dependencies.
Keep the pure snapshot format reader independent of docs tooling.

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
focused factory and a trusted-IPC serialization hook (exclude/recreate the
process-local lock, never deserialize a persistent pickle cache) to existing
index; retain legacy direct file entrypoints
for current tests/developer use. Never mutate this index after construction.
Facade captures coordinator.current() once per top-level call, invokes that
generation including nested snippet/search/related operations, then transforms
only presentation links on the returned copy.

- [x] **RED:** Wire tests initialize/list tools before source readiness; valid
  call before ready is error `INDEX_NOT_READY`; `/healthz` is 503 and `/livez`
  200. Add full snippet compatibility and generation-swap tests; public source
  fetch is forbidden in callbacks. A local-prefix fixture must retain literal
  code containing a public URL while its Markdown/HTML links become local:

```python
self.assertIn("`https://v8std.ru/std/437/`", result["page"]["body_markdown"])
self.assertEqual(result["page"]["url"], "http://localhost:8080/kb/std/437/")
self.assertEqual(result["page"]["source_urls"], ["https://its.1c.ru/db/v8std/content/437/hdoc"])
```

- [x] **GREEN presentation:** Parse Markdown link/image/reference/autolink and
  HTML attributes outside code; rewrite only known internal paths, preserve
  external provenance/query/fragment. Local URLs accepted as page lookup inputs
  resolve to canonical keys without affecting ranking. All nested result URLs
  and three legacy Resource bodies use the same policy; no global string replace.
  Validate publisher links against the same catalog. Preserve generated bare
  internal `URL:`/`HTML:` fields and resolve relative links in their page context;
  ordinary code literals and external source records are not link nodes.
- [x] **GREEN runtime:** Startup chooses snapshot mode from SITE_URL/default,
  supports stdio and HTTP from same build_server. Legacy explicit files remain
  usable; ambiguous legacy URLs plus site setting fail before network. Default
  direct Python transport stays compatible; container supplies stdio explicitly.
  Initialize/schema immediate, background bootstrap, bounded EOF/SIGTERM cleanup,
  clean stdout, health/version compact additive metadata, no raw errors/data.
- [x] **Verify:** Task 1–3 tests plus all MCP server/index/snippet/combined tests;
  real stdio subprocess and loopback HTTP smoke; before/after search benchmark
  on same corpus, slow-source requests and CPU/RAM refresh measurements. Commit
  only reviewed implementation; no changed scores or widened snippet/query limits.

### Task 4: Runtime/static images, local profile and Compose

**Files:** create `Dockerfile.mcp`, `Dockerfile.site`, `.dockerignore`,
`requirements-mcp.lock`, `compose.yaml`, `deploy/container/site.conf`,
`scripts/build_local_site.py`, `tests/test_v8std_mcp_distribution.py`,
`scripts/check_mcp_container.py`, `deploy/docker-catalog/server.yaml`;
modify `overrides/main.html`, docs and build wrapper only where profile needs it.
Add an explicit index for the three already published license text files in
`scripts/publish_license_texts.py` and cover it in its existing tests: the current
attribution page links `/LICENSES/`, which otherwise has no page when directory
listing is disabled. Both public and local builds must resolve this same path.

**Consumes:** Task 1 producer CLI and Task 3 runtime CLI. Runtime container
default CMD selects stdio; HTTP command selects host 0.0.0.0/port 8000.
Static image consumes already built local `site` and included snapshot, not
the runtime image. Keep existing source-bind Compose explicitly dev.

- [x] **RED:** Tests execute the local-profile build into a temporary directory,
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
- [x] **GREEN images/profile:** Resolve pinned base digests and full dependency
  lock; copy only runtime modules/rules/licenses. Non-root UID/GID 10001, read-only
  root, persistent writable cache, tmpfs, cap-drop and init in our owned launches;
  native Gateway uses the separately approved profile below. Local profile disables
  analytics/recorder and external fonts/assets, preserving public profile. Same
  archive bytes are used for public/local manifests. Build on arm64 and exercise
  amd64 in available Docker emulation, noting native-CI gate separately.
- [x] **GREEN launch/catalog:** Compose references published image coordinates
  with explicit version/digest override for local test images, loopback published
  ports, optional MCP profile, named cache and one common routable SITE_URL.
  Document/test desktop host access and Linux host-gateway. Catalog points to
  self-published image, declares site/snippet/cache and long-lived stdio behavior;
  validate against current Docker schema without submitting an external PR.
- [x] **Verify:** Run distribution unit/integration harness, real Docker stdio/HTTP,
  non-root read-only startup, persistent cache offline restart, local site request
  graph without public egress and multi-session Gateway where locally available.
  Verify licenses/SBOM inputs. Record unavailable external catalog acceptance
  explicitly, not as a passed test. Commit task and perform review.

#### Task 4 reviewed fixes — approved attempt-budget update

User explicitly requested `360` seconds after reviewing the original timeout.
This supersedes the original numerical budget only. Gateway scope/security
decisions and external mutation authority are not inferred from that change.
Keep historical measurements labelled with their original 60-second build.

- [x] **RED:** In `tests/test_v8std_mcp_snapshots.py`, assert a default store
  uses `360` attempt seconds and `20` read seconds; retain accelerated real
  worker timeout/reaping, close and responsive-query tests. In distribution
  tests resolve Compose with an explicit alternate SITE_URL and prove it is
  passed intact instead of replaced by the default local URL.
- [x] **GREEN:** Set `ATTEMPT_SECONDS = 360` in
  `scripts/v8std_mcp_snapshots.py`. Compose consumes
  `${V8STD_MCP_SITE_URL:-http://v8std.localhost:${V8STD_SITE_PORT:-18765}${V8STD_SITE_PREFIX:-/}}`.
  Test actual Compose interpolation; do not assume nested defaults work without
  executing its config resolver. Preserve local default, prefix and one setting.
  Adapt only the integration startup wait to allow the accepted attempt plus
  bounded startup margin; do not turn RPC/read/shutdown timeouts into360seconds.
- [x] **VERIFY:** Run focused snapshot/distribution tests, commit the exact
  changed runtime, build a new amd64 image from that clean source SHA and rerun
  full-corpus supervised cold/warm stdio/HTTP acceptance under QEMU. Exercise an
  explicit reachable SITE_URL override end-to-end, checking source and returned
  links. No privileged Gateway retry, image publication or native-CI claim.
- [x] **REVIEW:** Independent scoped review of the fix diff and evidence.
  These checks resolved Compose/QEMU findings only. The subsequent explicit
  Gateway profile approval and its scoped verification are recorded below.

#### Task 4 reviewed fixes — approved launcher-owned security profiles

User approved retaining the strict owned-launch profile and using Gateway's
actual native isolation, without deferring Catalog solely for absent flags.
The candidate design/ADR/invariant/distribution contract now express that
distinction. No main structured document, public API, image identity or other
release acceptance boundary changes. This approval does not authorize daemon,
socket, host or registry changes.

- [x] **RED:** Add focused inspection-validator tests in
  `tests/test_v8std_mcp_distribution.py`: an actual-shaped native Gateway state
  with `ReadonlyRootfs=False`/`CapDrop=None` is accepted only with user10001:10001,
  init/no-new-privileges, nonprivileged mode and no Docker socket mount. Reject
  each missing required control and socket aliases/mount destinations. Verify
  the generic override helper accepts two valid URLs; require default404 only
  when the explicit regression flag is enabled.
- [x] **GREEN:** In `scripts/check_mcp_container.py`, validate and report every
  created Gateway server's required controls and observed optional controls.
  Add `--require-default-source-404` for the intentional override regression;
  keep source/link/namespace checks for every override. Update Catalog comments
  and `docs/container-installation.md` to state both profiles and remaining
  external gates. Do not invent unsupported Catalog fields or modify Compose
  protections. Keep helper logic importable for focused tests.
- [x] **VERIFY:** Run focused distribution tests and actual two-session warm
  Gateway check using isolated config, already verified cache and network none.
  Inspect all session containers and retain actual profile evidence. Use only
  task-owned Docker resources; no socket escalation, cold-network workaround,
  public publication or unnecessary repeat of accepted QEMU/360 tests.
- [x] **REVIEW:** Scoped re-review of the Gateway finding against the approved
  amended contract, helper regression and observed evidence before closing
  Task4. Cold Gateway routing/native CI/publication remain external gates.

### Task 5: Restricted release transaction and independent index store

**Files:** create `scripts/v8std_mcp_release.py`, `tests/test_v8std_mcp_release.py`,
`deploy/container/release.schema.json`, controller/service/nginx configurations
under `deploy/container/`, `spec/operations/mcp-container-activation.md`.
Extend snapshot/runtime modules and their focused tests only for the release
contract's generation hold, selected rollback corpus and refresh resumption.

**Interfaces produced:** CLI `validate-envelope`, `deploy`, `recover`, `status`,
`publish-index`; inputs are typed bounded JSON or fixed paths under configured
state/store roots. Release controller effects go through a narrow adapter to
Docker/nginx/systemd; tests use disposable processes/filesystems and record exact
calls at this external boundary, not pretend mocked return values prove health.

**Execution boundary:** The ordinary slice is implemented in signed `1d04817`
and `5ae7588` and independently reviewed. Final148 release/hold/snapshot/runtime
tests and the real Docker/nginx check passed; five review findings were repaired
with RED/GREEN and approved in scoped re-review. This supersedes the earlier
paused29-test evidence. First migration is implemented in signed `fdb1d82` and
passed separate spec/quality review. The182-test focused run, amended36 bootstrap
tests and all36 restricted Linux cases passed; the verification record retains
the exact sequence and earlier failed diagnostics. Task5 is locally complete.
Native host setup/rehearsal, published-artifact evidence and production capacity
remain external gates. Task6 and final branch gates are still required.

- [x] **RED:** Test unknown schema, invalid digest/namespace/config path, stale or
  mutated duplicate ID, concurrent releases, failed pull/ready/switch/smoke,
  rollback failure and restart reconciliation. Example visible invariant:

```python
self.assertEqual(controller.status()["state"], "ROLLED_BACK")
self.assertEqual(edge.serving_digest(), predecessor_digest)
self.assertTrue(predecessor_snapshot_path.is_file())
```

- [x] **GREEN controller:** Verify envelope/attestation/trusted config before
  effects, durable journal+lock, exact image digest, capacity preflight and
  predecessor pins. Prepare candidate side port, real readiness and MCP smoke,
  nginx test then atomic switch/reload, public smoke then commit/drain. Enforce
  5min transaction, 90s readiness, 30s smoke/drain, 45s final stop; loss of caller
  does not kill host recovery. Stale retry cannot supersede current sequence.
  Integrate a bounded trusted host-control path that holds the selected verified
  generation during readiness/switch/rollback and resumes normal refresh after
  commit. Cache pins retain bytes; they do not select or freeze a process's
  generation. Likewise, zero refresh interval alone is not a release hold: the
  current coordinator performs a warm-start network refresh. Exercise a changing
  source manifest during the transaction, a postcommit worker failure, restart
  from the selected predecessor and refresh resumption. Neither a retained
  archive nor a disk pointer alone proves the endpoint serves the required
  corpus ID. Preserve ordinary local stdio/HTTP behavior and the single public
  SITE_URL setting; release control must not be exposed as an MCP tool.
- [x] **GREEN static store/operations:** Independent read-only nginx alias for
  `/indexes/v1/` with GET/HEAD, hash cache headers and bounded download admission;
  publisher stages/verifies/renames objects and tracks references/pins before GC.
  Activation runbook names exact backup/cleanup/TLS/default-vhost, secrets,
  protection, native capacity and initial Python rollback prerequisites. No live
  host changes occur from tests or writing the runbook.
- [x] **Verify:** Fault matrix for each state transition with real subprocess
  cancellation/crash recovery where possible; nginx syntax and static download
  while runtime stopped in disposable containers; unprivileged controller input
  rejects shell injection. Record capacity test settings and results without
  claiming 100k. Commit and review the host code as security-sensitive code,
  not an authorization to install it on production.

#### First-migration completion slice — before Task6 integration

**Files:** extend `scripts/v8std_mcp_release.py`,
`tests/test_v8std_mcp_release.py`, `tests/mcp_release_fixture.py`,
`deploy/container/` and `spec/operations/mcp-container-activation.md`.
Use a separate scoped review after the ordinary controller is stable. Do not
add a second runtime, change snapshot format or enlarge the CI command allowlist.

**Interface:** operator-only CLI `bootstrap`, `bootstrap-recover`,
`bootstrap-status`, dispatched in the existing release module; the restricted
CI entry must reject all three. Bootstrap consumes the existing validated
release envelope plus a root-owned, size-bounded window/legacy record from the
installed policy directory, not arbitrary CLI paths. That record contains UTC
start/end (at most7200seconds), exact envelope SHA256, the fixed legacy unit
`v8std-mcp.service` and hashes of saved config/data. Legacy startup/config paths
come from verified host inventory and root-owned policy, never from CI input.
It produces the existing bounded status shape and an initial accepted container
record only after real smoke. Reuse digest/attestation/hold/inspection/smoke code.
Prepare immutable artifacts/backup before the window; mint and authorize the
execution envelope just before each bounded attempt so its300second deadline
has not expired during preparation. Recovery of an already-started attempt
must remain allowed after window expiry; only new attempts are refused.

- [x] **RED initial boundary:** Execute CLI against a disposable fixture and
  show rejection outside/missing window, wrong envelope hash, existing active
  container, CI entry invocation and insufficient single-runtime capacity.
  Add subprocess fault cases after legacy stop, after candidate start, after
  switch and during initial active-record persistence. Assert the endpoint,
  exact served data and owned process count, not just a successful exit.
- [x] **GREEN initial transition:** Add a serialized initial journal and
  independently scheduled host recovery before stopping legacy. Stop/start is
  allowed only inside the operator window. Commit the first container record
  after local/public smoke, or restore verified Python config/data/upstream.
  A no-predecessor ordinary `deploy` remains rejected; do not fabricate its
  required `active.json`. Failures after accepted commit reconcile persistence,
  not blindly roll back an already accepted container. Before acceptance,
  startup/reboot recovery restores the saved legacy service; after acceptance
  it starts the exact accepted digest, without racing the still-enabled legacy unit.
- [x] **VERIFY initial transition:** Run the real disposable process fixture
  under restricted memory, including no-overlap, SIGKILL/lost SSH, crash at each
  persistence boundary, duplicate request and rollback failure. Record absence
  of any simultaneous legacy/candidate process in stop/start mode. Keep static
  archive GET/HEAD available throughout. Before the host window, replay the
  tested runbook on native Linux and measure return-to-legacy time.

The completed checkbox records local fixture verification. Native host rehearsal
remains a prerequisite for the later operational window; it has not been
performed or inferred from Docker tests.

Required observable outcomes (the fixture's CLI returns JSON with these fields):

```python
self.assertEqual(result["state"], "ROLLED_BACK")
self.assertEqual(served_runtime_sha, saved_legacy_sha)
self.assertEqual(served_data_sha, saved_legacy_data_sha)
self.assertEqual(candidate_process_count, 0)
self.assertEqual(static_archive_sha, published_archive_sha)
```

Here `result` is the parsed bootstrap CLI status. `served_runtime_sha` is the
restarted process's verified source identity, `served_data_sha` the legacy
health/data hash, and `candidate_process_count` the fixture-owned PID count;
the archive values come from an independent GET and the published manifest.
Do not compare legacy health fields against the new runtime's different schema.

Run existing release/hold/snapshot/runtime tests explicitly before the scoped
review; do not mark the live migration complete from these fixtures:

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_release tests.test_v8std_mcp_release_hold tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_runtime -v
```

### Task 6: Fail-closed publication CI, policy and final integration

**Files:** workflows under `.github/workflows/`, `scripts/publish_mcp_artifacts.py`,
`tests/test_mcp_publication.py`, process plan
`spec/plans/2026-09-10-mcp-ci-deployment-policy-plan.md`, `AGENTS.md`,
`spec/README.md`, repo skill references, architecture loader/policy tests,
`spec/operations/mcp-container-verification.md`, public installation docs and
Catalog release metadata/harness under `deploy/docker-catalog/`,
`scripts/check_mcp_container.py`, `tests/test_v8std_mcp_distribution.py`;
private usage logging in `scripts/v8std_mcp_usage.logrotate`, release launch/host
templates and their focused integration tests; public retirement conformance in
`tests/test_v8std_mcp_monitoring_retirement.py` and its separate approved plan;
the retained final parser regression in `scripts/v8std_mcp_presentation.py`
and `tests/test_v8std_mcp_presentation.py`.

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
- [ ] **VERIFY release scope and independent activation:** Image publication
  and corpus upload can run while runtime deployment is disabled. Test that
  first-bootstrap success alone does not activate automatic runtime deployment;
  failed overlap capacity leaves the running endpoint untouched. Document
  image-only scope without claiming Docker Catalog acceptance. Preserve the
  `longLived` source declaration and distinguish local test-catalog diagnostics
  from the actual Docker-published catalog; no upstream PR is a release prerequisite.
- [ ] **VERIFY private operations and retired public monitoring:** The approved
  `design:mcp-public-monitoring-retirement` supersedes the earlier preservation
  task. Consume its410/no-store conformance and production retirement evidence;
  never recreate dashboard, timer, aggregator or private monitor-state bridge.
  Independently wire and verify persistent private usage logging for the new
  runtime through its real launcher: rollback/restart/rotation must preserve
  existing history and new events without restoring logs from a release backup.
  Preserve the non-root runtime and existing rotation policy; grant no Docker
  socket/group. Test actual MCP health/readiness, not controller liveness.
  This checkbox remains incomplete until container logger integration is
  implemented and verified. Dashboard retirement alone does not complete it.
  Local OpenMetrics remains a separate deferred design.
- [ ] **VERIFY retained parser finding:** Add RED/GREEN for `![<code>](...)`
  followed by a visible internal link. HTML-looking image-alt text must not
  suppress rebasing or unknown-target validation of subsequent visible links.
  Preserve actual code/literal content, source offsets and canonical hashes.
  This is the concrete deferred Task3 review finding, not a new Markdown
  interpretation contract or permission to waive a pre-existing release defect.
- [ ] **Final gates:** Run semantic impact on actual paths, CLI `impact`,
  `validate --merge-ready`, all applicable fitness; strict build, then full suite;
  container smoke and shared-host mixed load on disposable local stack, review
  whole branch and repair concrete findings. Record exact SHA/results and
  unperformed external operations. No push, merge of incomplete plan, PR closure
  or production deployment inferred from these green tests.

### Deferred external Docker Catalog gate

The user's current choice is image-only publication. A later Catalog submission
uses the same published digest and `longLived: true`, followed by real repeated
tool calls without a masking global `--long-lived` flag. The upstream
`task catalog`/`ToTile` diagnostic loses this field, but it is a **test** catalog
generator. On2026-09-10 actual Docker v2/v3 catalogs contain the field for
Playwright and four other servers. Therefore its repair is not a necessary
precondition for image publication or even submission. No Catalog publication
or default end-user lifecycle success for v8std is claimed by removing the
incorrect pre-merge gate. Keep the original diagnostic and its correction in
the verification record; do not repeat it simply to rediscover the known defect.

## Evidence

Each task's implementation/review evidence is recorded during execution in its
SDD report and completion checkbox. Final durable summary goes in
`spec/operations/mcp-container-verification.md`, including commands, environment,
results and the boundary between local evidence and production acceptance.
