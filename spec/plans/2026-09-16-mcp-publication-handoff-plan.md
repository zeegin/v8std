---
schema_version: 1
kind: plan
id: mcp-publication-handoff
design: design:mcp-clean-host-installation
implements: []
---

# MCP Publication Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Сохранить опубликованные immutable индексы, доказательства происхождения и publication continuity при переносе на пустое хранилище.

**Architecture:** Операторский CLI делегирует ограниченному handoff модулю. Handoff — закрытый каталог с проверяемым manifest, а не произвольный tar/backup ОС. Import сначала проверяет весь комплект и лишь затем устанавливает immutable объекты и durable state под общим release lock.

**Tech Stack:** Python 3.12 stdlib, существующий snapshot validator, GitHub CLI attestations, unittest.

**Spec:** [Clean-host design](../designs/2026-09-16-mcp-clean-host-installation-design.md), [runtime contract 1.1](../contracts/mcp-release-runtime-v1-r1.md).

## Global Constraints

- Работа только в feature-ветке основного checkout; без production, push, публикации, worktree или PR.
- Не переносить legacy runtime/OS, сторонние сервисы, секреты, закрытые usage logs или фиктивные runtime journals.
- Сохранять все current/uncertain/grace archives, manifests, publication receipts/references и sequence continuity, включая terminal FAILED receipts.
- Не отключать provenance/main verification; несовпадение блокирует активацию. Imported receipt — история, не новая публикация Pages.
- In-flight publication должна быть reconciled до export; export сам не завершает и не выдумывает outcome.
- Import не запускает MCP, не переключает nginx, не активирует CI, не запускает GC и не меняет Pages.
- CLI операторский root-only и не включается в publisher PUBLIC/sudoers; shared release.lock сериализует import/export с publisher.
- TDD RED/GREEN, реальные файлы и snapshot bytes; подмена только внешних GitHub/Docker процессов. В публичных файлах нет частных параметров установки.

## Scope and frozen interface

Этот компонент проверяется отдельно; весь design/contract не отмечается
IMPLEMENTED до host provisioning и полной приёмки. Production transfer — внешний
этап. Библиотечные root/static_root параметры нужны тестовому filesystem и
внутреннему вызову; CLI их не принимает.

### Task 1: Implement strict handoff export, validation and resumable import

**Files:**

- Create: `scripts/v8std_mcp_handoff.py`, `scripts/v8std_mcp_provision.py`, `tests/test_v8std_mcp_handoff.py`.
- Modify narrowly: `scripts/v8std_mcp_release.py`, `tests/test_v8std_mcp_release.py` for the publication high-water prerequisite proved missing by the real regression below. Do not alter initial-install/ordinary runtime controllers.
- Read: release `Publisher`, envelope/descriptor helpers, snapshot format, existing publication fixtures.
- `v8std_mcp_provision.py` initially owns only root-only handoff subcommands. Host setup will extend this same CLI in its separate plan, without changing these interfaces.

**Interfaces and schema:**

```python
def export_handoff(root, static_root, destination, envelope, verifier, *, now=None):
    # returns {"schema_version": 1, "handoff_sha256": str,
    #          "archives": int, "publication_sequence": int}
    ...
def validate_handoff(source, expected_sha256, verifier):
    # returns validated manifest after file/schema/cross-reference/provenance checks
    ...
def import_handoff(root, static_root, source, expected_sha256, verifier):
    # returns {"state": "IMPORTED", "handoff_sha256": str,
    #          "publication_sequence": int}; exact duplicate is idempotent
    ...
```

`verifier` is a production `HandoffVerifier` with methods
`capture(archive, header, proof_dir)`, `verify(archive, header, proof_dir)`,
`capture_runtime(envelope, proof_dir)`, `verify_runtime(envelope, proof_dir)`.
It uses existing workflow/ref/source restrictions and current main ancestry,
not a new root of trust. Tests replace only command/network boundaries.

CLI: `handoff-export --envelope FILE --output DIRECTORY`,
`handoff-verify --input DIRECTORY --sha256 HEX`,
`handoff-import --input DIRECTORY --sha256 HEX`. Envelope is validated with
expired=True because transfer precedes an individually authorized initial attempt;
it fixes artifacts, not its future deadline/authorization. Root/static paths come
from trusted release policy. Input/output directory paths are operator inputs,
never CI inputs. Export output must not exist and cannot be within managed state,
static store or repository. Output mode 0700, regular files 0600.

