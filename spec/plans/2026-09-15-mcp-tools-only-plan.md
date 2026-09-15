---
schema_version: 1
kind: plan
id: mcp-tools-only
design: design:mcp-tools-only
implements:
  - contract:MCP_API@4.0
  - contract:MCP_CORPUS_SNAPSHOT@1.1
---

# MCP Tools Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Полностью отключить MCP Resources, сохранить пять tools и кешируемый индекс, подтвердить новый runtime реальными HTTP/stdio и смешанными локальными проверками.

**Architecture:** Один адаптер удаляет resource handlers закреплённого SDK при построении общего сервера. Готовое поколение больше не хранит полнокорпусную Resource presentation; исходный архив, background loader, ранжирование и интерфейсы tools не меняются. Приёмочные проверки используют tools для доказательства содержимого после refresh.

**Tech Stack:** Python 3.12, mcp==1.27.0/FastMCP, unittest, httpx, существующие snapshot fixtures, Docker/Compose и nginx.

**Spec:** [Согласованный design](../designs/2026-09-15-mcp-tools-only-design.md), [API 4.0](../contracts/mcp-api-v4-r0.md), [snapshot 1.1](../contracts/mcp-corpus-snapshot-v1-r1.md), [инвариант](../invariants/mcp-tools-only-surface-is-stable.md).

## Global Constraints

- В HTTP и stdio отсутствуют capability `resources`, Resource templates, resource notifications и все resource handlers.
- `initialize.result.capabilities.resources` отсутствует, а не равен `{}` или `null`.
- В `/version` остаётся `api: v2`, но `api_profiles` содержит только `legacy-tools`.
- Сохраняются `v8std_search`, `v8std_get_page`, `v8std_get_related`, `v8std_explain_snippet`, `v8std_explain_diagnostics`: имена, schemas, defaults, лимиты, формы успешных ответов и прежние ошибки tools.
- Формат snapshot major 1, состав пяти файлов, hashes и persistent cache namespace не меняются.
- Warm/offline, source isolation и атомарный background refresh сохраняются.
- Нет нового endpoint, сервиса, транспорта, флага конфигурации или fallback.
- Сайт, статический `/indexes/`, MCP data cache и закрытые журналы не удаляются.
- Публичный мониторинг не возвращается. Этот пакет не разрешает push, публикацию образа или ручные изменения production.
- Работа в основном checkout и существующей feature-ветке; новые worktrees, PR, remote mutations не нужны.
- TDD: сначала наблюдаемый RED, затем минимальная реализация и GREEN. Реальные wire/данные важнее проверки текста source.
- Strict build выполняется до полного suite: оба используют `site/LICENSES`. Генерацию и полный suite не запускать одновременно.
- `.venv` проекта не изменять. Для тестов доступен закреплённый runtime `/tmp/v8std-final-gates.e7aqas/venv/bin/python`; проверить его наличие и mcp==1.27.0 до использования.
- Существующие незавершённые CI/release планы не объявлять завершёнными. Полное отключение Resources заменяет их ресурсные ожидания по утверждённому design, не отменяя остальные gates.

## Scope and file boundaries

Task 1 меняет server/index/runtime и их прямые тесты, пользовательскую документацию.
Task 2 обновляет smoke нового runtime в release-controller; Task 3 меняет
container/load acceptance и пишет новый отчёт проверки. Задачи выполняются
последовательно; обе следующие задачи потребляют проверенную новую границу.
Ресурсные ожидания старого acceptance harness остаются промежуточным долгом
только до Task 3. Полный suite и strict build проводятся после всех задач;
между ними запускается полный набор затронутых focused modules.

`implements` не включает весь design/ADR и инвариант поставки, потому что
публикация digest во всех внешних каналах ещё не выполнена. Локальный candidate
и смоделированный switch не доказывают production rollout либо 100000 агентов.
Общий merge gate ветки остаётся отдельным от завершения этого плана.

### Task 1: Disable Resource dispatch and remove unused bulk presentation

**Files:**

- Modify: `scripts/v8std_mcp_server.py`, `scripts/v8std_mcp_runtime.py`, `scripts/v8std_mcp_index.py`.
- Create: `tests/test_v8std_mcp_tools_only.py`.
- Modify: `tests/test_v8std_mcp_runtime.py`, `tests/test_v8std_mcp_index.py`, `tests/test_v8std_mcp_combined.py`; `tests/test_v8std_mcp_server.py` only if an affected helper requires adaptation.
- Modify: `docs/mcp.md`, `docs/container-installation.md`; other active user documentation only for exact resource-support claims found by a scoped search.
- Read: `tests/mcp_snapshot_fixtures.py`, existing `StdioProcess`/HTTP fixtures, SDK dispatch/capability implementation.

