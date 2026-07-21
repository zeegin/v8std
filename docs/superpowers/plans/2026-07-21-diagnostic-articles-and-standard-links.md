# Diagnostic Articles and Exact Standard Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate complete source-backed articles for all 186 BSL Language Server and 172 EDT v8-code-style diagnostics, and generate exact, evidence-backed diagnostic-to-standard-clause links from one reviewed registry.

**Architecture:** Two standard-library Python modules own the two independent transformations: upstream article synchronization and exact standard-link generation. Committed JSON manifests pin source revisions, content hashes, and reviewed relationships; committed Markdown is deterministic generated output, while ACC remains unmanaged and byte-stable.

**Tech Stack:** Python 3.12 standard library, `unittest`, JSON, Markdown, Git, existing v8std AI/MCP generators, Zensical 0.0.47.

## Global Constraints

- Source snapshots are pinned to BSL Language Server `f4616cda8a216789ee40529ed857e614b9e2ea25` and EDT v8-code-style `c8fe7932babf718c0ace3cf836a99d6a3b98d098`.
- Imported BSL Language Server bodies retain `LGPL-3.0-or-later`; imported EDT bodies retain `EPL-2.0`.
- Ordinary builds and CI perform no network access.
- Implementation and tests use only the Python standard library.
- ACC pages and ACC relationship lines are outside the generator's ownership and must remain byte-identical.
- No confirmed relationship may fall back to a standard page without an exact clause anchor.
- Tests precede production code and must be observed failing for the intended reason.

---

## File map

- `scripts/diagnostic_articles.py`: source manifest types, upstream discovery, body normalization, provenance hashing, and deterministic article rendering.
- `scripts/sync_diagnostic_articles.py`: `--check`/`--write` CLI for the article pipeline.
- `scripts/diagnostic_standard_links.py`: v8std URL parsing, registry types, clause/anchor validation, semantic coverage, and Markdown rendering.
- `scripts/generate_diagnostic_standard_links.py`: `--check`/`--write` CLI for both link directions.
- `data/diagnostic-sources.json`: pinned family metadata and exactly 358 source entries.
- `data/diagnostic-standard-links.json`: confirmed and rejected reviewed relationship records.
- `docs/THIRD_PARTY_DIAGNOSTIC_ARTICLES.md`: attribution and license boundary.
- `tests/test_diagnostic_articles.py`: unit tests for normalization, manifests, revisions, hashes, rendering, and ACC preservation.
- `tests/test_diagnostic_standard_links.py`: unit and repository tests for URL forms, clauses, registry coverage, exact anchors, deterministic backlinks, and audit regressions.
- `tests/fixtures/diagnostic-link-audit.json`: machine-readable expected resolution of every finding from the 2026-07-21 audit.
- `docs/diagnostics/bslls/*.md`: 186 generated article bodies and exact links.
- `docs/diagnostics/v8-code-style/*.md`: 172 generated article bodies and exact links.
- `docs/std/*.md`: generated BSL Language Server/EDT backlinks at exact clauses; ACC lines preserved.
- `scripts/generate_ai_artifacts.py`, `tests/test_generate_ai_artifacts.py`: preserve and expose anchor-qualified standard relations.

---

### Task 1: Article normalization and provenance core

**Files:**
- Create: `scripts/diagnostic_articles.py`
- Create: `tests/test_diagnostic_articles.py`

**Interfaces:**
- Produces: `SourceFamily`, `SourceEntry`, `SourceCatalog`, `normalize_article(source: str) -> tuple[str, str]`, `content_sha256(body: str) -> str`, `immutable_source_url(family: SourceFamily, path: str) -> str`, and `render_article(marker: str, title: str, metadata: list[str], body: str, entry: SourceEntry, family: SourceFamily, standards_markdown: str) -> str`.
- Consumes: no project-specific modules.

- [ ] **Step 1: Write failing normalization and provenance tests**

