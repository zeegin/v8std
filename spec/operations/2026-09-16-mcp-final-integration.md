# MCP container distribution: final local integration

Verified code: `53126014af1d87abf10515a36d8c6925f6310aff`, signature G.
Integration base: `b7bef11e145a188b30e7a7b17df2be4cb1acbd0c`; remote main
was read-only rechecked against that exact value. Primary checkout, no worktree.
This report and plan checkoffs are later documentation, not new runtime inputs.

## Review and fixes

Task1–5 retain their accepted local evidence. Task6 includes the separately
reviewed parser, private logging, CI/process and tools-only integration slices.
Whole-branch review of `b7bef11..816b592` found no Critical, two Important and
one Minor finding. All three were accepted, planned before code, and repaired
in one combined wave, `e2e3526..5312601`. Its independent scoped re-review
approved all three as addressed, with zero new findings of any severity:

- Real image-pair smoke accepts Docker inspect's one-object array while retaining
  strict parsing, exact identity/profile checks and cleanup. Tests execute the
  actual helper rather than substituting local_smoke itself.
- A lost post-Pages reference acknowledgement cannot age out a potentially
  current archive. Durable publish journals protect uncertainty; reconciliation
  fsyncs displaced archives' full seven-day grace before changing the pointer.
- The native current-runtime fixture uses the actual tools-only candidate with
  all16 COPY inputs verified. The legacy rollback fixture remains unchanged.

The earlier three CI findings were independently approved in `149730d..816b592`:
QUEUED waits, COMMITTED waits for cleanup, and absent/expired history plus404
never authorizes manifest-less Pages publication. Detailed RED/GREEN and native
fixture commands remain in [container verification](mcp-container-verification.md)
and [CI repair verification](2026-09-16-mcp-ci-repair-verification.md).

Process-v2 RED used the actual CLI in a standalone fixture: it failed on the
old v1 path before implementation. The first corrected process run passed59/59.
Publication eligibility RED/GREEN covers main/PR/fork/tag/stale/failed gates,
independent publication/runtime activation and real ingress/journal boundaries.
The final full suite repeats those modules; no structured document inherited
from main is changed or deleted.

## Final stable-code checks

Runner: `/tmp/v8std-final-gates.e7aqas/venv/bin/python`, Python3.12.10 and
hash-locked dependencies; repository `.venv` untouched.

- Focused publication/release:157/157 pass in224.584s, including actual actionlint.
- Native nginx/static/hold tools-only fixture:1/1 pass in10.505s after a RED
  `resource_capability` failure. Six real crash/recovery cuts cover retention.
- Strict build: exit0,3283 vectors,1430 articles,0 violations,3 license texts.
  Pinned local builder `v8std-final-ci:108b91f`, ID
  `sha256:cffef3a1b208b462e5f2ca4b9266b1d6ca2c99e031d0170b2c04f1398583a722`,
  network none, user501:20, cap-drop ALL, no-new-privileges.
- Only after strict build exited: full suite740 tests in361.263s,
  727 passed,13 skipped,0 failures/errors. Public monitoring retirement's native
  Docker tests were explicitly enabled. No source writes or concurrent index
  generation occurred during the run.
- Semantic impact, CLI impact and ordinary validation against main passed.
  After the evidence-backed plan checkoffs, `validate --merge-ready --base-ref
  main` exits0, with no incomplete-plan exception. Documentation-focused
  architecture/process tests pass59/59 in5.238s; `git diff --check` exits0.

```sh
V8STD_MONITORING_RETIREMENT_DOCKER=1 /tmp/v8std-final-gates.e7aqas/venv/bin/python -m unittest discover -s tests -v
/tmp/v8std-final-gates.e7aqas/venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
/tmp/v8std-final-gates.e7aqas/venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready
```

Raw logs: `/tmp/v8std-ci-fix-gates.ZiEIAe/final-strict-build.log`,
`final-full-suite.log`, `final-impact-main.log`. The13 skips are5 opt-in image/
build checks,4 native-root logging checks,2 logging-Docker and2 release-Docker
checks. Separate fixture evidence is not counted as full-suite passes.