**Interfaces:**

- Consumes: `build_server(index, *, host, port, mcp_path, allowed_hosts, allowed_origins, log_level, usage_logger)` and current `SnapshotIndex` tool facade.
- Produces: unchanged five tool call signatures; `IndexGeneration` retains `corpus_id`, `index`, `canonical_site_url`, `page_paths` but no `resources` field; no `read_resource_text` method or independent Resource download/cache path.
- Exposes no new public API. `build_server` may use one private `_disable_resource_handlers(server: FastMCP) -> None` helper in the same file; no new runtime dependency or Docker COPY path is needed.

- [ ] **Step 1: Add failing wire and generation tests.**

Use the real SDK with existing in-memory/local snapshot fixtures. Add literal
expected tool names and canonical lifecycle (initialize, initialized, tools).
Run both stdio and loopback/ASGI HTTP; preserve assertions on JSON content type,
GET/SSE rejection and retained tool schemas/results. Essential assertions:

```python
self.assertNotIn("resources", initialized["result"]["capabilities"])
for method, params in (
    ("resources/list", {}),
    ("resources/templates/list", {}),
    ("resources/read", {"uri": "v8std://llms.txt"}),
    ("resources/read", {"uri": "v8std://llms-full.txt"}),
    ("resources/read", {"uri": "v8std://ai/pages.jsonl"}),
    ("resources/read", {"uri": "v8std://missing"}),
    ("resources/subscribe", {"uri": "v8std://llms.txt"}),
    ("resources/unsubscribe", {"uri": "v8std://llms.txt"}),
):
    reply = rpc(method, params)
    self.assertEqual(reply["error"]["code"], -32601)
    self.assertNotIn("result", reply)
```

Here `rpc` is the test's real transport round-trip returning the complete
JSON-RPC envelope, not a mocked reply. Check matching request ID, both cold
and ready states and a failing data facade to catch accidental data access.
Provide one shared fixture helper if needed; do not duplicate whole protocol
drivers or assert framework internals instead of wire output.

For generation preparation, make unintended bulk formatting fail while real
`build_generation` still creates a searchable index from verified bytes.
Check a pickle roundtrip and real local-prefix page presentation. Retain the
same archive/namespace and exercise warm/offline reuse. Do not replace
same-generation assertions with source-text or `hasattr` checks alone.

- [ ] **Step 2: Observe and record RED.**

Run the new module with the pinned interpreter:

```bash
/tmp/v8std-final-gates.e7aqas/venv/bin/python -m unittest tests.test_v8std_mcp_tools_only -v
```

Expected failures: Resources capability is present, resource requests succeed,
or generation construction invokes the unwanted bulk formatter. An import
error or invalid fixture is not the expected RED; repair that test setup first.

- [ ] **Step 3: Implement the common runtime boundary.**

Remove the three `@server.resource` functions and change `MCP_API_PROFILES`
to `["legacy-tools"]`. Add a private adapter after FastMCP construction:

```python
def _disable_resource_handlers(server: FastMCP) -> None:
    for request_type in (
        mcp_types.ListResourcesRequest,
        mcp_types.ListResourceTemplatesRequest,
        mcp_types.ReadResourceRequest,
        mcp_types.SubscribeRequest,
        mcp_types.UnsubscribeRequest,
    ):
        server._mcp_server.request_handlers.pop(request_type, None)
```

Import `mcp.types as mcp_types`. Keep the FastMCP constructor, tool decorators,
stdout/lifecycle and other capabilities unchanged. The wire tests protect this
deliberate pinned-SDK adapter; do not fork SDK or override transport responses.

In `build_generation`, retain index construction and canonical path catalog,
but remove parsing/presentation that exists only to populate `resources`:

```python
return IndexGeneration(snapshot.metadata["corpus_id"], index, canonical, paths)
```

Remove `SnapshotIndex.read_resource_text` and, after checking callers, the
legacy index Resource fetch method and its Resource-only limits/cache fields.
Keep shared `_fetch_url`, parser, body limits, snapshot validators and site
archive files required by actual index or loader paths. No corpus format change.

- [ ] **Step 4: Migrate affected lifecycle tests and docs without losing coverage.**

Replace resource positive assertions with tools and negative resource probes.
Preserve real backpressure shutdown coverage: build a valid page fixture with
12,000 non-BMP characters in `body_markdown`, update its vector text hash using
the existing fixture helpers, then request `v8std_get_page`. Assert the real
encoded response exceeds the test pipe buffer before relying on blocked output;
exercise EOF and SIGTERM without unbounded waits. A sequence of bounded tool
responses is also valid if it demonstrably fills the pipe. Do not keep a test
expecting a 2 MiB resource response, or silently delete shutdown assertions.