```python
from scripts.diagnostic_articles import (
    SourceFamily,
    content_sha256,
    immutable_source_url,
    normalize_article,
)


class DiagnosticArticleCoreTests(unittest.TestCase):
    def test_normalize_article_removes_only_first_h1(self):
        title, body = normalize_article(
            "# Заголовок диагностики\n\nОписание.\n\n## Примеры\n\n```bsl\nСообщить(\"x\");\n```\n"
        )
        self.assertEqual(title, "Заголовок диагностики")
        self.assertEqual(body, "Описание.\n\n## Примеры\n\n```bsl\nСообщить(\"x\");\n```\n")

    def test_normalize_article_rejects_missing_h1(self):
        with self.assertRaisesRegex(ValueError, "first non-empty line must be H1"):
            normalize_article("## Описание\n")

    def test_immutable_source_url_uses_full_revision(self):
        family = SourceFamily(
            family="bslls",
            repository="https://github.com/1c-syntax/bsl-language-server",
            revision="f4616cda8a216789ee40529ed857e614b9e2ea25",
            license="LGPL-3.0-or-later",
            source_root="docs/diagnostics",
        )
        self.assertEqual(
            immutable_source_url(family, "docs/diagnostics/UsingModalWindows.md"),
            "https://github.com/1c-syntax/bsl-language-server/blob/"
            "f4616cda8a216789ee40529ed857e614b9e2ea25/"
            "docs/diagnostics/UsingModalWindows.md",
        )

    def test_content_hash_is_stable_for_normalized_body(self):
        self.assertEqual(
            content_sha256("Описание.\n"),
            "0c0dec5dbd13824c66a2a7d2b3c39cc501a331c88430b10e9bb829ef4764839b",
        )
```

- [ ] **Step 2: Run tests and observe the missing-module failure**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_articles -v`

Expected: `ModuleNotFoundError: No module named 'scripts.diagnostic_articles'`.

- [ ] **Step 3: Implement immutable dataclasses and pure normalization functions**

```python
@dataclass(frozen=True)
class SourceFamily:
    family: str
    repository: str
    revision: str
    license: str
    source_root: str


@dataclass(frozen=True)
class SourceEntry:
    id: str
    source_path: str
    source_url: str
    content_sha256: str


def normalize_article(source: str) -> tuple[str, str]:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.splitlines()
    first = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first is None or not lines[first].startswith("# "):
        raise ValueError("first non-empty line must be H1")
    title = lines[first][2:].strip()
    body = "\n".join(lines[first + 1 :]).strip() + "\n"
    return title, body


def content_sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
```

Implement `immutable_source_url` by accepting only canonical GitHub HTTPS repository URLs and a full lowercase 40-character revision.

- [ ] **Step 4: Run the unit tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_articles -v`

Expected: all Task 1 tests pass, including the fixed SHA-256 assertion.

- [ ] **Step 5: Commit the core**

```bash
git add scripts/diagnostic_articles.py tests/test_diagnostic_articles.py
git -c commit.gpgsign=false commit -m "Add diagnostic article normalization core"
```

---

### Task 2: Source manifest validation and article CLI

**Files:**
- Modify: `scripts/diagnostic_articles.py`
- Create: `scripts/sync_diagnostic_articles.py`
- Modify: `tests/test_diagnostic_articles.py`
- Create: `docs/THIRD_PARTY_DIAGNOSTIC_ARTICLES.md`

**Interfaces:**
- Consumes: Task 1 dataclasses and pure functions.
- Produces: `load_catalog(path: Path) -> SourceCatalog`, `discover_family(checkout: Path, family: SourceFamily) -> dict[str, tuple[Path, str, str]]`, `verify_checkout_revision(checkout: Path, expected: str) -> None`, `render_article(marker: str, title: str, metadata: list[str], body: str, entry: SourceEntry, family: SourceFamily, standards_markdown: str) -> str`, and CLI exit codes `0` clean, `1` drift/validation failure, `2` invocation error.

- [ ] **Step 1: Add failing tests for revision, composition, managed blocks, and ACC preservation**

```python
def test_verify_checkout_revision_rejects_wrong_sha(self):
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory)
        subprocess.run(["git", "init", "-q", checkout], check=True)
        subprocess.run(["git", "-C", checkout, "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", checkout, "config", "user.name", "Test"], check=True)
        (checkout / "README.md").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "-C", checkout, "add", "README.md"], check=True)
        subprocess.run(
            ["git", "-C", checkout, "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"],
            check=True,
        )
        with self.assertRaisesRegex(ValueError, "checkout revision mismatch"):
            verify_checkout_revision(checkout, "0" * 40)