`handoff.json` exact root fields: schema_version=1, envelope (unchanged major-1
envelope), created_at (nonnegative finite timestamp), publication_sequence
(maximum of all receipt sequences), current_sequence (current-index sequence),
files (relative path => object with exactly sha256 and bytes). Its SHA-256 is
returned separately and must be supplied independently on verify/import.

File allowlist: `state/current-index.json`,
`state/publications/ID.json`, `state/manifests/HEX.json`,
`state/references/HEX.json`, `objects/HEX/snapshot.tar.gz`,
`proofs/HEX.jsonl`, `proofs/runtime.jsonl`, `proofs/runtime-index.json`,
`proofs/runtime-platform.json`. Only these paths, no links/devices/hardlinks,
extra unlisted files, duplicate JSON keys, traversal or implicit recursive copy.
At most 10000 entries, manifest at most 4 MiB, total at most 8 GiB, each snapshot
at most existing MAX_ARCHIVE_BYTES, state records at most 128 KiB, proofs at most
4 MiB. Use streaming hashes/copies; validate snapshots with existing bounded parser.

- [ ] **Step 0: Repair the consumer's missing publication high-water guard.**

A prerequisite probe against real ingest/Publisher reproduced admission and
COMMITTED sequence40 after real FAILED41 with current-index37. Preserving those
bytes cannot by itself fix ordering. This is an implementation defect under the
approved publication continuity requirement, not permission to alter history.

Add one bounded shared publication-history helper in release.py that validates
receipt headers/IDs and computes the maximum sequence including FAILED receipts.
Under release.lock, ingest handles an exact existing-ID duplicate first, then
requires every new ID to have a strictly greater sequence before receiving/staging
new archive bytes. Mutated duplicate still rejects. Worker publish must also
reject an older unverified RECEIVED record against other receipt sequences so a
queued historical request cannot bypass admission. Exclude that exact record
from the comparison. Preserve legitimate VERIFIED/RECOVERY_REQUIRED reconciliation
and exact terminal duplicates; already exposed immutable archive completion is
not a new publication, and current-index must never regress. Wrong/unknown
history fails closed rather than silently reducing the watermark.

An existing handoff-import receipt in PREPARED or invalid shape denies new
publication ingress as well as runtime activation; COMMITTED must have a
watermark consistent with the actual imported history (newer later receipts are
valid). The receipt does not substitute for missing imported history. Reuse the
existing strict receipt validation where possible, without a circular import.

```python
publish('current', sequence=36)
reference('ack', sequence=37)
fail_verification('failed-latest', sequence=41)
with self.assertRaisesRegex(ReleaseError, 'stale_sequence'):
    ingest_new('older', sequence=40)
self.assertEqual(read_record(root / 'current-index.json')['sequence'], 37)
```

These helpers in the new regression test execute real ingest/Publisher with only
external gh transport replaced. Retain exact duplicate outcomes for sequences
36/37/41 after later history exists, reject equal sequence/new ID, allow sequence42,
and cover deferred unverified/verified recovery separately. Update the existing
stale-reference test to expect earlier rejection at ingress, preserving its actual
GC/reference assertions. Run focused publication tests RED then GREEN before
building handoff; final handoff tests consume this corrected real boundary.

- [ ] **Step 1: Write RED for history preservation and strict import.**

Prepare real published snapshots with: current acknowledged archive, newer
uncertain publish, displaced archive within seven-day grace and an old FAILED
receipt with the largest sequence. Also include an older collected archive's
receipt/manifest without bytes; collected unprotected history is valid. Explicit
publication IDs and sequences must be literal fixture expectations.

```python
report = export_handoff(root, store, destination, envelope, verifier, now=1000000)
self.assertEqual(report['publication_sequence'], 41)
import_handoff(empty_root, empty_store, destination, report['handoff_sha256'], verifier)
self.assertEqual(read_record(empty_root / 'current-index.json')['sequence'], 37)
self.assertEqual(read_record(empty_root / 'publications' / 'failed-latest.json')['state'], 'FAILED')
self.assertEqual((empty_store / uncertain_hash / 'snapshot.tar.gz').read_bytes(), uncertain_bytes)
self.assertFalse((empty_root / 'active.json').exists())
```

Check new publication sequence 40 is rejected using the actual Publisher after
import; exact duplicate retains outcome. Check current/uncertain/grace omissions,
archive mutation, inconsistent manifest/current/reference, wrong source/digest,
altered inventory hash, invalid state and unfinished publication are rejected.