Update combined tests to validate real server capabilities/tool behavior.
Document five tools with no MCP Resources; preserve all public website and
installation URLs. Explain resource clients must use tools and that public
web files remain downloadable. Do not rewrite historical spec/operation reports.

- [ ] **Step 5: Run focused GREEN and self-review.**

```bash
/tmp/v8std-final-gates.e7aqas/venv/bin/python -m unittest tests.test_v8std_mcp_tools_only tests.test_v8std_mcp_server tests.test_v8std_mcp_index tests.test_v8std_mcp_runtime tests.test_v8std_mcp_snippet tests.test_v8std_mcp_combined tests.test_v8std_mcp_snapshots -v
```

Record counts, skips, exact RED/GREEN outputs and why each fixture catches a
production regression. Commit only this task's files; controller supplies a
separate spec/quality review before Task 2. Full suite is an end-of-plan gate.

### Task 2: Align new-runtime release smoke without weakening legacy recovery

**Files:**

- Modify: `scripts/v8std_mcp_release.py`, `tests/test_v8std_mcp_release.py`.
- Modify only if needed for affected assertions: `tests/test_v8std_mcp_release_docker.py`.
- Read: `tests/mcp_release_fixture.py` and its pinned historical `LEGACY_SHA`; do not replace the legacy-source fixture with current code.

**Interfaces:**

- Consumes: Task 1's real HTTP tool-only API and existing health/release identity.
- Preserves: `smoke(url, record, deadline)` returning verified health; `rpc(...)`
  remains strict about successful results. Add a private complete-envelope
  helper only if needed to verify expected resource errors without swallowing
  unexpected transport/protocol failures.
- Preserves: `HostAdapter.legacy_check`, pinned old source/cache verification,
  rollback, attestations, held-generation bracket and all deadlines.

- [ ] **Step 1: Prove the current new-runtime smoke rejects a valid tools-only server.**

Use the existing real runtime fixture from `tests/mcp_release_fixture.py` and
the held identity setup in release tests. Add regressions that call the actual
`smoke`, not an adapter fake that simply returns healthy. A tools-only runtime
must pass; an initialized response advertising Resources or a successful
resource read must fail. Expected checks include:

```python
health = release.smoke(runtime_url, record, time.monotonic() + 30)
self.assertEqual(health["hold_token"], record["hold_token"])
self.assertEqual(health["runtime_sha"], record["runtime_source_sha"])
```

`runtime_url` and `record` are the existing local fixture's real running
runtime and expected held-release record. For error branches, controlled HTTP
responses may replace the network boundary, but execute real `smoke`/RPC parsing
and assert the actual rejected category and request IDs. Do not patch smoke
itself. Record RED caused by the obsolete required resource catalog.

- [ ] **Step 2: Replace only the new-runtime resource expectation.**

Retain every existing health identity, useful search/page response and
generation bracket check. Require no `resources` key in initialize capabilities.
Exercise the remaining retained tools (`v8std_get_related` and
`v8std_explain_diagnostics`) with valid bounded inputs. Replace the successful
resource catalog query with a negative probe whose full JSON-RPC envelope has
matching ID, code `-32601`, no `result` and no content payload. Use the same
deadline and bounded HTTP reader; do not catch all `ReleaseError` and treat it
as expected resource denial.

Keep `legacy_check` resource reads unchanged: they prove restoration of the
specifically pinned historical runtime/cache, not support by the new server.
The design already identifies that rollback to an old version restores its
Resources. Do not broaden this task into automatic version detection, new
release schema, host settings, CI polling fixes or actual deployment.

- [ ] **Step 3: Run release regression GREEN, self-review and report.**

```bash
/tmp/v8std-final-gates.e7aqas/venv/bin/python -m unittest tests.test_v8std_mcp_release tests.test_v8std_mcp_tools_only -v
```

Record real fixture/recovery coverage, new smoke branch tests, RED/GREEN output
and any skipped optional Docker cases. Commit only task-owned files and obtain
task-scoped spec/quality review before Task 3.

### Task 3: Update acceptance and verify the new local candidate

**Files:**

- Modify: `scripts/check_mcp_container.py`, `scripts/check_mcp_load.py`.
- Modify: `tests/test_v8std_mcp_distribution.py`, `tests/test_v8std_mcp_load.py`; add focused acceptance-helper tests there as needed.
- Create: `spec/operations/2026-09-15-mcp-tools-only-verification.md`.
- Read only: Dockerfiles, Compose, snapshot fixture/format helpers, existing operation reports and source-provenance checks.

**Interfaces:**

- Consumes: Task 1's tool-only JSON-RPC boundary and unchanged old-format archive.
- Keeps: `request(number)` and `valid_reply(kind, body)` harness interfaces.
- Replaces: bulk `resource_hash` evidence with `page_content_hash` for real
  `v8std_get_page("std437")` output; report uses `page_content_hashes` and separate
  rejected-resource probe accounting, never successful resource throughput.