def test_render_article_preserves_local_metadata_and_marks_imported_body(self):
    rendered = render_article(
        marker="bslls:UsingModalWindows",
        title="Использование модальных окон (UsingModalWindows)",
        metadata=["- Тип: Дефект кода", "- Важность: Важный"],
        body="## Описание диагностики\n\nПолный текст.\n",
        entry=SOURCE_ENTRY,
        family=BSLLS_FAMILY,
        standards_markdown="- [#std703, п. 1](../../std/703.md#1) — Запрещает модальные вызовы.\n",
    )
    self.assertIn("<!-- diagnostic-source:start", rendered)
    self.assertIn("sha256=", rendered)
    self.assertIn("SPDX-License-Identifier: LGPL-3.0-or-later", rendered)
    self.assertIn("## Соответствие стандартам", rendered)

def test_write_mode_does_not_touch_acc_tree(self):
    before = hash_tree(REPO_ROOT / "docs/diagnostics/acc")
    run_sync_fixture(write=True)
    self.assertEqual(before, hash_tree(REPO_ROOT / "docs/diagnostics/acc"))
```

- [ ] **Step 2: Run tests and observe missing APIs**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_articles -v`

Expected: import failures for `verify_checkout_revision`, `render_article`, and `hash_tree`.

- [ ] **Step 3: Implement manifest/schema validation and managed rendering**

The JSON schema enforced by `load_catalog` is:

```json
{
  "version": 1,
  "families": [{
    "family": "bslls",
    "repository": "https://github.com/1c-syntax/bsl-language-server",
    "revision": "f4616cda8a216789ee40529ed857e614b9e2ea25",
    "license": "LGPL-3.0-or-later",
    "source_root": "docs/diagnostics",
    "diagnostics": [{
      "id": "UsingModalWindows",
      "source_path": "docs/diagnostics/UsingModalWindows.md",
      "source_url": "https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingModalWindows.md",
      "content_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }]
  }]
}
```

Reject unknown top-level/family/entry fields, duplicate family/diagnostic IDs, noncanonical URLs, non-full revisions, invalid SPDX values, and hash mismatches. Managed comments contain only single-line `key=value` provenance; render the upstream body byte-for-byte after newline normalization.

- [ ] **Step 4: Implement `sync_diagnostic_articles.py` CLI**

```text
usage: sync_diagnostic_articles.py (--check | --write)
       --bslls-checkout PATH --v8-code-style-checkout PATH
       [--repo-root PATH]
```

`--check` renders every page in memory and emits one path per drifted file.
`--write` updates `data/diagnostic-sources.json` and exactly the two managed
diagnostic trees. Both modes hash `docs/diagnostics/acc` before and after and
raise if it changes.

- [ ] **Step 5: Add the third-party notice**

The notice names both repositories, pinned revisions, SPDX licenses, managed
comment format, and states that v8std editorial metadata/relationship analysis
is separate from imported bodies.

