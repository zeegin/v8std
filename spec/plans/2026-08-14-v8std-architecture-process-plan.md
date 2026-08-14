---
schema_version: 1
kind: plan
id: v8std-architecture-process
design: design:v8std-architecture-process
implements:
  - design:v8std-architecture-process
  - process:architecture-artifacts@1
---

# V8std Architecture Process Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ввести проверяемый процесс требований, ADR, инвариантов, контрактов, design и plan, полностью мигрировать существующий `spec/` и закрепить branch-first workflow в repo skill и `AGENTS.md`.

**Architecture:** Один атомарный bootstrap добавляет нормативную process specification, Python-валидатор графа и Git-заморозки, мигрированные документы, repo skill и обязательные инструкции. Structured Markdown остаётся единственным источником истины; состояния вычисляются из Git, типизированных связей и завершённости plan, а не хранятся в поле `status`.

**Tech Stack:** Python 3.12, PyYAML, `unittest`, Markdown с YAML front matter, Git CLI, Codex repo skills, GitHub Actions, Zensical 0.0.47.

## Global Constraints

- Выполнять plan в ветке `architecture/v8std-process-design`; прямые коммиты и push в `main` запрещены.
- Работать в основном checkout. Worktree и pull request не создавать без отдельного указания пользователя.
- Bootstrap не реализует MCP v3, monitoring redesign или OpenMetrics; эти документы остаются design-only.
- Process requirements не превращать в продуктовые ADR или архитектурные инварианты.
- Не добавлять поле `status`; состояния вычислять из Git, связей и чекбоксов plan.
- После bootstrap-merge structured design, ADR, invariant, contract, plan и versioned process specification неизменяемы.
- Требования, ADR и инварианты используют смысловые `UPPER_SNAKE_CASE` коды без цифр.
- ADR-файл имеет вид `YYYY-MM-DD-<semantic-slug>.md`; дата создания не заменяется датой merge.
- Ссылки типизированы: `design:<id>`, `adr:<id>`, `invariant:<id>`, `contract:<id>@<version>.<revision>`, `plan:<id>`.
- `spec/` не включать в `docs/`, навигацию, `llms.txt`, `llms-full.txt` или `pages.jsonl`.
- Валидатор не исполняет команды из Markdown через shell; он только проверяет declarations.
- Старые unstructured документы разрешено переписать только в bootstrap; постоянного legacy-флага не создавать.
- При проектной ошибке остановить задачу и вернуться к `superpowers:brainstorming`, а не ослаблять проверки.
- Перед коммитом задачи отметить `[x]` только у реально выполненных шагов этой задачи и включить plan в коммит.
- Локальный merge выполняется только после полного gate; push и deploy в plan не входят.

## File Structure

| Path | Responsibility |
|---|---|
| `spec/process/architecture-artifacts-v1.md` | Единственная нормативная schema видов документов, ссылок, состояний и заморозки |
| `scripts/v8std_architecture_model.py` | Front matter, filenames, typed refs и in-memory graph |
| `scripts/v8std_architecture_validation.py` | Structure, lifecycle, traceability и freeze rules |
| `scripts/v8std_architecture.py` | CLI `validate`, `status`, `impact` |
| `tests/test_v8std_architecture_*.py` | Process, model, graph, Git/CLI и repository fixtures |
| `.agents/skills/v8std-architecture/` | Impact check, artifact selection, gates и recovery |
| `spec/designs/` | Design snapshots и requirement definitions |
| `spec/adr/` | Датированные atomic decisions |
| `spec/invariants/` | Product architecture properties и fitness checks |
| `spec/contracts/` | Versioned observable boundaries и conformance checks |
| `spec/plans/` | Executable plans; completion вычисляется по checkboxes |

## Requirement Coverage

| Process requirement | Implemented by |
|---|---|
| `ALL_CHANGES_USE_BRANCHES` | Task 7 AGENTS/skill and Task 9 integration |
| `MAIN_ACCEPTS_ONLY_VALIDATED_MERGES` | Tasks 4, 8 and 9 |
| `TRIVIALITY_IS_ASSESSED_NOT_ASSUMED` | Task 7 impact workflow and pressure tests |
| `ARCHITECTURE_IMPACT_IS_RECHECKED` | Tasks 4, 7 and 9 |
| `REQUIREMENTS_ARE_TRACEABLE` | Tasks 2, 3, 5 and 6 |
| `ARCHITECTURE_DECISIONS_ARE_ATOMIC` | Tasks 3 and 6 |
| `ADR_IDENTITIES_ARE_SEMANTIC` | Tasks 1, 2 and 6 |
| `ARCHITECTURE_INVARIANTS_ARE_SEMANTIC` | Tasks 1, 3 and 6 |
| `OBSERVABLE_BOUNDARIES_ARE_CONTRACTED` | Tasks 3, 5 and 6 |
| `ARCHITECTURE_DOCUMENTS_ARE_IMMUTABLE` | Task 4 and final merge-ready validation |
| `PROJECT_ERRORS_TRIGGER_COMPREHENSIVE_REVIEW` | Task 7 recovery workflow and Task 9 review handling |
| `DESIGN_APPROVAL_PRECEDES_IMPLEMENTATION` | Task 7 skill gates |
| `ARCHITECTURE_PROCESS_IS_MACHINE_VALIDATED` | Tasks 1–4 and 8 |
| `INTERNAL_SPECIFICATIONS_STAY_UNPUBLISHED` | Task 8 |
| `DEPLOYMENT_REQUIRES_EXPLICIT_REQUEST` | Task 7 AGENTS/skill and integration procedure |
| `EXISTING_SPECIFICATIONS_USE_ONE_MODEL` | Tasks 5 and 6 |
| `SUPERPOWERS_DRIVES_DESIGN_AND_PLANNING` | Task 7 skill workflow |
| `PRODUCT_ARCHITECTURE_EXCLUDES_DEVELOPMENT_PROCESS` | Tasks 1, 3, 6 and 7 |

---

### Task 1: Normative process specification

**Files:**
- Create: `spec/process/architecture-artifacts-v1.md`
- Create: `tests/test_v8std_architecture_process.py`
- Modify: `spec/README.md`
- Modify: `spec/designs/2026-08-14-v8std-architecture-process-design.md`
- Modify: `spec/plans/2026-08-14-v8std-architecture-process-plan.md`

**Interfaces:**
- Produces one machine-readable `schema` mapping read by validator and skill.
- Produces document-key grammar and immutable repository layout.

