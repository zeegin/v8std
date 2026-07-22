# Diagnostics by Standard Clause Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat `/diagnostics/` table with a searchable, accessible registry grouped by standard and exact clause.

**Architecture:** Extend the existing Python relationship generator so it parses standard clauses and renders semantic HTML inside Markdown. Keep confirmed relationship data as the sole mapping source; add a small progressive-enhancement JavaScript module and scoped CSS for filtering and optional empty-clause display.

**Tech Stack:** Python 3.12, `unittest`, Markdown/HTML, vanilla JavaScript, CSS, Zensical 0.0.47.

## Global Constraints

- Show only standards and clauses with confirmed diagnostics by default.
- The control label is exactly `Показать пункты без проверок`.
- A confirmed relationship without a clause belongs to `Стандарт в целом`.
- A relationship with only one of `clause` and `anchor` is invalid.
- Without JavaScript, the compact useful registry remains visible.
- Do not modify existing relationship decisions or diagnostic backlinks.

---

### Task 1: Clause-aware registry model and renderer

**Files:**
- Modify: `scripts/generate_diagnostic_standard_links.py`
- Modify: `tests/test_diagnostic_standard_links.py`

**Interfaces:**
- Produces: `load_standard_pages(standards_dir: Path) -> dict[str, StandardPage]`
- Produces: `render_registry_index(reviews, standard_pages) -> str`
- `StandardPage` contains the standard title and ordered clause records with `clause`, `anchor`, and optional `summary`.

- [ ] **Step 1: Write failing parser and renderer tests**

Add fixture standards containing clauses `1`, `6.1`, and a code-first clause. Assert that parsing extracts the first prose sentence, preserves numeric ordering, falls back to no summary, renders `std → clause → diagnostics`, links to `../std/640.md#61`, creates `Стандарт в целом`, excludes rejected links, and raises `ValueError` for partial or missing clause targets.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links.GeneratedRelationshipGraphTests -v`

Expected: FAIL because clause parsing and the new renderer contract do not exist.

- [ ] **Step 3: Implement the minimal clause model**

Add frozen dataclasses for a clause and standard page, parse numeric `######` headings, skip managed backlink comments/admonitions/code as summary candidates, validate confirmed relationships, and group them by `(standard, clause, anchor)`. Sort clause numbers by integer components and deduplicate diagnostics per group using `_registry_diagnostic_sort_key`.

- [ ] **Step 4: Render progressive semantic markup**

Generate a root `.diagnostics-registry`, a search input, the exact empty-toggle label, `<details class="diagnostics-standard">` blocks, clause sections, unique counts, hidden empty entries marked with `data-empty="true"`, and searchable normalized text in `data-search`. Render standard-level relationships last.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links.GeneratedRelationshipGraphTests -v`

Expected: all generated relationship graph tests PASS.

- [ ] **Step 6: Commit**

Run: `git add scripts/generate_diagnostic_standard_links.py tests/test_diagnostic_standard_links.py && git -c commit.gpgsign=false commit -m "Group diagnostic registry by standard clauses"`

### Task 2: Registry interaction

**Files:**
- Create: `docs/assets/javascripts/diagnostics-registry.js`
- Create: `tests/test_diagnostics_registry_js.py`
- Modify: `zensical.toml`

**Interfaces:**
- Consumes: `[data-diagnostics-registry]`, `[data-diagnostics-search]`, `[data-show-empty]`, `[data-standard]`, `[data-clause]`, and `[data-empty]` emitted by Task 1.
- Produces: filtering behavior without changing the generated catalog.

- [ ] **Step 1: Write failing static behavior tests**

Assert the module registers on `document$` when available and `DOMContentLoaded` otherwise, normalizes Russian/Latin text, hides nonmatches, opens standards containing matches, restores original `open` state when the query clears, and never reveals `data-empty="true"` unless the toggle is checked.

- [ ] **Step 2: Run the test and verify failure**

Run: `.venv/bin/python -m unittest tests.test_diagnostics_registry_js -v`

Expected: FAIL because the JavaScript file and Zensical registration are absent.

- [ ] **Step 3: Implement interaction**

Create an idempotent initializer. Cache each standard's initial `open` state, filter clauses from normalized `data-search`, hide standards with no visible clause, open matches while a query is active, restore state on clear, and reapply filtering when the empty toggle changes.

- [ ] **Step 4: Register and test**

Add `assets/javascripts/diagnostics-registry.js` to `extra_javascript` and rerun `.venv/bin/python -m unittest tests.test_diagnostics_registry_js -v`.

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add docs/assets/javascripts/diagnostics-registry.js tests/test_diagnostics_registry_js.py zensical.toml && git -c commit.gpgsign=false commit -m "Add diagnostic registry filtering"`

### Task 3: Responsive registry presentation

**Files:**
- Modify: `docs/assets/stylesheets/extra.css`
- Modify: `tests/test_diagnostic_standard_links.py`

**Interfaces:**
- Consumes the class names emitted in Task 1.
- Produces a readable wide and narrow layout with visible keyboard focus.

- [ ] **Step 1: Add failing markup contract assertions**

Assert the generated registry includes separate elements for controls, standard summary, counts, clauses, and diagnostic links so styling does not depend on content position.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links.GeneratedRelationshipGraphTests -v`

Expected: FAIL for any missing styling hook.

- [ ] **Step 3: Add scoped CSS**

Style only `.diagnostics-registry`: compact controls, bordered standard cards, clear disclosure focus state, muted counters, clause separators, wrapped diagnostic chips, dark palette support, and a single-column mobile layout below `44.984375em`. Use `[hidden] { display: none !important; }` within the registry.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links.GeneratedRelationshipGraphTests tests.test_diagnostics_registry_js -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add docs/assets/stylesheets/extra.css tests/test_diagnostic_standard_links.py && git -c commit.gpgsign=false commit -m "Style clause-aware diagnostic registry"`

### Task 4: Regeneration and end-to-end verification

**Files:**
- Modify: `docs/diagnostics/index.md` (generated)

**Interfaces:**
- Consumes all earlier generator, JavaScript, and CSS changes.
- Produces the committed public registry and verification evidence.

- [ ] **Step 1: Regenerate the registry**

Run: `.venv/bin/python scripts/generate_diagnostic_standard_links.py --write`

Expected: reports `registry=True` on the first run and changes `docs/diagnostics/index.md`.

- [ ] **Step 2: Prove deterministic generation**

Run: `.venv/bin/python scripts/generate_diagnostic_standard_links.py --check`

Expected: `relationship graph clean` and exit code 0.

- [ ] **Step 3: Run relationship and full unit tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links tests.test_diagnostics_registry_js -v`

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 4: Build strict documentation**

Run: `VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict`

Expected: exit code 0 without warnings.

- [ ] **Step 5: Inspect representative output and formatting**

Verify `std640` contains separate groups for clauses `3`, `4`, `5`, `6.1`, `6.2`, and `7`, plus `Стандарт в целом`; confirm `git diff --check` is silent and unrelated untracked audit files remain untouched.

- [ ] **Step 6: Commit generated output**

Run: `git add docs/diagnostics/index.md && git -c commit.gpgsign=false commit -m "Publish diagnostics grouped by standard clauses"`