- [ ] **Step 6: Run focused tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_articles -v`

Expected: all tests pass.

- [ ] **Step 7: Commit manifest/CLI infrastructure**

```bash
git add scripts/diagnostic_articles.py scripts/sync_diagnostic_articles.py tests/test_diagnostic_articles.py docs/THIRD_PARTY_DIAGNOSTIC_ARTICLES.md
git -c commit.gpgsign=false commit -m "Add reproducible diagnostic article sync"
```

---

### Task 3: Generate and verify all 358 source-backed articles

**Files:**
- Create: `data/diagnostic-sources.json`
- Modify: `docs/diagnostics/bslls/*.md`
- Modify: `docs/diagnostics/v8-code-style/*.md`
- Modify: `tests/test_diagnostic_articles.py`

**Interfaces:**
- Consumes: Task 2 `--write` and `--check` CLI.
- Produces: 186 BSL Language Server and 172 EDT pages whose managed bodies exactly match the pinned source checkout.

- [ ] **Step 1: Add failing repository coverage tests**

```python
def test_manifest_and_local_catalogs_have_exact_expected_composition(self):
    catalog = load_catalog(REPO_ROOT / "data/diagnostic-sources.json")
    self.assertEqual(len(catalog.family("bslls").diagnostics), 186)
    self.assertEqual(len(catalog.family("v8-code-style").diagnostics), 172)
    self.assertEqual(catalog.ids("bslls"), markdown_ids("bslls"))
    self.assertEqual(catalog.ids("v8-code-style"), markdown_ids("v8-code-style"))

def test_every_managed_body_is_nonempty_and_contains_upstream_structure(self):
    for page in all_managed_pages():
        body = managed_body(page.read_text(encoding="utf-8"))
        self.assertGreater(len(body.strip()), 20, page)
        self.assertRegex(body, r"(?m)^(?:## |[^#\n])")
```

- [ ] **Step 2: Run coverage tests and observe missing manifest/managed blocks**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_articles -v`

Expected: failure because `data/diagnostic-sources.json` and managed blocks do not exist.

- [ ] **Step 3: Generate the manifest and all articles from the pinned checkouts**

Run:

```bash
.venv/bin/python scripts/sync_diagnostic_articles.py --write \
  --bslls-checkout /tmp/v8std-bslls-audit.fPBfU2 \
  --v8-code-style-checkout /tmp/v8std-diagnostic-audit.Cil1k9
```

Expected summary: `bslls: 186 written; v8-code-style: 172 written; ACC unchanged`.

- [ ] **Step 4: Inspect source fidelity and article layout**

Compare these representative classes line-by-line with normalized upstream:

- `UsingModalWindows`: long BSL article with table, limitation, example, sources;
- `DeprecatedMethodCall`: BSL article with multiple explanatory paragraphs;
- `query-in-loop`: EDT article with bad/good BSL examples;
- `form-module-missing-pragma`: EDT article with multiple standard sources;
- one minimal article from each family.

Run:

```bash
.venv/bin/python scripts/sync_diagnostic_articles.py --check \
  --bslls-checkout /tmp/v8std-bslls-audit.fPBfU2 \
  --v8-code-style-checkout /tmp/v8std-diagnostic-audit.Cil1k9
```

Expected: `358 articles clean` and exit code 0.

- [ ] **Step 5: Run focused and existing catalog tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_diagnostic_articles tests.test_v8_code_style_diagnostics -v
```

Expected: all tests pass; source links now use immutable revisions, so update the old `blob/master` assertion to validate the manifest URL instead of weakening source provenance.

- [ ] **Step 6: Commit generated articles**

```bash
git add data/diagnostic-sources.json docs/diagnostics/bslls docs/diagnostics/v8-code-style tests/test_diagnostic_articles.py tests/test_v8_code_style_diagnostics.py
git -c commit.gpgsign=false commit -m "Import complete diagnostic articles"
```

---

### Task 4: Exact relationship registry and URL parser

**Files:**
- Create: `scripts/diagnostic_standard_links.py`
- Create: `tests/test_diagnostic_standard_links.py`
- Create: `data/diagnostic-standard-links.json`

**Interfaces:**
- Produces: `SourceProposal`, `LinkReview`, `parse_v8std_url(url: str) -> tuple[str, str | None]`, `heading_anchor(clause: str) -> str`, `load_reviews(path: Path) -> tuple[LinkReview, ...]`, `discover_source_proposals(catalog: SourceCatalog, checkouts: dict[str, Path]) -> set[SourceProposal]`, and `validate_review_coverage(proposals: set[SourceProposal], reviews: tuple[LinkReview, ...]) -> None`.
- Consumes: Task 2 source catalog and normalized article/source paths.

- [ ] **Step 1: Write failing URL, anchor, and registry tests**

```python
def test_parse_supported_v8std_urls(self):
    cases = [
        ("https://its.1c.ru/db/v8std#content:455:hdoc", ("std455", None)),
        ("https://its.1c.ru/db/v8std#content:455:hdoc:2.4.3", ("std455", "2.4.3")),
        ("https://its.1c.ru/db/v8std/content/455/hdoc", ("std455", None)),
        ("https://its.1c.ru/db/v8std/content/455/hdoc/", ("std455", None)),
        ("https://its.1c.ru/db/v8std/content/455/hdoc#2.4.3", ("std455", "2.4.3")),
        ("https://its.1c.ru/db/v8std#contrut:761:hdoc", ("std761", None)),
    ]
    for url, expected in cases:
        with self.subTest(url=url):
            self.assertEqual(parse_v8std_url(url), expected)

def test_unknown_v8std_url_is_an_error(self):
    with self.assertRaisesRegex(ValueError, "unsupported v8std URL"):
        parse_v8std_url("https://its.1c.ru/db/v8std?content=455")

def test_heading_anchor_matches_zensical_numeric_slug(self):
    self.assertEqual(heading_anchor("2.4.3"), "243")
    self.assertEqual(heading_anchor("6.4.1"), "641")

def test_confirmed_review_requires_clause_anchor_reason_and_evidence(self):
    with self.assertRaisesRegex(ValueError, "confirmed review requires clause"):
        LinkReview.from_dict({
            "diagnostic": "bslls:UsingModalWindows",
            "standard": "std703",
            "review": "confirmed",
            "evidence": [],
            "reason": "",
        })
```

- [ ] **Step 2: Run tests and observe missing-module failure**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links -v`

Expected: `ModuleNotFoundError: No module named 'scripts.diagnostic_standard_links'`.

- [ ] **Step 3: Implement strict URL parsing, dataclasses, JSON schema, and proposal coverage**

The registry is a JSON object with `version: 1` and `reviews: []`. Enforce exact
field sets. Confirmed records require `clause`, derived `anchor`, non-empty
`reason`, and at least one immutable `evidence` URL. Rejected records require a
non-empty reason and evidence but may have null clause/anchor. A
`(diagnostic, standard, evidence proposal)` must have exactly one review.

- [ ] **Step 4: Bootstrap the candidate registry without confirming anything automatically**

Create `data/diagnostic-standard-links.json` from all unique source proposals,
with `review: "rejected"`, reason `"Unreviewed bootstrap record"`, and the
source URL as evidence. This deliberately keeps the repository test red until
every record is semantically reviewed; no bootstrap record may remain at the
end of Tasks 5–6.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links -v`

Expected: parser/schema unit tests pass. Semantic coverage tests are introduced
red in Tasks 5 and 6, immediately before reviewing each family.

- [ ] **Step 6: Commit parser and deliberately incomplete candidate registry**

```bash
git add scripts/diagnostic_standard_links.py tests/test_diagnostic_standard_links.py data/diagnostic-standard-links.json
git -c commit.gpgsign=false commit -m "Add exact diagnostic relationship registry"
```

---

### Task 5: Review every BSL Language Server relationship

**Files:**
- Modify: `data/diagnostic-standard-links.json`
- Modify: `tests/fixtures/diagnostic-link-audit.json`
- Modify: `tests/test_diagnostic_standard_links.py`

**Interfaces:**
- Consumes: Task 4 source proposals and registry validation.
- Produces: one reviewed resolution for every BSL Language Server proposal plus any confirmed local-standard relationships supported by article semantics.

- [ ] **Step 1: Add failing BSL audit regression assertions**

```python
def test_bslls_known_missing_links_are_confirmed_at_exact_clauses(self):
    expected = {
        "bslls:UsingModalWindows": {"std703"},
        "bslls:UsingSynchronousCalls": {"std703"},
        "bslls:DeprecatedMethodCall": {"std453"},
        "bslls:DeprecatedCurrentDate": {"std643"},
        "bslls:QueryNestedFieldsByDot": {"std654"},
        "bslls:RefOveruse": {"std654"},
        "bslls:ReservedParameterNames": {"std640"},
    }
    assert_confirmed_standard_sets(self, expected)

def test_generic_std456_proposals_are_not_bulk_confirmed(self):
    generic = [r for r in reviews() if r.standard == "std456" and r.source_proposal]
    self.assertFalse(any(r.reason == "Unreviewed bootstrap record" for r in generic))
    self.assertTrue(all(r.review == "rejected" or (r.clause and r.anchor) for r in generic))
```

The complete 28-edge missing set from the audit is stored in
`tests/fixtures/diagnostic-link-audit.json`, not abbreviated to the example
above.

- [ ] **Step 2: Run tests and observe unreviewed/missing failures**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links -v`

Expected: failures enumerate BSL Language Server bootstrap records and the 28
missing subject-specific edges.

- [ ] **Step 3: Review BSL records in deterministic batches**

Process IDs sorted case-insensitively in batches of 20. For every proposal:

1. read the complete imported article;
2. read every numbered clause on the proposed local standard page;
3. record the exact clause and reason if normative conditions match;
4. reject broad source lists that do not explain the diagnostic;
5. add locally discovered standards only when the diagnostic scope is fully
   covered by the cited clause;
6. run the focused test after each batch.

The batch command is:

```bash
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check \
  --family bslls --show-unreviewed --limit 20
```

Expected after the last batch: `bslls proposals: all reviewed` and zero
`Unreviewed bootstrap record` strings for `bslls:` records.

- [ ] **Step 4: Resolve the 14 known misplaced BSL clause mappings**

Use the exact expected/current table in
`diagnostic-standard-links-review-2026-07-21.md`; assert corrected clauses for
the ten `std469`/`std474` mappings, `ExcessiveAutoTestCheck`, and `CachedPublic`.

- [ ] **Step 5: Run BSL relationship tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links -v`

Expected: all BSL-specific tests pass; EDT unreviewed failures remain.

- [ ] **Step 6: Commit BSL semantic review**

```bash
git add data/diagnostic-standard-links.json tests/fixtures/diagnostic-link-audit.json tests/test_diagnostic_standard_links.py
git -c commit.gpgsign=false commit -m "Review BSL diagnostic standard clauses"
```

---

### Task 6: Review every EDT v8-code-style relationship

**Files:**
- Modify: `data/diagnostic-standard-links.json`
- Modify: `tests/fixtures/diagnostic-link-audit.json`
- Modify: `tests/test_diagnostic_standard_links.py`

**Interfaces:**
- Consumes: Task 4 source proposals and Task 3 full EDT articles.
- Produces: one reviewed resolution for every EDT source proposal and all 12 locally proven missing relationships.

- [ ] **Step 1: Add failing EDT audit regression assertions**

The fixture records all ten source-missing links, twelve locally proven links,
all clause-placement findings, the stale `std499` transaction links, and the
two semantic corrections from the audit.

```python
def test_edt_semantic_corrections_are_explicit(self):
    self.assertRejected("v8cs:extension-md-object-prefix", "std469")
    self.assertConfirmed("v8cs:using-isinrole", "std737", "3")
    self.assertRejected("v8cs:using-isinrole", "std689")
    for diagnostic in TRANSACTION_DIAGNOSTICS:
        self.assertRejected(diagnostic, "std499")
        self.assertConfirmed(diagnostic, "std783", "1.3")
```

- [ ] **Step 2: Run tests and observe EDT audit failures**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links -v`

Expected: failures list EDT unreviewed records and missing/corrected mappings.

- [ ] **Step 3: Review EDT records in deterministic batches**

Use the same six-step semantic process as Task 5 and this command:

```bash
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check \
  --family v8-code-style --show-unreviewed --limit 20
```

For the known source URL typo `contrut`, retain the immutable source URL as
evidence and note that normalization intentionally recovered `std761`.

- [ ] **Step 4: Add and review the 12 locally proven missing mappings**

Create confirmed records for the exact list in the audit. Evidence must include
the local standard URL/anchor and the immutable upstream diagnostic article;
the reason must state the matching diagnostic condition, not merely repeat the
standard title.

- [ ] **Step 5: Resolve every manual clause-placement finding**

Convert the audit's EDT table into fixture entries with expected review,
standard, and clause. The test compares the whole fixture to the registry so a
listed finding cannot be silently omitted.

- [ ] **Step 6: Run all relationship tests**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links -v`

Expected: all tests pass and `--show-unreviewed` returns no records for either
managed family.

- [ ] **Step 7: Commit EDT semantic review**

```bash
git add data/diagnostic-standard-links.json tests/fixtures/diagnostic-link-audit.json tests/test_diagnostic_standard_links.py
git -c commit.gpgsign=false commit -m "Review EDT diagnostic standard clauses"
```

---

### Task 7: Generate exact links and standard backlinks

**Files:**
- Modify: `scripts/diagnostic_standard_links.py`
- Create: `scripts/generate_diagnostic_standard_links.py`
- Modify: `tests/test_diagnostic_standard_links.py`
- Modify: `docs/diagnostics/bslls/*.md`
- Modify: `docs/diagnostics/v8-code-style/*.md`
- Modify: `docs/std/*.md`

**Interfaces:**
- Consumes: fully reviewed registry from Tasks 5–6.
- Produces: `render_diagnostic_relations`, `render_standard_backlinks`, `rewrite_diagnostic_page`, `rewrite_standard_page`, and deterministic `--check`/`--write` CLI.

- [ ] **Step 1: Write failing round-trip and ACC-preservation tests**

```python
def test_forward_and_reverse_links_are_generated_from_same_record(self):
    review = confirmed_review(
        diagnostic="bslls:UsingModalWindows",
        standard="std703",
        clause="1",
    )
    forward = render_diagnostic_relations([review], standard_titles={"std703": "Ограничение модальных окон"})
    reverse = render_standard_backlinks([review])
    self.assertIn("../../std/703.md#1", forward)
    self.assertIn("../diagnostics/bslls/UsingModalWindows.md", reverse["std703"]["1"])

def test_rewrite_standard_page_preserves_acc_lines_byte_for_byte(self):
    source = FIXTURE_STANDARD_WITH_ACC_AND_OLD_MANAGED_LINKS
    before = re.findall(r"^.*#acc:.*$", source, re.MULTILINE)
    rewritten = rewrite_standard_page(source, generated_reviews())
    after = re.findall(r"^.*#acc:.*$", rewritten, re.MULTILINE)
    self.assertEqual(before, after)
```

- [ ] **Step 2: Run tests and observe missing rendering APIs**

Run: `.venv/bin/python -m unittest tests.test_diagnostic_standard_links -v`

Expected: import failures for rendering/rewrite functions.

- [ ] **Step 3: Implement managed-region rewriting**

Diagnostic relationship regions use:

```markdown
<!-- diagnostic-standards:start -->
## Соответствие стандартам
- [#std703, п. 1: Ограничение на использование модальных окон](../../std/703.md#1) — запрещает диагностируемые модальные вызовы.
<!-- diagnostic-standards:end -->
```

Standard backlink regions use clause-qualified comments:

```markdown
<!-- diagnostic-backlinks:start clause=2.4.3 -->
###### Проверки
~[#bslls:EventHandlerInvalidSignature](../diagnostics/bslls/EventHandlerInvalidSignature.md)~
<!-- diagnostic-backlinks:end clause=2.4.3 -->
```

Remove legacy BSL/EDT lines outside managed regions only after confirming their
diagnostic/standard pair is represented by a reviewed confirmed or rejected
registry record. Never remove an ACC line.

- [ ] **Step 4: Implement the generator CLI and write the migrated graph**

Run:

```bash
.venv/bin/python scripts/generate_diagnostic_standard_links.py --write
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check
```

Expected: the first command reports written diagnostic/standard counts; the
second reports `relationship graph clean` and exits 0.

- [ ] **Step 5: Verify exact anchor existence against rendered heading rules**

Run the full relationship test module. It must parse every `docs/std/*.md`
numeric heading, derive Zensical's anchor, and prove every confirmed registry
record points to one of those anchors.

- [ ] **Step 6: Commit generated exact links**

```bash
git add scripts/diagnostic_standard_links.py scripts/generate_diagnostic_standard_links.py tests/test_diagnostic_standard_links.py docs/diagnostics/bslls docs/diagnostics/v8-code-style docs/std
git -c commit.gpgsign=false commit -m "Generate exact diagnostic standard links"
```

---

### Task 8: AI/MCP integration, indexes, and full verification

**Files:**
- Modify: `scripts/generate_ai_artifacts.py`
- Modify: `tests/test_generate_ai_artifacts.py`
- Modify: `docs/diagnostics/index.md`
- Modify: `docs/diagnostics/bslls/index.md`
- Modify: `docs/diagnostics/v8-code-style/index.md`
- Modify generated AI/MCP artifacts as required by repository policy.

**Interfaces:**
- Consumes: generated exact Markdown links and complete article bodies.
- Produces: AI/MCP records whose related standards preserve `#anchor` URLs and whose page text includes imported article content.

- [ ] **Step 1: Add failing AI artifact assertions**

```python
def test_diagnostic_relation_preserves_exact_standard_anchor(self):
    page = self.pages_by_id["bslls:UsingModalWindows"]
    standard = next(item for item in page["related"] if item["id"] == "std703")
    self.assertTrue(standard["url"].endswith("/std/703/#1"))

def test_full_diagnostic_article_is_available_to_mcp(self):
    page = self.pages_by_id["bslls:UsingModalWindows"]
    self.assertIn("Ограничения диагностики", page["content"])
    self.assertIn("ПоказатьПредупреждение", page["content"])
```

- [ ] **Step 2: Run AI tests and observe anchor/content failures**

Run: `.venv/bin/python -m unittest tests.test_generate_ai_artifacts -v`

Expected: relation URL lacks the anchor or parser omits managed body content.

- [ ] **Step 3: Preserve anchors through Markdown relation parsing and public URLs**

Update the relation parser so `../../std/703.md#1` becomes
`https://v8std.ru/std/703/#1` while the canonical page ID remains `std703`.
Do not create separate page records per clause.

- [ ] **Step 4: Regenerate indexes and AI artifacts**

Run:

```bash
.venv/bin/python scripts/generate_ai_artifacts.py
```

Update diagnostic indexes from the local generated page titles without network
access. Expected family counts remain 186 and 172.

- [ ] **Step 5: Run the complete verification matrix**

Run:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/sync_diagnostic_articles.py --check \
  --bslls-checkout /tmp/v8std-bslls-audit.fPBfU2 \
  --v8-code-style-checkout /tmp/v8std-diagnostic-audit.Cil1k9
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check
.venv/bin/python scripts/search_benchmark.py
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
git diff --check
```

Expected: all tests pass; 358 articles clean; relationship graph clean; search
benchmark meets current repository thresholds; Zensical prints `No issues
found`; diff check exits 0.

- [ ] **Step 6: Prove deterministic regeneration**

Record `git status --short`, run both `--write` generators and AI generation,
then compare `git status --short` again. Expected: no new diff.

- [ ] **Step 7: Inspect representative rendered pages**

Open built pages for:

- BSL long article with exact standard link;
- BSL rejected generic `std456` proposal;
- EDT multi-example article;
- EDT diagnostic with multiple exact standards;
- standard page containing ACC plus generated managed-family backlinks.

Verify headings, code fences, tables, licenses, exact anchors, and backlink
placement in the rendered HTML.

- [ ] **Step 8: Commit integration and generated artifacts**

```bash
git add scripts/generate_ai_artifacts.py tests/test_generate_ai_artifacts.py docs/diagnostics docs/std docs/ai docs/llms.txt docs/llms-full.txt
git -c commit.gpgsign=false commit -m "Expose complete diagnostic articles and exact clauses"
```

If ignored generated artifacts are not tracked by repository policy, omit them
from `git add` after verifying generation; do not force-add ignored files.

---

## Plan self-review result

- Spec coverage: article provenance, licenses, exact relationships, URL
  normalization, semantic review, ACC preservation, AI/MCP propagation, and
  full verification each have an implementing task and an authoritative test.
- Scope: the article pipeline and relationship pipeline are separate modules
  but remain one plan because completion requires their combined generated
  pages.
- Type consistency: both CLIs consume the same `SourceCatalog`; relationship
  records consistently use `diagnostic`, `standard`, `clause`, `anchor`,
  `evidence`, `reason`, `review`, and optional `notes`.
- No placeholder implementation steps remain; the only mass-edit operations are
  deterministic generator invocations followed by explicit semantic batch
  review and fixture comparison.