- [x] **Step 1: Write the failing process-contract test**

Create a local YAML front-matter loader and assert:

```python
PROCESS = ROOT / "spec/process/architecture-artifacts-v1.md"
payload = load_front_matter(PROCESS)
self.assertEqual(payload["kind"], "process")
self.assertEqual(payload["id"], "architecture-artifacts")
self.assertEqual(payload["schema_version"], 1)
self.assertEqual(payload["version"], 1)
self.assertNotIn("status", payload)
self.assertEqual(payload["schema"]["semantic_id_pattern"], r"^[A-Z][A-Z_]*$")
self.assertEqual(
    payload["schema"]["adr_filename_pattern"],
    r"^\d{4}-\d{2}-\d{2}-[a-z]+(?:-[a-z]+)*\.md$",
)
```

Also assert `spec/` is not a Zensical nav path.

- [x] **Step 2: Run the test and verify RED**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_process -v`

Expected: FAIL because the process specification is absent.

- [x] **Step 3: Create the single versioned schema source**

Create `spec/process/architecture-artifacts-v1.md` with this front matter:

```yaml
---
schema_version: 1
kind: process
id: architecture-artifacts
version: 1
schema:
  semantic_id_pattern: '^[A-Z][A-Z_]*$'
  document_id_pattern: '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'
  typed_reference_pattern: '^(design|adr|invariant|contract|plan|process):'
  contract_reference_pattern: '^contract:[A-Z][A-Z_]*@\d+\.\d+$'
  adr_filename_pattern: '^\d{4}-\d{2}-\d{2}-[a-z]+(?:-[a-z]+)*\.md$'
  directories:
    design: spec/designs
    adr: spec/adr
    invariant: spec/invariants
    contract: spec/contracts
    plan: spec/plans
    process: spec/process
  frozen_kinds: [design, adr, invariant, contract, plan, process]
  forbidden_fields: [status]
---
```

The body defines exact per-kind fields and filename rules:

| Kind | ID | Required typed fields | Filename |
|---|---|---|---|
| `design` | lower kebab | `scope`, `requirements`, `decisions`, `invariants`, `contracts`, `plans`, `supersedes`, `cancels` | `YYYY-MM-DD-<id>-design.md` |
| `adr` | semantic uppercase | `scope: product`, `design`, `requirements`, `aliases`, `supersedes`, `cancels`, `invariants`, `contracts` | `YYYY-MM-DD-<id-as-kebab>.md` |
| `invariant` | semantic uppercase | `scope: product`, `introduced_by`, `requirements`, `check` | `<id-as-kebab>.md` |
| `contract` | semantic uppercase | `scope`, `version`, `revision`, `compatibility`, `design`, `producer`, `consumers`, `requirements`, `governs`, `conformance`, `supersedes`, `deprecates` | `<id-as-kebab>-vN-rN.md` |
| `plan` | lower kebab | `design`, `implements` | `YYYY-MM-DD-<id>-plan.md` |
| `process` | lower kebab | `version`, `schema` | `<id>-vN.md` |

Define that requirement lifecycle uses only `introduces/uses/replaces/cancels`; ADR impact uses explicit `introduces/preserves/replaces/cancels`; contract compatibility is `backward-compatible` or `breaking`; plan completion requires at least one checkbox and all checked; an incomplete candidate plan is allowed during implementation but rejected by the `--merge-ready` gate; process requirements cannot feed product architecture; the ADR creation date exists only in the filename and never changes to the merge date; numeric aliases are allowed only for migrated `ADR-0001`–`ADR-0004` and never in current typed refs; a base document becomes frozen when its base revision has valid structured front matter, which enables one bootstrap rewrite without a permanent bypass; declared commands are never dynamically executed.

- [x] **Step 4: Structure the accepted design and this plan**

Add to the process design front matter:

```yaml
schema_version: 1
scope: process
decisions: []
invariants: []
contracts: []
plans: [plan:v8std-architecture-process]
```

Add above this plan title:

```yaml
---
schema_version: 1
kind: plan
id: v8std-architecture-process
design: design:v8std-architecture-process
implements:
  - design:v8std-architecture-process
  - process:architecture-artifacts@1
---
```

- [x] **Step 5: Replace `spec/README.md` with a short index**

List the six directories, typed-reference examples, internal-only boundary and pre-merge command `.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready`. Remove the old claims that design is mutable and that one ADR may replace only one predecessor.

- [x] **Step 6: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_process -v`

Expected: all process tests PASS.

Mark Task 1 complete and commit:

```bash
git add spec tests/test_v8std_architecture_process.py
git commit -m "docs: define architecture artifact schema"
```

### Task 2: Structured Markdown parser and graph model

**Files:**
- Create: `scripts/v8std_architecture_model.py`
- Create: `tests/test_v8std_architecture_model.py`

**Interfaces:**
- Produces `ArtifactRef.parse(value: str) -> ArtifactRef`.
- Produces `load_document(path, repo_root, schema) -> ArchitectureDocument`.
- Produces `discover_documents(repo_root, schema) -> list[ArchitectureDocument]`.
- Produces `build_graph(documents) -> ArchitectureGraph`.

- [x] **Step 1: Write failing model tests**

Cover valid ADR, invalid Gregorian date, filename/ID mismatch, forbidden `status`, typed contract ref, duplicate key, and complete/incomplete plan. Assert:

```python
self.assertEqual(document.key, "adr:PAGE_READING_VIA_RESOURCES")
self.assertEqual(document.created_on.isoformat(), "2026-08-14")
self.assertFalse(incomplete_plan.is_complete_plan)
self.assertTrue(complete_plan.is_complete_plan)
```

- [x] **Step 2: Run model tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_model -v`

Expected: FAIL because the model module is absent.

- [x] **Step 3: Implement immutable public types**

Implement:

```python
@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    identity: str
    version: int | None = None
    revision: int | None = None

@dataclass(frozen=True)
class ProcessSchema:
    version: int
    directories: dict[str, str]
    semantic_id_pattern: re.Pattern[str]
    document_id_pattern: re.Pattern[str]
    typed_reference_pattern: re.Pattern[str]
    contract_reference_pattern: re.Pattern[str]
    adr_filename_pattern: re.Pattern[str]
    frozen_kinds: frozenset[str]
    forbidden_fields: frozenset[str]

