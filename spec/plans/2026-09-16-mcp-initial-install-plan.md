---
schema_version: 1
kind: plan
id: mcp-initial-install
design: design:mcp-clean-host-installation
implements:
  - invariant:MCP_RELEASE_ACCEPTANCE_HAS_REAL_ORIGIN
---

# MCP Initial Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Реализовать принятие первого контейнера и его crash recovery без фиктивного predecessor.

**Architecture:** Отдельный `InitialInstallController` использует существующие envelope, lock, HostAdapter, durable journal и real smoke. Первоначальная попытка не меняет обычный deploy или legacy bootstrap. Provisioning и перенос publication store — отдельные планы того же design.

**Tech Stack:** Python 3.12, stdlib, unittest, существующий process/HTTP fixture и закреплённый MCP SDK.

**Spec:** [Design](../designs/2026-09-16-mcp-clean-host-installation-design.md), [runtime contract 1.1](../contracts/mcp-release-runtime-v1-r1.md), [acceptance invariant](../invariants/mcp-release-acceptance-has-real-origin.md).

## Global Constraints

- Работа в основном checkout, в feature-ветке. Нет push, PR, worktree, подключения к production или переустановки ОС.
- Только root-only `initial-install`, `_initial-install`, `initial-install-recover`; publisher PUBLIC/sudoers не расширяются.
- Первый journal имеет `kind: initial-install`, не имеет predecessor; COMMITTED записывается durable после public MCP/static smoke и до active pointer.
- До COMMITTED recovery возвращает maintenance 503 с Retry-After и останавливает только owned candidate. Неподтверждённый cleanup означает RECOVERY_REQUIRED.
- После COMMITTED recovery восстанавливает принятый контейнер, включая потерю active pointer. Нельзя повторно установить первый runtime после удаления pointer.
- Initial transaction/readiness/smoke/stop/reserve: 300/90/30/45/60 s. Ordinary reserve 180 s и loader 360 s/read 20 s не меняются.
- Образ и corpus уже на host: initial path не выполняет pull/build, не требует legacy backup или выдуманного network evidence.
- Пять tools, POST JSON, отсутствие Resources, persistent cache, static delivery и private usage history сохраняются.
- Никаких private host/account/domain/path значений в публичных изменениях; только продуктовые fixed paths и синтетические fixtures.
- TDD с наблюдаемым RED/GREEN; focused tests между изменениями, strict build и полный suite после всех clean-host компонентов, не одновременно с генерацией сайта.

## File boundaries and scope

Существующий release module большой: добавляется только новый controller и узкие
HostAdapter методы, без переноса или переписывания обычного rollout. Новые fixtures
по возможности находятся в `tests/mcp_initial_install_fixture.py`, чтобы не
разрастался legacy fixture. План реализует acceptance invariant, но не объявляет
весь release contract/design выполненным: host provisioning, corpus handoff и
фактическая внешняя поставка имеют отдельные доказательства.

### Task 1: Implement initial acceptance and recovery

**Files:**

- Modify: `scripts/v8std_mcp_release.py`.
- Create: `tests/test_v8std_mcp_initial_install.py`, `tests/mcp_initial_install_fixture.py`.
- Modify only for a shared fixture seam: `tests/mcp_release_fixture.py`, `tests/test_v8std_mcp_release.py`.
- Read: `deploy/container/release-entry.py`, `deploy/container/release.sudoers`, existing recovery units, `tests/test_v8std_mcp_release_docker.py`.

**Interfaces:**

- `InitialInstallController(Controller)` produces `submit(raw: bytes) -> dict`, `execute() -> dict`, `reconcile(journal: dict) -> dict`.
- Constants `INITIAL_INSTALL_AUTH = Path('/etc/v8std-release/initial-install.json')`, `INITIAL_RECOVERY_RESERVE = 60`, `MAINTENANCE_UPSTREAM = b'server 127.0.0.1:9 down;\n'`.
- `HostAdapter.initial_authorization(envelope)` verifies trusted fixed-path JSON with exactly schema_version 1, mode clean-host, envelope_sha256 of canonical envelope and allow_no_predecessor true; returns no new authority.
- `HostAdapter.initial_host(journals, deadline)` proves absence of legacy unit/app/config, active/predecessor, dirty runtime inboxes, unknown journal states, unowned runtime containers/slots, and unmanaged upstream. Terminal failed initial attempts are allowed only with confirmed cleanup; their stopped owned containers/cache may remain. Any non-initial historical journal or accepted initial journal denies a new attempt.
- `HostAdapter.initial_capacity(candidate, deadline)` enforces disk/FD and available memory at least the configured single-container memory plus 128 MiB, never old/new overlap/network evidence. Factor only genuinely shared basic probes from capacity; ordinary policy remains unchanged.
- `HostAdapter.maintenance(deadline)` writes only the fixed managed include, validates/reloads nginx and confirms the public `/mcp` returns 503 with Retry-After using a bounded HTTP check that handles HTTPError explicitly. It does not stop nginx/static/TLS or touch vhosts.
- Existing `bootstrap_prepared(candidate, deadline)` may supply the preloaded exact image/archive check; if renamed to a neutral private helper, retain the bootstrap wrapper and tests.
- `Controller.recover` dispatches `kind: initial-install` before ordinary/legacy logic; `schedule` allows initial-install only for root CLI. Received initial attempts found by recovery fail closed and require a new ID after cleanup, rather than inventing acceptance.

- [x] **Step 1: Write behavioral RED tests using real journals and runtime smoke.**

