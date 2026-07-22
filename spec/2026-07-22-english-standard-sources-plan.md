# English Standard Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add verified English 1Ci Knowledge Base links beside Russian ITS links on matching standard pages.

**Architecture:** A JSON registry is the source of truth for confirmed `stdNNN` to English URL mappings. A deterministic Python synchronizer validates the registry and standard pages, renders source sections, and supports check/write modes; existing artifact generation consumes the resulting URLs.

**Tech Stack:** Python 3.12 standard library, `unittest`, JSON, Markdown, existing v8std artifact generator and Zensical build.

## Global Constraints

- Preserve the Russian ITS URL as the primary source.
- Never use the English catalog root as a substitute for a missing article.
- Do not infer an English URL from `stdNNN`; only registry entries are rendered.
- Normal tests and builds must not require network access.
- English links are labelled as language versions, not equivalent current revisions.

---

### Task 1: Registry validation and rendering contract

**Files:**
- Create: `tests/test_standard_sources.py`
- Create: `scripts/standard_sources.py`

**Interfaces:**
- Produces: `load_registry(path: Path) -> dict[str, str]`
- Produces: `render_sources(standard: str, russian_url: str, english_url: str | None) -> str`
- Produces: `sync_standard_sources(docs_dir: Path, registry_path: Path, write: bool) -> list[Path]`

- [ ] Write tests that require schema/version validation, unique standard IDs and URLs, the exact 1Ci HTTPS path prefix, matching ITS IDs, two-link rendering, preservation of single-source pages, and idempotence.
- [ ] Run `python3.12 -m unittest tests.test_standard_sources -v` and confirm failure because `scripts.standard_sources` does not exist.
- [ ] Implement the smallest standard-library module satisfying those tests, with CLI `--check` by default and `--write` for updates.
- [ ] Run `python3.12 -m unittest tests.test_standard_sources -v` and confirm all tests pass.

### Task 2: Verified mapping registry

**Files:**
- Create: `data/standard-english-sources.json`
- Modify: `tests/test_standard_sources.py`

**Interfaces:**
- Registry shape: `{"version": 1, "sources": [{"standard": "std498", "english_url": "https://kb.1ci.com/1C_Enterprise_Platform/Guides/Developer_Guides/1C_Enterprise_Development_Standards/Code_conventions/Using_1C_Enterprise_language_structures/Event_log/?language=en"}]}` sorted numerically by standard.

- [ ] Add a failing repository-level test that loads the real registry and requires every entry to resolve to an existing `docs/std/NNN.md` with the matching ITS source.
- [ ] Run the focused test and confirm failure while the registry is absent.
- [ ] Build mappings from the current public XWiki tree; confirm candidates by translated title plus distinctive structure/content, omitting unresolved cases.
- [ ] Add the sorted registry and run the focused tests until they pass.

### Task 3: Synchronize Markdown and generated artifacts

**Files:**
- Modify: every `docs/std/NNN.md` named by the registry
- Modify generated files written by `scripts/generate_ai_artifacts.py`
- Modify: `scripts/generate_social_cards.py` only if its source-section parser rejects the plural heading
- Modify tests for social-card parsing only if Task 3 exposes that incompatibility

**Interfaces:**
- Consumes: `python3.12 scripts/standard_sources.py --write`
- Produces: source sections matching the approved design and generated AI/MCP metadata containing both URLs.

- [ ] Run `python3.12 scripts/standard_sources.py --check` and confirm it reports unsynchronized pages.
- [ ] Run `python3.12 scripts/standard_sources.py --write`, then repeat `--check` and confirm no drift.
- [ ] Run `python3.12 scripts/generate_ai_artifacts.py` using the project virtual environment when present.
- [ ] Run the generator again and confirm `git status --short` is unchanged after the second run.
- [ ] Run focused tests for standard sources, artifact generation, and social cards; correct only incompatibilities caused by plural source sections.

### Task 4: Full verification and documentation of coverage

**Files:**
- Modify: `README.md` only if contributor commands for checking sources belong in the existing workflow section.

**Interfaces:**
- Verification commands are the deliverable; no new runtime interface.

- [ ] Run `python3.12 -m unittest discover -s tests -v` and require zero failures.
- [ ] Run `VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict` and require exit code 0.
- [ ] Run `python3.12 scripts/standard_sources.py --check` and the artifact generator once more to prove idempotence.
- [ ] Run `git diff --check` and inspect representative matched, unmatched, and duplicate-title pages.
- [ ] Report exact registry coverage, omitted/ambiguous cases, verification evidence, and files changed without claiming 317-page English coverage.