@dataclass(frozen=True)
class ArchitectureDocument:
    path: Path
    kind: str
    identity: str
    scope: str | None
    front_matter: dict[str, object]
    body: str
    references: tuple[ArtifactRef, ...]
    created_on: date | None
    checkbox_count: int
    checked_count: int

    @property
    def is_complete_plan(self) -> bool:
        return self.kind == "plan" and self.checkbox_count > 0 and self.checkbox_count == self.checked_count

@dataclass(frozen=True)
class ArchitectureGraph:
    documents: dict[str, ArchitectureDocument]
    aliases: dict[str, str]
    requirements: dict[str, str]
    incoming: dict[str, tuple[str, ...]]
```

`ArtifactRef` implements `parse()` and canonical `__str__()`; `ArchitectureDocument`
implements `key` so every later task uses one canonical typed identity.

- [x] **Step 4: Implement parsing and discovery**

Load schema only from `architecture-artifacts-v1.md`; parse YAML with `yaml.safe_load`; reject malformed front matter and forbidden fields. Parse typed refs, Gregorian dates and exact kebab projections. Scan only schema directories, ignore `README.md`, sort paths, and extract requirement definitions from `### UPPER_SNAKE_CASE` headings inside `## Требования`.

- [x] **Step 5: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_model -v`

Expected: all model tests PASS.

Mark Task 2 complete and commit:

```bash
git add scripts/v8std_architecture_model.py tests/test_v8std_architecture_model.py \
  spec/plans/2026-08-14-v8std-architecture-process-plan.md
git commit -m "feat: parse architecture artifacts"
```

### Task 3: Graph, lifecycle and traceability validation

**Files:**
- Create: `scripts/v8std_architecture_validation.py`
- Create: `tests/test_v8std_architecture_validation.py`

**Interfaces:**
- Produces `validate_graph(graph) -> list[ValidationIssue]`.
- Produces `validate_merge_readiness(graph) -> list[ValidationIssue]`.
- Produces `compute_states(graph, accepted_keys) -> dict[str, frozenset[str]]`.

- [ ] **Step 1: Write failing graph tests**

Cover dangling/wrong-type refs, duplicate IDs, replacement cycles, mixed cancel/supersede, one-to-many and many-to-one ADR replacements, and composite replacements split between designs. Require stable codes:

```python
DANGLING_REFERENCE
INVALID_REFERENCE_TYPE
DUPLICATE_IDENTITY
RELATION_CYCLE
MIXED_CANCEL_AND_SUPERSEDE
COMPOSITE_REPLACEMENT_SPLIT
```

- [ ] **Step 2: Write failing lifecycle tests**

Cover undefined/cancelled/dropped requirements, process requirement used by product ADR, invariant without basis/check, contract without producer/consumers/version/conformance, premature retirement, historical alias in prose versus current ref, accepted design without plan, and complete/incomplete plans. `validate_graph()` accepts a structurally correct incomplete candidate plan; `validate_merge_readiness()` returns `INCOMPLETE_PLAN`.

- [ ] **Step 3: Run validation tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_validation -v`

Expected: FAIL because validation module is absent.

- [ ] **Step 4: Implement stable issue collection and typed rules**

```python
@dataclass(frozen=True, order=True)
class ValidationIssue:
    code: str
    path: str
    message: str

def validate_graph(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues = []
    issues.extend(validate_references(graph))
    issues.extend(validate_requirements(graph))
    issues.extend(validate_adr_relations(graph))
    issues.extend(validate_invariants(graph))
    issues.extend(validate_contracts(graph))
    issues.extend(validate_plans(graph))
    return sorted(set(issues))
```

Validate lifecycle cycles separately from provenance. Require every predecessor requirement to be preserved, replaced or cancelled. Permit `required_when: implemented` declarations to reference future MCP test modules; never execute them.

`validate_merge_readiness()` additionally rejects incomplete plans. It resolves
declared Python test modules for `required_when: accepted` artifacts and for
`required_when: implemented` artifacts only after they become implemented. A
missing required module is `MISSING_FITNESS_EVIDENCE`; a future module declared
on an unimplemented artifact is valid.

- [ ] **Step 5: Implement computed states without `status`**

Compute `CANDIDATE`, `ACCEPTED`, `SUPERSEDED`, `CANCELLED`, `DEPRECATED`, `RETIRED`, and `IMPLEMENTED`. A complete accepted plan makes only its typed `implements` targets implemented. Do not store or infer `DEPLOYED` from repository files.

- [ ] **Step 6: Run GREEN and commit**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_validation -v`

Expected: all graph, lifecycle and state tests PASS.

Mark Task 3 complete and commit:

```bash
git add scripts/v8std_architecture_validation.py tests/test_v8std_architecture_validation.py \
  spec/plans/2026-08-14-v8std-architecture-process-plan.md
git commit -m "feat: validate architecture graph"
```

### Task 4: Git freeze, impact candidates and CLI

**Files:**
- Create: `scripts/v8std_architecture.py`
- Create: `tests/test_v8std_architecture_cli.py`
- Modify: `scripts/v8std_architecture_validation.py`

**Interfaces:**
- Produces `validate --root PATH [--base-ref REF] [--merge-ready]`.
- Produces `status --root PATH [--main-ref REF]`.
- Produces `impact --root PATH --base-ref REF`.
- Produces `validate_frozen_documents(repo_root, base_ref, graph)` and `find_impact_candidates(graph, changed_paths)`.

- [ ] **Step 1: Write failing temp-Git freeze tests**

Initialize a temp Git repository and set local identity. Commit one structured design and one old unstructured file. Assert that editing, deleting or moving the structured design produces `FROZEN_DOCUMENT_MODIFIED`, `FROZEN_DOCUMENT_DELETED` or `FROZEN_DOCUMENT_MOVED`; adding a successor passes; moving the old unstructured file during bootstrap passes; editing its structured replacement after a commit fails.

```python
subprocess.run(["git", "config", "user.name", "Architecture Test"], cwd=root, check=True)
subprocess.run(["git", "config", "user.email", "architecture@example.invalid"], cwd=root, check=True)
```

- [ ] **Step 2: Write failing CLI and impact tests**

Require exit `0` for a structurally valid graph containing an incomplete candidate plan. The same graph with `--merge-ready` returns `1` and `INCOMPLETE_PLAN`. Other invalid graphs return `1` plus `CODE path: message`. A changed `scripts/v8std_mcp_server.py` governed by a contract must be listed by `impact` but must not itself become a validation error.

- [ ] **Step 3: Run tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_cli -v`