## Artifact and capacity boundaries

The actual input-identity helper confirms5312601 and the verified candidate
`c4c0878a3c5e12323358f139e070253bd9e8ac5a` have identical inputs:

- Runtime: `9f580a029745e00395e4a49b1e79c9f1d4ee0f9f6c583d614f5ac02abfa1e35a`.
- Corpus: `021a01ae0e5c06eac49f1625c9a3b06b5e3619535f9f1f1216f3059e49a14f08`.

The final CI helper and host-controller repairs are outside Dockerfile.mcp's
COPY closure. Prior [tools-only candidate evidence](2026-09-15-mcp-tools-only-verification.md)
remains applicable; no old image has been relabelled. That bounded local run
used8 active clients and64 maintained idle sockets:2383 successful tool calls,
38.22RPS, p95≈225ms, p99≈267ms,0 unexpected errors, plus static/denial checks.
This is not100000-agent capacity, native amd64 capacity or target-host overlap proof.
The recorded minor limitation remains: updated body content was checked after
switching to process B, not independently after refreshing process A before the
switch; separate in-process refresh tests cover that behavior.

## Semantic impact and preserved decisions

Manual actual-diff check: requirements are the approved distribution, controlled
delivery, monitoring retirement and tools-only scope; ADR directions are
preserved. Invariants retain atomic complete snapshots, recoverable predecessor,
single combined runtime, POST-only JSON, private operational data and one site
override without public fallback. Versioned successors encode the intentional
Resources removal; historical schemas/contracts are not rewritten. CI and host
are producer/consumer boundaries, not new trusted absence signals. All governed
paths were reviewed, including test/operations glue; historical monitoring
matches from CLI impact do not reactivate retired designs. No unresolved
implementation-versus-design contradiction remains after the final fix wave.

Rulings retained in original decision order, including superseded ones:

1. Use a supervised process for cancellable snapshot I/O/build and trusted
   in-process generation transfer, recreating process-local locks. Never load
   downloaded/cached pickle. If wrong, startup/transfer RSS requires executor
   redesign; local image/memory checks bound the current evidence.
2. Use pinned markdown-it-py4.0.0 for source-preserving CommonMark rather than a
   second incomplete grammar. If wrong, parser memory/CPU or packaging requires
   rework; canonical source/hashes and rank checks remain unchanged.
3. Originally retain the60s loader bound and treat QEMU failure as failed
   emulated acceptance, not native capacity evidence. The user subsequently
   explicitly replaced the bound with360s; the old number is not current policy.
   Native performance remains unproven until measured on the target host.
4. Missing public state is UNKNOWN during read-only candidate planning; Pages
   needs verified prior state or a newly committed and externally verified
   archive. If sequencing is wrong, first-publication orchestration needs repair;
   no operator absence flag or authority expansion was introduced.
5. Protect uncertain publication journals until acknowledged reconciliation and
   persist displaced grace before advancing the reference. If no acknowledgement
   arrives, archives may remain indefinitely and disk capacity can reject a new
   publication. This cost is preferred to deleting a possibly public current
   object; real journal/crash/GC tests and independent review cover the rule.

## External handoff — not performed by these gates

Local plan completion is not external release completion. No push, registry/
Pages publication, GitHub settings/secret change, Docker Catalog submission,
public comment, production setup, live GC or service switch was performed.
Production protection/environments/credentials, backup-and-restore readiness,
host installation/static-index route, trusted CI multiarch publication with
anonymous exact-digest/default-source checks, and first runtime activation
remain separate prerequisites in the [activation runbook](mcp-container-activation.md).
The two-hour migration window needs an exact date/time before a live switch.

The prepared Docker Catalog entry must reference the same published artifact.
Submission/review and repeated default Toolkit calls without global
`--long-lived` remain external acceptance; repairing the local Docker test
catalog generator is not a prerequisite. No100000-agent support is promised.
