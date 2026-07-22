# Unified Diagnostic Chips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render every visible diagnostic identifier as the same clickable chip and remove the visible «Проверки» heading from standards.

**Architecture:** Keep relationship data and URL generation in `diagnostic_standard_links.py`, but make its standard backlink renderer emit semantic HTML using shared `.diagnostic-links` and `.diagnostic-chip` classes. Reuse the same link class in the generated registry and the two authored help pages; keep search-only attributes unchanged.

**Tech Stack:** Python 3.12, `unittest`, generated Markdown with embedded HTML, Zensical, CSS.

## Global Constraints

- Every visible `acc:…`, `bslls:…`, and `v8cs:…` diagnostic identifier is a link with class `.diagnostic-chip`.
- Standard backlink groups have `aria-label="Проверки"` but no visible «Проверки» heading.
- Existing `diagnostic-backlinks:start` and `diagnostic-backlinks:end` markers remain unchanged.
- Search attributes and other invisible technical values are not converted into components.
- Light theme, dark theme, keyboard focus, and narrow screens remain readable.

---

### Task 1: Render standard backlinks as chip groups

**Files:**
- Modify: `tests/test_diagnostic_standard_links.py`
- Modify: `scripts/diagnostic_standard_links.py`
- Regenerate: `docs/std/*.md`

**Interfaces:**
- Consumes: `_diagnostic_path(diagnostic: str) -> str` and confirmed `LinkReview` records.
- Produces: `render_standard_backlinks(reviews) -> dict[str, dict[str, str]]` whose values contain one `.diagnostic-links` container and `.diagnostic-chip` anchors.

- [ ] **Step 1: Write failing renderer tests**

Add assertions to `RelationshipRenderingTests` for the exact public contract:

```python
self.assertIn('<div class="diagnostic-links" aria-label="Проверки">', reverse["std703"]["1"])
self.assertIn(
    '<a class="diagnostic-chip" href="../diagnostics/bslls/UsingModalWindows.md">bslls:UsingModalWindows</a>',
    reverse["std703"]["1"],
)
self.assertNotIn("###### Проверки", reverse["std703"]["1"])
self.assertNotIn("~[#", reverse["std703"]["1"])
```

Update rewrite fixtures so their expected managed region uses the new container while retaining both marker comments.

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```bash
python3.12 -m unittest tests.test_diagnostic_standard_links.RelationshipRenderingTests -v
```

Expected: failures because `render_standard_backlinks` still emits `###### Проверки` and strikethrough Markdown links.

- [ ] **Step 3: Implement the semantic chip renderer**

Change the rendered lines to this structure; both the diagnostic identifier and its path come from validated catalog records:

```python
lines = [
    f"<!-- diagnostic-backlinks:start clause={clause} -->",
    '<div class="diagnostic-links" aria-label="Проверки">',
]
for review in sorted(items, key=lambda item: item.diagnostic):
    lines.append(
        f'<a class="diagnostic-chip" href="{_diagnostic_path(review.diagnostic)}">'
        f"{review.diagnostic}</a>"
    )
lines.extend([
    "</div>",
    f"<!-- diagnostic-backlinks:end clause={clause} -->",
])
```

Keep `_remove_empty_legacy_check_sections` so old empty headings can still be cleaned during migration; update its tests only where new generated output is expected.

- [ ] **Step 4: Run focused tests and regenerate standards**

Run:

```bash
python3.12 -m unittest tests.test_diagnostic_standard_links.RelationshipRenderingTests -v
python3.12 scripts/generate_diagnostic_standard_links.py --write
python3.12 scripts/generate_diagnostic_standard_links.py --check
```

Expected: tests pass; write updates managed regions; check exits successfully without another diff.

- [ ] **Step 5: Commit**

```bash
git add scripts/diagnostic_standard_links.py tests/test_diagnostic_standard_links.py docs/std
git commit -m "feat: render standard diagnostics as chips"
```

### Task 2: Share the chip component across the registry and help pages

**Files:**
- Modify: `scripts/generate_diagnostic_standard_links.py`
- Modify: `tests/test_diagnostics_registry_js.py`
- Modify: `docs/assets/stylesheets/extra.css`
- Modify: `docs/search-help.md`
- Modify: `docs/mcp.md`
- Regenerate: `docs/diagnostics/index.md`

**Interfaces:**
- Consumes: `.diagnostic-chip` anchor contract from Task 1.
- Produces: a shared `.diagnostic-links` layout and `.diagnostic-chip` visual component used by every visible diagnostic link.