Expected: FAIL because CLI and Git comparison are absent.

- [ ] **Step 4: Implement base-revision loading and freeze comparison**

Use `git ls-tree -r --name-only <base-ref> -- spec` and `git show <base-ref>:<path>`. Treat a base file as frozen only when that base revision already has valid `schema_version: 1` front matter. Compare canonical key, path and bytes. A missing Git executable or unresolved requested base ref is a validation error, never a silent skip.

- [ ] **Step 5: Implement non-blocking impact candidates**

Match changed paths to contract/invariant `governs` entries by exact path or directory prefix ending in `/`. Print matching typed refs and paths. Do not infer a contract version change merely from a path match; skill review and conformance tests decide semantic impact.

- [ ] **Step 6: Implement deterministic CLI**

Implement the exact callable signatures `build_parser() -> argparse.ArgumentParser`,
`command_validate(args: argparse.Namespace) -> int`,
`command_status(args: argparse.Namespace) -> int`,
`command_impact(args: argparse.Namespace) -> int`, and
`main(argv: Sequence[str] | None = None) -> int`.

`validate` combines structural, graph and optional freeze issues. Only `--merge-ready` adds readiness issues for incomplete plans and missing required accepted/implemented fitness evidence. `status` prints `<typed-ref>\t<comma-separated-states>`. `impact` obtains paths from `git diff --name-only <base-ref>...HEAD` and exits zero after reporting candidates.

- [ ] **Step 7: Run architecture tests and commit**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_v8std_architecture_process \
  tests.test_v8std_architecture_model \
  tests.test_v8std_architecture_validation \
  tests.test_v8std_architecture_cli -v
```

Expected: all architecture tests PASS.

Mark Task 4 complete and commit:

```bash
git add scripts/v8std_architecture.py scripts/v8std_architecture_validation.py \
  tests/test_v8std_architecture_cli.py \
  spec/plans/2026-08-14-v8std-architecture-process-plan.md
git commit -m "feat: enforce frozen architecture documents"
```

### Task 5: Migrate implemented July designs, plans and contracts

**Files:**
- Move: `spec/2026-07-22-diagnostics-by-standard-clause-design.md` → `spec/designs/2026-07-22-diagnostics-by-standard-clause-design.md`.
- Move: `spec/2026-07-22-english-standard-sources-design.md` → `spec/designs/2026-07-22-english-standard-sources-design.md`.
- Move: `spec/2026-07-22-unified-diagnostic-chips-design.md` → `spec/designs/2026-07-22-unified-diagnostic-chips-design.md`.
- Move: `spec/2026-07-22-diagnostics-by-standard-clause-plan.md` → `spec/plans/2026-07-22-diagnostics-by-standard-clause-plan.md`.
- Move: `spec/2026-07-22-english-standard-sources-plan.md` → `spec/plans/2026-07-22-english-standard-sources-plan.md`.
- Move: `spec/2026-07-22-unified-diagnostic-chips-plan.md` → `spec/plans/2026-07-22-unified-diagnostic-chips-plan.md`.
- Create: `spec/contracts/diagnostic-relation-graph-v1-r0.md`.
- Create: `spec/contracts/diagnostic-chip-markup-v1-r0.md`.
- Create: `spec/contracts/standard-source-registry-v1-r0.md`.
- Create: `tests/test_v8std_architecture_repository.py`.

**Interfaces:**
- Produces three `IMPLEMENTED` designs backed by complete plans and current tests.
- Produces three implemented observable contracts.

- [ ] **Step 1: Add failing real-repository state assertions**

```python
EXPECTED_IMPLEMENTED = {
    "design:diagnostics-by-standard-clause",
    "design:english-standard-sources",
    "design:unified-diagnostic-chips",
}
for ref in EXPECTED_IMPLEMENTED:
    self.assertIn("IMPLEMENTED", states[ref])
