---
schema_version: 1
kind: plan
id: mcp-ci-deployment-policy
design: design:mcp-ci-deployment-policy
implements:
  - design:mcp-ci-deployment-policy
  - process:architecture-artifacts@2
requirements:
  - MCP_SERVER_DEPLOYS_AUTOMATICALLY_FROM_VERIFIED_MAIN
  - MCP_AUTODEPLOY_ACTIVATION_IS_CONTROLLED
---

# MCP CI Deployment Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Согласованно включить process v2 в инструменты репозитория и код CI, сохраняя отдельный gate первичной активации production.

**Architecture:** Структура архитектурного графа не меняется; его текущая нормативная версия становится v2. Инструкции, проверки и CI различают разрешённый main release, ещё не включённую автоматизацию и неавторизованные источники запуска.

**Tech Stack:** Существующий Python architecture CLI/unittest, GitHub Actions YAML, Markdown process instructions.

**Spec:** [Deployment policy design](../designs/2026-09-10-mcp-ci-deployment-policy-design.md), [process v2](../process/architecture-artifacts-v2.md).

## Global Constraints

- Structured documents из main не меняются: process v1 и прежние plans остаются историческими свидетельствами.
- Push локального main требует явного запроса. До первичной активации MCP deploy требует отдельного запроса.
- После активации только проверенный SHA main и опубликованный digest поступают в обычный автоматический rollout.
- PR/fork/tag/устаревший run не получают право менять production.
- Не создавать worktree, не менять repository permissions/secrets и не запускать live deploy при реализации.
- Этот plan исполняется в Task 6 продуктового implementation plan; второго независимого исполнителя для тех же файлов не создавать.

### Task 1: Normative pointer and current instructions

**Files:** modify `scripts/v8std_architecture_model.py`, `AGENTS.md`,
`spec/README.md`, `.agents/skills/v8std-architecture/SKILL.md` and its relevant
references; update current policy assertions in `tests/test_v8std_architecture_repository.py`,
`tests/test_v8std_architecture_process.py`, and CLI fixtures when needed.

**Interface:** `load_process_schema(root)` loads v2; an explicitly constructed
test repository must supply its declared current schema rather than depend on
accidentally present checkout files. Graph reference semantics stay unchanged.

- [ ] Write/run RED: a temporary repository with process v2 validates via CLI;
  frozen v1 remains protected, and schema fields equal the prior schema. Use
  actual CLI behavior and graph validation, not only a string-presence assertion.
- [ ] Implement the current schema pointer and synchronize policy prose. Replace
  only the current manual-every-release rule with conditional automatic delivery
  after activation; preserve branch, approval, plan, freeze, merge, push and
  external-mutation boundaries.

```python
PROCESS_SCHEMA_PATH = Path("spec/process/architecture-artifacts-v2.md")
```

- [ ] Run `.venv/bin/python -m unittest tests.test_v8std_architecture_cli tests.test_v8std_architecture_model tests.test_v8std_architecture_process tests.test_v8std_architecture_repository tests.test_v8std_architecture_validation -v`; prove no frozen document from main changed with architecture `validate --base-ref main`.

### Task 2: Executable publication eligibility and fail-closed activation

**Files:** publication workflows, `scripts/publish_mcp_artifacts.py`,
`tests/test_mcp_publication.py`, activation/verification operations documents.
These files are owned by product Task 6, not edited by a concurrent worker.

**Interface:** release eligibility consumes event/ref/repository, successful
gate results and explicit activation state; outputs an allowed action set.
Missing or malformed fields deny production mutation. Host validates exact
envelope sequence/digests independently of workflow eligibility.

- [ ] Write/run RED table tests for push/main with activation, push/main before
  activation, PR, fork, tag, failed gates and stale sequence. Controlled publisher
  adapter records actual attempted object/manifest/host operations:

```python
self.assertEqual(result.production_actions, [])
self.assertEqual(host.accepted_releases, [])
self.assertTrue(previous_manifest_path.is_file())
```

- [ ] Implement/pin workflows, bounded typed publication helper and disabled-by-default
  activation. Preserve the existing published site before activation; a new
  Pages publication requires a verified prior manifest/archive or a newly
  committed and externally verified corpus publication. Missing history plus404
  is UNKNOWN, not initial absence (the approved boundary in
  `design:mcp-tools-only`, implemented by the2026-09-16 Task6 refinement).
  Do not publish a public manifest for a missing ai object or promote a public-default MCP
  release without a ready source. Describe required main protection/environment
  settings as explicit external prerequisites, not already configured facts.
- [ ] Run publication and architecture tests, then strict build before full suite.
  Record gate results and explicit absence of live activation in operations
  evidence; mark this plan complete only with its Task 6 review. External setup,
  push and rollout remain integration operations outside these checkboxes.