Build a fixture around the existing process runtime and edge; substitute only
host OS/Docker/systemd boundaries. The actual controller, journal writes,
HTTP lifecycle, five-tool smoke and static hash checks remain real. A stopped
container is distinct from an absent container; an inspect error is neither.

```python
result = initial.submit(canonical_json(envelope))
self.assertEqual(result['state'], 'RECEIVED')
result = initial.execute()
self.assertEqual(result['state'], 'COMMITTED')
self.assertTrue(result['cleanup_complete'])
self.assertFalse((root / 'predecessor.json').exists())
self.assertEqual(read_record(root / 'active.json')['release_id'], envelope['release_id'])
(root / 'active.json').unlink()
recovered = Controller(root, adapter).recover()
self.assertEqual(recovered['state'], 'COMMITTED')
self.assertEqual(read_record(root / 'active.json')['release_id'], envelope['release_id'])
```

Explicitly cover: same duplicate (even expired) returns same outcome; mutated
duplicate and stale sequence reject; clean/legacy/active/foreign upstream/foreign
container/corrupt record reject before runtime effects; policy runtime_enabled
true rejects; altered/non-root-writable authorization rejects. Root-only CLI and
restricted entry reject initial verbs for publisher identity. Failed retry needs
confirmed cleanup and higher sequence, while COMMITTED forever prohibits a second
initial attempt. Public index archive remains readable during maintenance.

- [x] **Step 2: Observe RED.**

Run `python -m unittest tests.test_v8std_mcp_initial_install -v` using the
verified locked dependency interpreter selected for this checkout. Start with
an assertion that the required controller/CLI behavior exists so absence is a
clear assertion failure, not an unrelated fixture/import failure. Record command,
failure and missing behavior in the private execution report.

- [x] **Step 3: Implement the durable state machine and bounded host adapters.**

Use the existing common release lock and `Controller.existing` duplicate logic.
Check genuine empty-host predicates for a new ID. Save a RECEIVED journal before
scheduling; schedule failure retains a reconcilable receipt. Execute rechecks
authorization/policy/host ownership under lock before effects. Build candidate
from exact envelope, descriptors, first policy port and deterministic name/token.

```python
work = deadline - INITIAL_RECOVERY_RESERVE
journal = {'kind': 'initial-install', 'envelope': envelope,
           'state': 'RECEIVED', 'intent': 'verify',
           'candidate': None, 'cleanup_complete': False}
```

Verify provenance/main ancestry/config/manifest/preloaded image/archive and basic
capacity before VERIFIED; persist candidate and pins before start; mark PREPARED,
hold with exact manifest, internal readiness and full smoke, READY, switch, public
MCP/static smoke, SWITCHED, COMMITTED. Active pointer and resume/cleanup follow
COMMITTED. Pins contain the candidate archive without manufacturing predecessor.
Use journal intents before side effects for recovery observability.

On exception reread durable journal: a successfully persisted COMMITTED followed
by an fsync error is accepted, not failed. Before commit attempt maintenance and
owned stop within the reserved budget; save FAILED only once both are confirmed.
If one operation fails, still attempt the other when safe and budget remains,
then save RECOVERY_REQUIRED. Preserve candidate/cache/journal evidence. Never
clear runtime state by recursive deletion. Do not re-enable runtime policy.

Accepted reconciliation reuses held manifest and checks real identity, restores
the accepted container if stopped/missing and confirms public service before
repairing pointer/resuming. Ordinary later releases supersede initial history:
recovery must not switch back to the first image after a newer accepted release.

- [x] **Step 4: Add crash, uncertain-write and boundary regressions.**

Inject process exits after each durable transition and before/after candidate
start, switch, COMMITTED write and active pointer write. Recreate controller and
recover against surviving on-disk state, not a mock of recovery. For precommit
states assert maintenance response and no running candidate; for committed state
assert accepted identities and repaired active pointer. Stop/maintenance failure
must remain RECOVERY_REQUIRED. Prove uncertain persistence by letting atomic write
reach disk then raising; also test a failure before rename. Assert no predecessor
or legacy start, and static archive hash unchanged. Exercise a timeout with live
cleanup reserve and the unchanged ordinary rollback tests.

```python
self.assertEqual(recovered['state'], 'FAILED')
self.assertTrue(recovered['cleanup_complete'])
self.assertEqual(edge.request('/mcp', method='POST').status, 503)
self.assertFalse(adapter.inspect(candidate, deadline)['State']['Running'])
```

Here edge and adapter belong to the real-process fixture, and error paths use
explicit before/after fault points. Do not substitute a canned healthy smoke.

- [x] **Step 5: Focused GREEN, self-review and scoped independent review.**

Run `python -m unittest tests.test_v8std_mcp_initial_install tests.test_v8std_mcp_release tests.test_v8std_mcp_tools_only -v`.
Record actual counts and skips; distinguish process-fixture proof from real-host
or privileged-container proof. Check ordinary deploy/bootstrap regression,
no credentials in status, exact CLI restriction and unchanged runtime budgets.
Complete this task only after independent spec/quality review findings are fixed.

## Integration evidence

- [ ] Repeat semantic impact, run CLI impact/validation and the acceptance fitness module against the final clean-host diff.
- [ ] Run strict build and full suite on the integrated candidate, without concurrent site generation.

Local merge follows repository gates after companion plans are complete. Push,
publication, initial host activation and Catalog submission are separate results,
not checkboxes that can be inferred from local tests.