```

Build `states` with `accepted_keys=frozenset(graph.documents)` to model the
target state after the atomic bootstrap merge. Assert every root-level
`spec/*.md` file is `README.md`.

- [ ] **Step 2: Run repository test and verify RED**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_repository -v`

Expected: FAIL because legacy documents are unstructured and in the root.

- [ ] **Step 3: Move all six documents with `git mv`**

Use exact paths:

```bash
git mv spec/2026-07-22-diagnostics-by-standard-clause-design.md spec/designs/
git mv spec/2026-07-22-english-standard-sources-design.md spec/designs/
git mv spec/2026-07-22-unified-diagnostic-chips-design.md spec/designs/
git mv spec/2026-07-22-diagnostics-by-standard-clause-plan.md spec/plans/
git mv spec/2026-07-22-english-standard-sources-plan.md spec/plans/
git mv spec/2026-07-22-unified-diagnostic-chips-plan.md spec/plans/
```

- [ ] **Step 4: Add exact requirement definitions and front matter**

| Design | Requirement codes |
|---|---|
| diagnostics-by-standard-clause | `DIAGNOSTICS_GROUP_BY_STANDARD_CLAUSE`, `EMPTY_DIAGNOSTIC_CLAUSES_ARE_OPT_IN`, `DIAGNOSTIC_REGISTRY_WORKS_WITHOUT_JAVASCRIPT`, `CONFIRMED_DIAGNOSTIC_RELATIONS_ARE_LOSSLESS`, `DIAGNOSTIC_CLAUSE_TEXT_IS_DERIVED` |
| english-standard-sources | `ENGLISH_STANDARD_LINKS_REQUIRE_VERIFICATION`, `RUSSIAN_STANDARD_SOURCE_REMAINS_PRIMARY`, `STANDARD_SOURCE_REGISTRY_IS_DETERMINISTIC`, `STANDARD_SOURCE_VALIDATION_IS_OFFLINE` |
| unified-diagnostic-chips | `DIAGNOSTIC_IDENTIFIERS_USE_SHARED_CHIPS`, `DIAGNOSTIC_CHIPS_ARE_ACCESSIBLE`, `GENERATED_DIAGNOSTIC_CHIPS_ARE_IDEMPOTENT` |

Add one `### CODE` definition per obligation. Use `schema_version: 1`, `kind: design`, `scope: product`, `requirements.introduces`, empty lifecycle fields, no ADR/invariant refs, and contract refs from Step 6.

- [ ] **Step 5: Structure and complete historical plans only after evidence**

Add `schema_version`, `kind: plan`, matching `id`, typed `design`, and `implements`. Run:

```bash
.venv/bin/python -m unittest \
  tests.test_standard_sources \
  tests.test_diagnostic_standard_links \
  tests.test_diagnostics_registry_js -v
```

Expected: 65 tests PASS. Only then change every historical plan checkbox to `[x]`.

Before checking the boxes, also run the completion gates present in those plans:

```bash
.venv/bin/python scripts/standard_sources.py --check
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
```

Expected: both generators report clean state, the full suite has zero failures,
and strict build exits 0. Only this combined evidence authorizes marking the
historical plans complete.

- [ ] **Step 6: Create three extracted contracts**

| Ref | Producer | Consumers | Governs | Conformance |
|---|---|---|---|---|
| `contract:DIAGNOSTIC_RELATION_GRAPH@1.0` | reviewed relation registries and relationship generator | standard pages, diagnostic pages and registry | `data/diagnostic-standard-links.json`, `scripts/generate_diagnostic_standard_links.py`, `docs/diagnostics/` | `tests.test_diagnostic_standard_links` |
| `contract:DIAGNOSTIC_CHIP_MARKUP@1.0` | diagnostic renderers | CSS, JavaScript, accessibility and readers | `scripts/diagnostic_standard_links.py`, `docs/assets/`, `docs/diagnostics/` | `tests.test_diagnostics_registry_js` |
| `contract:STANDARD_SOURCE_REGISTRY@1.0` | `data/standard-english-sources.json` maintainers | `standard_sources.py`, tests and generators | `data/standard-english-sources.json`, `scripts/standard_sources.py`, `docs/std/` | `tests.test_standard_sources` |

Set `compatibility: backward-compatible`, `required_when: implemented`, exact requirement refs, `supersedes: []`, and `deprecates: []`.

- [ ] **Step 7: Validate and commit migrated implemented specs**

Run:

```bash
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main
.venv/bin/python -m unittest \
  tests.test_v8std_architecture_repository \
  tests.test_standard_sources \
  tests.test_diagnostic_standard_links \
  tests.test_diagnostics_registry_js -v
```

Expected: validator exits 0 and all selected tests PASS.

Mark Task 5 complete and commit:

```bash
git add spec tests/test_v8std_architecture_repository.py
git commit -m "docs: migrate implemented specifications"
```

### Task 6: Migrate MCP design-only architecture package

**Files:**
- Move: `spec/2026-08-14-mcp-v3-resource-contract-design.md` → `spec/designs/2026-08-14-mcp-v3-resource-contract-design.md`.
- Move: `spec/2026-08-14-mcp-monitoring-dashboard-design.md` → `spec/designs/2026-08-14-mcp-monitoring-dashboard-design.md`.
- Move: `spec/2026-08-14-mcp-openmetrics-generation-design.md` → `spec/designs/2026-08-14-mcp-openmetrics-generation-design.md`.
- Rewrite: `spec/adr/0001-separate-mcp-v3-endpoint.md` → `spec/adr/2026-08-14-mcp-version-endpoint-isolation.md`.
- Rewrite: `spec/adr/0002-public-mcp-monitoring.md` → `spec/adr/2026-08-14-public-mcp-monitoring.md`.
- Rewrite: `spec/adr/0003-local-openmetrics-exposition.md` → `spec/adr/2026-08-14-local-openmetrics-exposition.md`.
- Rewrite: `spec/adr/0004-v3-page-reading-via-resources.md` → `spec/adr/2026-08-14-page-reading-via-resources.md`.
- Create: `spec/invariants/mcp-version-isolation.md`.
- Create: `spec/invariants/mcp-legacy-endpoint-stability.md`.
- Create: `spec/invariants/mcp-resource-version-page-reading-via-resources.md`.
- Create: `spec/invariants/mcp-resource-links-are-listable.md`.
- Create: `spec/invariants/public-monitoring-excludes-sensitive-data.md`.
- Create: `spec/invariants/operator-data-stays-outside-web-root.md`.
- Create: `spec/invariants/metrics-endpoints-are-loopback-only.md`.
- Create: `spec/invariants/metrics-label-cardinality-is-bounded.md`.
- Create: `spec/contracts/mcp-api-v2-r0.md`.
- Create: `spec/contracts/mcp-api-v3-r0.md`.
- Create: `spec/contracts/mcp-usage-events-v1-r0.md`.
- Create: `spec/contracts/mcp-usage-events-v2-r0.md`.
- Create: `spec/contracts/mcp-monitoring-projection-v1-r0.md`.
- Create: `spec/contracts/mcp-monitoring-projection-v2-r0.md`.
- Create: `spec/contracts/mcp-openmetrics-v1-r0.md`.
- Modify: `tests/test_v8std_architecture_repository.py`.

**Interfaces:**
- Produces accepted, not implemented MCP v3, monitoring redesign and OpenMetrics designs.
- Preserves implemented MCP v2 and legacy monitoring contracts separately.

- [ ] **Step 1: Add failing planned-state assertions**

```python
PLANNED = {
    "design:mcp-v3-resource-contract",
    "design:mcp-monitoring-dashboard",
    "design:mcp-openmetrics-generation",
}
for ref in PLANNED:
    self.assertEqual(states[ref], frozenset({"ACCEPTED"}))
```

Build target states with `accepted_keys=frozenset(graph.documents)`. Also assert
numeric ADR paths are absent and aliases cannot be used by current front matter.

- [ ] **Step 2: Move designs and define requirements**

Use `git mv`. Add exact requirements:

| Design | Requirement codes |
|---|---|
| mcp-v3-resource-contract | `MCP_LEGACY_VERSION_REMAINS_COMPATIBLE`, `MCP_VERSIONS_FAIL_INDEPENDENTLY`, `MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES`, `MCP_RESOURCE_VERSION_HAS_ONE_PRIMARY_PAGE_READER`, `MCP_RESOURCE_CATALOG_IS_PAGINATED`, `MCP_RESOURCE_LIST_USES_STABLE_SNAPSHOTS`, `MCP_RESOURCE_NOTIFICATIONS_ARE_OMITTED`, `MCP_RESOURCE_LINKS_RESOLVE_TO_LISTED_RESOURCES`, `MCP_RESOURCES_EXCLUDE_SUPPORT_PAGES`, `MCP_TEMPLATES_EXCLUDE_LANGUAGE_AND_METHOD_SOURCES` |
| mcp-monitoring-dashboard | `MONITORING_SHOWS_AGENT_FAMILIES`, `MONITORING_SHOWS_API_VERSIONS`, `MONITORING_SHOWS_MCP_OPERATIONS`, `PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA`, `OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT`, `MONITORING_REMAINS_PUBLIC`, `LEGACY_USAGE_EVENTS_REMAIN_READABLE` |
| mcp-openmetrics-generation | `OPENMETRICS_IS_GENERATED_LOCALLY`, `PROMETHEUS_INTEGRATION_IS_DEFERRED`, `METRICS_EXCLUDE_HIGH_CARDINALITY_LABELS`, `METRICS_ENDPOINTS_USE_LOOPBACK`, `METRIC_NAMES_ARE_VERSIONED_CONTRACTS` |

The `MCP_TEMPLATES_EXCLUDE_LANGUAGE_AND_METHOD_SOURCES` definition explicitly names both `lang` and `metod8dev`.

- [ ] **Step 3: Rewrite four ADRs**

| Path | ID | Alias | Input requirements |
|---|---|---|---|
| `spec/adr/2026-08-14-mcp-version-endpoint-isolation.md` | `MCP_VERSION_ENDPOINT_ISOLATION` | `ADR-0001` | `MCP_LEGACY_VERSION_REMAINS_COMPATIBLE`, `MCP_VERSIONS_FAIL_INDEPENDENTLY` |
| `spec/adr/2026-08-14-public-mcp-monitoring.md` | `PUBLIC_MCP_MONITORING` | `ADR-0002` | `MONITORING_SHOWS_AGENT_FAMILIES`, `MONITORING_SHOWS_API_VERSIONS`, `MONITORING_SHOWS_MCP_OPERATIONS`, `PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA`, `OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT`, `MONITORING_REMAINS_PUBLIC` |
| `spec/adr/2026-08-14-local-openmetrics-exposition.md` | `LOCAL_OPENMETRICS_EXPOSITION` | `ADR-0003` | `OPENMETRICS_IS_GENERATED_LOCALLY`, `PROMETHEUS_INTEGRATION_IS_DEFERRED`, `METRICS_ENDPOINTS_USE_LOOPBACK` |
| `spec/adr/2026-08-14-page-reading-via-resources.md` | `PAGE_READING_VIA_RESOURCES` | `ADR-0004` | `MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES`, `MCP_RESOURCE_VERSION_HAS_ONE_PRIMARY_PAGE_READER` |

Each ADR has exactly one decision and the sections `Входные требования`, `Решение`, `Влияние на инварианты`, `Влияние на контракты`, `Отклонённые альтернативы`. Remove stored status and numeric current refs.

- [ ] **Step 4: Create eight product invariants**

| ID | Introduced by | Check module | Required when |
|---|---|---|---|
| `MCP_VERSION_ISOLATION` | `MCP_VERSION_ENDPOINT_ISOLATION` | `tests.test_v8std_mcp_versions` | implemented |
| `MCP_LEGACY_ENDPOINT_STABILITY` | `MCP_VERSION_ENDPOINT_ISOLATION` | `tests.test_v8std_mcp_server` | accepted |
| `MCP_RESOURCE_VERSION_PAGE_READING_VIA_RESOURCES` | `PAGE_READING_VIA_RESOURCES` | `tests.test_v8std_mcp_v3` | implemented |
| `MCP_RESOURCE_LINKS_ARE_LISTABLE` | `PAGE_READING_VIA_RESOURCES` | `tests.test_v8std_mcp_v3` | implemented |
| `PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA` | `PUBLIC_MCP_MONITORING` | `tests.test_v8std_mcp_monitoring` | implemented |
| `OPERATOR_DATA_STAYS_OUTSIDE_WEB_ROOT` | `PUBLIC_MCP_MONITORING` | `tests.test_v8std_mcp_monitoring` | implemented |
| `METRICS_ENDPOINTS_ARE_LOOPBACK_ONLY` | `LOCAL_OPENMETRICS_EXPOSITION` | `tests.test_v8std_mcp_metrics` | implemented |
| `METRICS_LABEL_CARDINALITY_IS_BOUNDED` | `LOCAL_OPENMETRICS_EXPOSITION` | `tests.test_v8std_mcp_metrics` | implemented |

Each invariant states the durable property, exact requirement refs, `owner: v8std maintainers`, command and why violation falsifies the ADR.

- [ ] **Step 5: Create seven versioned contracts**

| Ref | Intent | Producer | Consumers | Required when |
|---|---|---|---|---|
| `contract:MCP_API@2.0` | implemented | MCP v2 `/mcp` | existing clients | accepted |
| `contract:MCP_API@3.0` | design-only breaking | future MCP v3 `/v3/mcp` | resource-capable clients | implemented |
| `contract:MCP_USAGE_EVENTS@1.0` | implemented legacy | current logger/Nginx | current aggregator | accepted |
| `contract:MCP_USAGE_EVENTS@2.0` | design-only compatible reader | future emitters | redesigned aggregator | implemented |
| `contract:MCP_MONITORING_PROJECTION@1.0` | implemented legacy | current aggregator | public legacy JSON | accepted |
| `contract:MCP_MONITORING_PROJECTION@2.0` | design-only breaking | redesigned aggregator | public and SSH views | implemented |
| `contract:MCP_OPENMETRICS@1.0` | design-only | MCP metric registries | future Prometheus | implemented |

Use these exact compatibility, governed paths, conformance commands and source sections:

| Ref | Compatibility | Governs | Conformance | Normative source |
|---|---|---|---|---|
| `contract:MCP_API@2.0` | backward-compatible | `scripts/v8std_mcp_server.py`, `scripts/v8std_mcp_index.py` | `.venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_mcp_index -v` | current code and tests plus v3 design section `Контракты версий` |
| `contract:MCP_API@3.0` | breaking | `scripts/v8std_mcp_v3.py`, `scripts/v8std_mcp_resources.py` | `.venv/bin/python -m unittest tests.test_v8std_mcp_v3 -v` | v3 design sections `Контракты версий` through `Результаты инструментов v3` |
| `contract:MCP_USAGE_EVENTS@1.0` | backward-compatible | `scripts/v8std_mcp_server.py`, `scripts/v8std_mcp_monitoring.py` | `.venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_mcp_monitoring -v` | current logger/parser and monitoring section `Совместимость со старыми логами` |
| `contract:MCP_USAGE_EVENTS@2.0` | backward-compatible | `scripts/v8std_mcp_server.py`, `scripts/v8std_mcp_v3.py`, `scripts/v8std_mcp_monitoring.py` | `.venv/bin/python -m unittest tests.test_v8std_mcp_monitoring.MonitoringEventV2Tests -v` | monitoring section `Контракт событий` |
| `contract:MCP_MONITORING_PROJECTION@1.0` | backward-compatible | `scripts/v8std_mcp_monitoring.py` | `.venv/bin/python -m unittest tests.test_v8std_mcp_monitoring -v` | current report and monitoring `Контекст` |
| `contract:MCP_MONITORING_PROJECTION@2.0` | breaking | `scripts/v8std_mcp_monitoring.py` | `.venv/bin/python -m unittest tests.test_v8std_mcp_monitoring.MonitoringProjectionV2Tests -v` | monitoring sections `Публичная и локальная операторская проекции`, `URL и контроль доступа`, `Модель данных отчёта` |
| `contract:MCP_OPENMETRICS@1.0` | backward-compatible | `scripts/v8std_mcp_metrics.py`, `scripts/v8std_mcp_server.py`, `scripts/v8std_mcp_v3.py` | `.venv/bin/python -m unittest tests.test_v8std_mcp_metrics -v` | OpenMetrics sections `Формат exposition`, `Контракт метрик`, `Запрещённые labels`, `Безопасность` |

The contract bodies extract exact URI, cursor, pagination, template exclusion,
event, redaction and metric rules from those named sources. Existing contracts
use current tests; design-only contracts declare future modules and are not
executed until a complete plan marks them implemented.

- [ ] **Step 6: Declare complete ADR impact maps**

- Endpoint isolation introduces `MCP_VERSION_ISOLATION`, `MCP_LEGACY_ENDPOINT_STABILITY`, preserves API v2 and introduces API v3.
- Page reading introduces `MCP_RESOURCE_VERSION_PAGE_READING_VIA_RESOURCES`, `MCP_RESOURCE_LINKS_ARE_LISTABLE` and constrains API v3.
- Public monitoring introduces both security invariants, preserves v1 contracts and introduces v2 contracts.
- OpenMetrics introduces loopback/cardinality invariants and OpenMetrics v1.

All unused `preserves/replaces/cancels` collections are explicit empty values.

- [ ] **Step 7: Validate design-only state and commit**

Run:

```bash
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main
.venv/bin/python -m unittest \
  tests.test_v8std_architecture_repository \
  tests.test_v8std_mcp_server \
  tests.test_v8std_mcp_monitoring -v
```

Expected: validator exits 0; current tests PASS; future designs are `ACCEPTED` without `IMPLEMENTED`.

Mark Task 6 complete and commit:

```bash
git add spec tests/test_v8std_architecture_repository.py
git commit -m "docs: migrate MCP architecture package"
```

### Task 7: Repo skill and mandatory AGENTS rules

**Files:**
- Create: `.agents/skills/v8std-architecture/SKILL.md`.
- Create: `.agents/skills/v8std-architecture/references/impact-check.md`.
- Create: `.agents/skills/v8std-architecture/references/document-triggers.md`.
- Create: `.agents/skills/v8std-architecture/references/failure-recovery.md`.
- Create: `.agents/skills/v8std-architecture/references/pressure-scenarios.md`.
- Modify: `AGENTS.md`.
- Modify: `tests/test_v8std_architecture_repository.py`.

**Interfaces:**
- Consumes `spec/process/architecture-artifacts-v1.md` as the only schema source.
- Produces impact classification and document-selection workflow for every mutation.
- Produces mandatory branch, review, validation, merge and deploy rules visible before skill invocation.

- [ ] **Step 1: Invoke `superpowers:writing-skills` and establish RED pressure baseline**

Run these scenarios without the new skill and create
`.agents/skills/v8std-architecture/references/pressure-scenarios.md` with one
table row per scenario: input, RED failure, expected behavior, GREEN result.

1. User labels an MCP contract change trivial.
2. User asks for a direct commit to `main`.
3. Implementation disproves approved design.
4. Replacing ADR silently drops an invariant.
5. Agent edits an accepted contract version.
6. Design-only work is called implemented.
7. Merge is proposed with an incomplete plan.
8. ADR file is renamed to the merge date.
9. Git workflow rule is proposed as a product invariant.

- [ ] **Step 2: Write failing static policy tests**

```python
agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
self.assertIn("Прямые коммиты и push в `main` запрещены", agents)
self.assertIn(".agents/skills/v8std-architecture/SKILL.md", agents)
self.assertIn("локальный merge", agents)
self.assertIn("Deploy выполняется только по явному запросу", agents)

skill = (ROOT / ".agents/skills/v8std-architecture/SKILL.md").read_text(encoding="utf-8")
self.assertIn("spec/process/architecture-artifacts-v1.md", skill)
self.assertNotIn("semantic_id_pattern", skill)
```

- [ ] **Step 3: Run tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_v8std_architecture_repository -v`

Expected: FAIL because the skill is absent and current `AGENTS.md` permits direct main commits.

- [ ] **Step 4: Replace `AGENTS.md` with the short mandatory set**

Retain root-cause, contradiction, logic-error and token-reporting rules. Replace Git permissions with:

```markdown
- Любое изменение файлов выполняй в отдельной ветке, созданной до первой записи.
- Прямые коммиты и push в `main` запрещены. После всех gate выполняй локальный merge без повторного выбора способа интеграции.
- Работай в основном checkout. Worktree и pull request используй только по явному указанию пользователя.
- Перед изменением используй `superpowers:brainstorming` и `.agents/skills/v8std-architecture/SKILL.md`; тривиальность является результатом impact check.
- Нетривиальную реализацию не начинай до письменного согласования design-пакета и создания plan через `superpowers:writing-plans`.
- Внутренние design, ADR, invariants, contracts, plans и process specifications храни только в `spec/`.
- Не изменяй и не удаляй structured documents из `main`; создавай преемника, версию или ревизию.
- Перед merge повтори impact check, запусти `validate --merge-ready`, fitness checks, полный test suite и strict build.
- Если реализация опровергла design, остановись и верни работу в brainstorming с комплексным пересмотром графа.
- Deploy выполняется только по явному запросу и только для проверенного SHA из `main`.
```

- [ ] **Step 5: Create the concise repo skill and focused references**

The `SKILL.md` trigger covers any requested v8std mutation, architecture/document/contract/ADR/invariant question, and discovery that may change impact classification. Its operation order is:

```text
1. Read branch, main, AGENTS.md and the versioned process specification.
2. Before mutation, create a feature branch if current branch is main.
3. Inspect actual context and run impact candidates.
4. Classify trivial only after proving no ADR/invariant/contract impact.
5. For nontrivial work, return to brainstorming and select artifacts.
6. After written design approval, use writing-plans when implementation is requested.
7. Stop implementation and re-enter brainstorming on project error.
8. Before merge rerun impact, `validate --merge-ready`, declared checks, unit tests and strict build.
9. Locally merge; never push or deploy without explicit authorization.
```

`impact-check.md` contains observable-boundary questions; `document-triggers.md` maps causes to artifacts; `failure-recovery.md` distinguishes implementation defect from project error; `pressure-scenarios.md` stores the nine inputs and expected behaviors. None copies schema fields.

- [ ] **Step 6: Run GREEN pressure tests**

Follow `superpowers:writing-skills` RED–GREEN–REFACTOR. Require branch/gate/document behavior in all nine scenarios. The direct-main and merge-date cases remain forbidden even on the trivial path.

- [ ] **Step 7: Run static tests, validator and commit**

Run:

```bash
.venv/bin/python -m unittest tests.test_v8std_architecture_repository -v
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main
```

Expected: tests PASS and validator exits 0.

Mark Task 7 complete and commit:

```bash
git add AGENTS.md .agents/skills/v8std-architecture \
  tests/test_v8std_architecture_repository.py \
  spec/plans/2026-08-14-v8std-architecture-process-plan.md
git commit -m "docs: enforce v8std architecture workflow"
```

### Task 8: CI, publication boundary and complete-corpus gate

**Files:**
- Modify: `.github/workflows/ci.yml`.
- Modify: `tests/test_v8std_architecture_repository.py`.
- Modify: `spec/plans/2026-08-14-v8std-architecture-process-plan.md`.

**Interfaces:**
- Produces post-main CI validation and local pre-merge commands.
- Produces executable proof that internal specifications stay unpublished.

- [ ] **Step 1: Add failing publication-boundary tests**

Build the existing AI index and assert no source path, title, URL or body originates in `spec/`. Recursively parse `zensical.toml` nav and reject targets beginning `spec/`. The rendered `site/` scan remains in Step 6 after the strict build creates fresh output.

- [ ] **Step 2: Add architecture validation to GitHub Actions**

Set checkout `fetch-depth: 2`, then add before Docker build:

```yaml
- name: Validate architecture graph
  run: |
    python3 -m pip install --disable-pip-version-check PyYAML
    python3 scripts/v8std_architecture.py validate --root . --base-ref HEAD^ --merge-ready
```

Keep existing Docker tests and strict build unchanged. Do not execute check commands from Markdown.

- [ ] **Step 3: Run focused architecture tests**

```bash
.venv/bin/python -m unittest \
  tests.test_v8std_architecture_process \
  tests.test_v8std_architecture_model \
  tests.test_v8std_architecture_validation \
  tests.test_v8std_architecture_cli \
  tests.test_v8std_architecture_repository -v
```

Expected: all architecture/process/publication tests PASS.

- [ ] **Step 4: Run validator and impact evidence**

```bash
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main
```

Expected: impact reports affected process/contract candidates and validate exits 0.

- [ ] **Step 5: Run full tests and strict build**

```bash
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
```

Expected: zero test failures/errors and strict build exit 0.

- [ ] **Step 6: Scan public outputs and generator drift**

```bash
if rg -n 'spec/(designs|adr|invariants|contracts|plans|process)' \
  site docs/llms.txt docs/llms-full.txt docs/ai/pages.jsonl; then
  exit 1
fi
.venv/bin/python scripts/generate_ai_artifacts.py
git diff --check
git status --short
```

Expected: no `spec/` publication, no whitespace errors and no unrelated file absorption.

- [ ] **Step 7: Commit CI and publication gate**

Mark Task 8 complete and commit:

```bash
git add .github/workflows/ci.yml tests/test_v8std_architecture_repository.py \
  spec/plans/2026-08-14-v8std-architecture-process-plan.md
git commit -m "ci: validate architecture process"
```

### Task 9: Final review and plan completion

**Files:**
- Modify: `spec/plans/2026-08-14-v8std-architecture-process-plan.md`.
- Review: every path in `git diff --name-only main...HEAD`.

**Interfaces:**
- Produces a complete immutable plan commit ready for local integration.
- Produces no push, PR or deployment.

- [ ] **Step 1: Request independent review**

Use `superpowers:requesting-code-review`. Check all 18 process requirements and specifically verify:

- process rules did not become product ADR/invariants;
- each ADR contains one decision and complete impact disposition;
- MCP future work is not marked implemented;
- historical plans are complete only where executable evidence exists;
- validator has no permanent bootstrap bypass;
- current refs never use numeric aliases;
- Markdown commands are never dynamically executed;
- `AGENTS.md`, skill and process schema do not contradict one another.

- [ ] **Step 2: Resolve blocking findings correctly**

For implementation defects, add a failing regression test, prove RED, fix, and prove GREEN. For design contradictions, stop and return to brainstorming instead of changing architecture implicitly.

- [ ] **Step 3: Run the pre-completion final gate**

```bash
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
git diff --check
```

Expected: validator exits 0, tests pass, strict build exits 0 and diff check is silent.

- [ ] **Step 4: Mark plan complete and commit**

After Steps 1–3 succeed, mark their checkboxes and this Step 4 checkbox `[x]`.
Confirm no unchecked plan steps remain and commit:

```bash
if rg -n '^- \[ \]' spec/plans/2026-08-14-v8std-architecture-process-plan.md; then
  exit 1
fi
git add spec/plans/2026-08-14-v8std-architecture-process-plan.md
git commit -m "docs: complete architecture process bootstrap"
```

## Integration Procedure After Plan Completion

This procedure is outside plan completion: it verifies the exact complete plan
commit and performs the already approved local integration without creating a
future checkbox that would have to be marked prematurely.

```bash
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready
.venv/bin/python -m unittest discover -s tests -v
git status --short --branch
git switch main
git merge --no-ff architecture/v8std-process-design -m "merge: establish v8std architecture process"
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref HEAD^ --merge-ready
git branch -d architecture/v8std-process-design
git status --short --branch
```

Required result: validator and tests pass on the exact feature commit, the tree
is clean before merge, local `main` contains the merge, post-merge validation
passes, the feature branch is deleted, and no push/deploy command has run.