- [ ] **Step 1: Add acceptance-helper RED tests.**

Exercise actual helper behavior with complete hand-derived envelopes:

```python
requests = [load.request(number) for number in range(20)]
self.assertEqual({msg["method"] for _, msg in requests}, {"tools/call"})
self.assertEqual({msg["params"]["name"] for _, msg in requests}, {
    "v8std_search", "v8std_get_page", "v8std_get_related",
    "v8std_explain_snippet", "v8std_explain_diagnostics",
})
self.assertFalse(load.valid_reply("page", b'{"error":{"code":-32601}}'))
```

Reject success counters fed by errors, empty replies or stale controlled-page
content. The page-content expectation must come from the staged fixture's
explicit body, not by invoking the response-hash function on both sides.
Record existing helper failures before changing their implementation.

- [ ] **Step 2: Update real container and mixed-load paths.**

Container RPC helpers need a complete-envelope path for expected `-32601`
errors; keep ordinary successful calls strict. Verify capability absence and
all negative resource methods over HTTP/stdio, with canonical lifecycle and
warm cache. Check all five tools; direct-runtime exact catalog and Gateway's
aggregate tool catalog are separate conditions, not a flag enabling Resources.

Use the old 20-slot load shape with its final three slots assigned to
`v8std_get_related` instead of Resources. Validate real related results. Keep
initialize/discovery/admission separate from tool-data latency and report
negative resource probes independently. Reject unexpected SSE responses in
the JSON-only profile. Keep static archive downloads, idle reconnection,
logging, CPU/RAM/FD samples, bounded cleanup and same-image controlled switch.

For content refresh, stage two valid archives with an actual change near the
start of `std437.body_markdown`, so it is visible within the retained page
budget. Update the matching vector/body hash with existing fixture helpers.
Fetch that page before and after refresh and compare its returned body hash
with the two distinct fixture expectations. Identity-only changes do not pass.
Do not relax snapshot limits or derive expected hashes from runtime presentation.

- [ ] **Step 3: Observe GREEN and build a source-identified local image.**

```bash
/tmp/v8std-final-gates.e7aqas/venv/bin/python -m unittest tests.test_v8std_mcp_distribution tests.test_v8std_mcp_load tests.test_v8std_mcp_tools_only -v
```

Commit the task's code before building so the label identifies exact inputs.
Run `docker buildx build --platform linux/arm64 --build-arg SOURCE_SHA=<verified-commit>
--load -f Dockerfile.mcp -t v8std-tools-only-mcp:<short-sha> .` on this arm64 host.
Resolve actual SHA and substitute it; never write a fake provenance label.
Inspect image ID/revision/non-root config and compare the copied runtime sources
to the committed files. Use the retained local static-site image only after
verifying its corpus identity still matches the unchanged corpus inputs.
If unavailable, build an exact-source local site image with existing builder.

Run updated `check_mcp_container.py` on these local images, then updated
`check_mcp_load.py` with two explicitly synthetic changed-content fixtures.
Use 60 seconds, 8 active requests, 64 maintained idle connections; retain
existing container resource limits, discovery burst and static archive traffic.
Consult current `--help` for concrete argument names rather than invent flags.
No production traffic, registry push, privileged container or socket mount.
Remove only the containers/networks/volumes created by these checks.

- [ ] **Step 4: Record candidate evidence and finish focused verification.**

Write the operation report with exact source SHA/image ID, platform, cache
origin, commands, successful tools and rejected Resources, changed content
hashes, profile counts/errors/p95/p99/RPS/RAM and cleanup. Old performance
reports remain unchanged. Distinguish native arm64 verification from an
unperformed amd64 or production capacity test. Record any unavailable check
as incomplete, not as a pass.

Controller runs strict build, full suite, semantic impact, CLI impact and
`validate --merge-ready` after the task review. Missing gates in the pre-existing
container/CI plans block whole-branch integration, not permission to falsely
mark those plans done. Complete this task only after its scoped review and
required local candidate evidence are available.

## End-of-plan verification and integration boundary

- [ ] Recheck actual diff against the approved five-file design package and preserve frozen main documents.
- [ ] Run strict build first and then the full unittest suite with the existing pinned dependency environment.
- [ ] Run architecture validate/impact, declared conformance modules and diff checks; record merge-ready outcome separately.
- [ ] Preserve review/evidence for this plan and resolve its findings before marking its tasks complete.

Commit and local merge are integration actions, not plan checkboxes. A local
merge is permitted only when the whole branch passes required gates; no
feature-to-main push, production deployment or publishing is authorized here.