- [ ] **Step 2: Observe RED before implementation.**

Run `python -m unittest tests.test_v8std_mcp_handoff -v` with locked runtime
dependencies. Begin with behavioral availability assertion so missing API is a
clear RED, not an unrelated test-fixture import error. Record failure evidence.

- [ ] **Step 3: Implement inventory and provenance boundaries.**

Under lock, reject pending-index and nonterminal/cleanup-pending receipts; accept
only COMMITTED/FAILED histories with validated headers, IDs matching filenames,
distinct positive sequences and sensible reference times. Require an actual
committed reference receipt equal to current-index. Protected set is current,
every nonfailed publish after current acknowledgement, every reference younger
than seven days and the selected runtime envelope archive. Preserve every
present valid immutable archive as a conservative superset, not only protected
ones. Any missing protected archive is an error. Every present object has exact
manifest, reference and a matching committed publication provenance header.

Preserve all known terminal receipts, manifests and reference records even if an
old unprotected archive was already collected. Do not fabricate current-index,
acceptance or reference timestamps. Preserve reference timestamps across import.

Capture signed bundles with `gh attestation download` in a private isolated
working directory; move only its exact digest-named JSONL output into the
allowlisted proof slot. Keep bounded stdout and deadline/process-group termination
behavior of the release command runner; a helper local to handoff may add cwd
without changing global process cwd. Run verification with existing attestation
arguments plus `--bundle` for captured proof, and check source ancestry again.
Capture exact OCI index/platform JSON and validate their digest/membership using
`verify_descriptors`; runtime bundle binds published index digest/source main.
Import rechecks bundles, descriptors, and live main ancestry; saved text claiming
verification is not a substitute for signed evidence. No personal credentials
or ambient user HOME are inherited.

Write file inventory last and fsync directories; partial output lacks a completed
handoff.json and is never accepted. No automatic cleanup of caller output. A
retry uses a fresh output directory; report controlled error codes, not raw CLI
output. Operator keeps expected handoff hash separately from transferred files.

- [ ] **Step 4: Implement fail-closed import and interruption recovery.**

Validate the complete source before target mutation. Under release lock require
no runtime acceptance, slots, active/predecessor, pending jobs or unrelated target
publication/store state. Import journal at fixed root `handoff-import.json`
records exactly schema_version, handoff_sha256, state PREPARED/COMMITTED and
publication_sequence. An existing identical unfinished journal allows resume;
another hash or any mismatching target file rejects. A pre-existing publication
store without this import journal is never adopted merely because some files match.

Persist PREPARED before copies. Install only known destinations, atomically and
without replacing conflicting files. Public objects have directory 0755/file
0644; metadata/proofs stay private. Copy receipts/manifests/references, then
current-index, then mark import COMMITTED after rechecking all target bytes.
Retain proof files under root `handoff-proofs/`; no runtime journal/pins created.
Record sequence watermark in receipt and preserve actual history so existing
publisher duplicate/stale logic continues unchanged. Re-running after COMMITTED
checks identity and returns same result without resetting later history.

CLI must deny non-root before reads, validate trusted input paths/parents and
prevent source/destination aliasing. Tests use a temporary root and bounded
filesystem helper; never expose a production `--root` option. A crash after any
copy or current pointer write resumes only the same verified handoff. Runtime
installation remains prohibited until import is COMMITTED; host installer will
consume this durable receipt before offering the initial runtime command.

- [ ] **Step 5: GREEN, failure tests and independent review.**

Run `python -m unittest tests.test_v8std_mcp_handoff tests.test_v8std_mcp_release -v`.
Test each copy/commit interruption, symlink parent/leaf, FIFO/hardlink, extra file,
huge entry/manifest, unknown key, changed source after validation and mismatching
target. Prove imported unacknowledged/grace protection using actual Publisher.gc
on a disposable fixture with legitimate test pins, never newly invented runtime
pins in import. Prove no secrets/runtime files copied by enumerating the actual
output tree. Review tests and implementation together; record skips honestly.

## Integration evidence

- [ ] Validate architecture graph and handoff focused suite after provisioner CLI integration; run strict build and complete suite at clean-host final gate.

This plan does not claim that any real host has been exported or imported.

## Upstream interfaces

[GitHub attestation download](https://cli.github.com/manual/gh_attestation_download)
and [verify](https://cli.github.com/manual/gh_attestation_verify) define bundle
retrieval and verification. Refresh command support at actual provisioning time;
missing service authentication is a blocker, not permission to bypass provenance.