- [ ] **Step 1: Write failing static contract tests**

Add tests that load the generated registry, stylesheet, and help pages and assert:

```python
self.assertIn('class="diagnostic-chip"', registry)
self.assertNotIn('class="diagnostics-clause__diagnostic"', registry)
self.assertIn(".md-typeset .diagnostic-chip", stylesheet)
self.assertIn('class="diagnostic-chip" href="diagnostics/acc/1245.md"', search_help)
self.assertIn('class="diagnostic-chip" href="diagnostics/bslls/UsingModalWindows.md"', mcp_help)
```

Also assert all visible diagnostic identifiers in `docs/search-help.md` and `docs/mcp.md` are inside `.diagnostic-chip` anchors, excluding fenced code and technical URLs.

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```bash
python3.12 -m unittest tests.test_diagnostics_registry_js -v
```

Expected: failures for the old registry class and unlinked inline-code examples.

- [ ] **Step 3: Implement the shared component**

Make the registry generator emit:

```html
<div class="diagnostics-clause__links diagnostic-links">
  <a class="diagnostic-chip" href="acc/1248.md">acc:1248</a>
</div>
```

Replace the local selector with shared styles and add interaction states:

```css
.diagnostic-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}

.md-typeset .diagnostic-chip {
    background: var(--md-code-bg-color);
    border-radius: 0.3rem;
    display: inline-block;
    font-family: var(--md-code-font-family);
    font-size: 0.72rem;
    padding: 0.25rem 0.45rem;
}

.md-typeset .diagnostic-chip:hover,
.md-typeset .diagnostic-chip:focus-visible {
    background: var(--md-accent-fg-color--transparent);
    color: var(--md-accent-fg-color);
}
```

Replace diagnostic inline-code examples in the two help pages with explicit relative HTML anchors, for example:

```html
<a class="diagnostic-chip" href="diagnostics/acc/1245.md">acc:1245</a>
```

Preserve noncanonical search examples such as `ACC 1245` as ordinary inline code because they are search phrases, not diagnostic identifiers.

- [ ] **Step 4: Regenerate the registry and run focused tests**

Run:

```bash
python3.12 scripts/generate_diagnostic_standard_links.py --write
python3.12 scripts/generate_diagnostic_standard_links.py --check
python3.12 -m unittest tests.test_diagnostics_registry_js -v
```

Expected: generator check is clean and all focused tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_diagnostic_standard_links.py tests/test_diagnostics_registry_js.py docs/assets/stylesheets/extra.css docs/search-help.md docs/mcp.md docs/diagnostics/index.md
git commit -m "feat: unify diagnostic chip links"
```

### Task 3: Validate generated content and rendered behavior

**Files:**
- Verify only: all files changed in Tasks 1–2.

**Interfaces:**
- Consumes: generated standard and registry markup plus shared CSS.
- Produces: evidence that generation is idempotent, documentation builds strictly, and chips work at desktop and mobile widths.

- [ ] **Step 1: Scan visible source for uncovered identifiers**

Run a Python check that scans Markdown outside generated search attributes and fails when a visible canonical diagnostic identifier is not within a `.diagnostic-chip` anchor. Expected: zero uncovered identifiers; diagnostic page identity headings are explicitly excluded because they are page titles, not mentions.

- [ ] **Step 2: Run the full automated suite**

Run:

```bash
python3.12 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Run strict generation and site build checks**

Run:

```bash
python3.12 scripts/generate_diagnostic_standard_links.py --check
VIRTUAL_ENV="/Users/ingvarvilkman/Documents/git/v8std/.venv" ./scripts/zensical_docs.sh build --strict
```

Expected: both generator checks succeed and Zensical reports no strict-build errors.

- [ ] **Step 4: Inspect the live site**

Open `/diagnostics/`, `/std/441/`, `/search-help/`, and `/mcp/` at desktop and narrow mobile widths. Verify chip wrapping, hover/focus, link targets, dark/light readability, absence of the visible «Проверки» heading, and placement directly beneath standard clauses.

- [ ] **Step 5: Commit any verification-only adjustments**

If visual verification requires a scoped CSS or test adjustment, repeat Steps 2–4 and commit only those files:

```bash
git add docs/assets/stylesheets/extra.css tests
git commit -m "fix: refine diagnostic chip presentation"
```

If no adjustment is necessary, do not create an empty commit.
