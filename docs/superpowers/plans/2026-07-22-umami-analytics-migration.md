# u.ingvar.pro Analytics Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Yandex.Metrika with the supplied `u.ingvar.pro` statistics and session-recorder scripts in every generated website page.

**Architecture:** Keep analytics in the shared `overrides/main.html` template so both normal and home pages inherit one integration. Put both deferred scripts in `extrahead`, remove the obsolete Yandex analytics block, and remove only the Yandex consent-cookie entry from the existing TOML configuration.

**Tech Stack:** Zensical, Jinja templates, TOML, Python `unittest`.

## Global Constraints

- Use website ID `e6d9711e-3090-45e1-aa57-be1a9fe4567a` for both scripts.
- Load `https://u.ingvar.pro/script.js` with `defer`.
- Load `https://u.ingvar.pro/recorder.js` with `defer`, `data-sample-rate="0.15"`, `data-mask-level="moderate"`, and `data-max-duration="300000"`.
- Both scripts must render inside `<head>` and must not depend on the former Yandex consent mechanism.
- Preserve all unrelated working-tree changes, including concurrent edits to `zensical.toml`.

---

### Task 1: Replace the shared analytics integration

**Files:**
- Create: `tests/test_analytics_integration.py`
- Modify: `overrides/main.html:55-79`
- Modify: `zensical.toml:88-93`

**Interfaces:**
- Consumes: Zensical's shared Jinja `extrahead` block and `[project.extra.consent.cookies]` configuration.
- Produces: every generated page includes the two exact `u.ingvar.pro` script tags in `<head>` and contains no Yandex analytics integration.

- [ ] **Step 1: Write the failing regression test**

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN_TEMPLATE = ROOT / "overrides" / "main.html"
CONFIG = ROOT / "zensical.toml"


class AnalyticsIntegrationTest(unittest.TestCase):
    def test_u_ingvar_scripts_replace_yandex_analytics(self):
        template = MAIN_TEMPLATE.read_text(encoding="utf-8")
        config = CONFIG.read_text(encoding="utf-8")

        extrahead = template.split("{% block extrahead %}", 1)[1].split("{% endblock %}", 1)[0]
        self.assertIn(
            '<script defer src="https://u.ingvar.pro/script.js" '
            'data-website-id="e6d9711e-3090-45e1-aa57-be1a9fe4567a"></script>',
            extrahead,
        )
        self.assertIn(
            '<script defer src="https://u.ingvar.pro/recorder.js" '
            'data-website-id="e6d9711e-3090-45e1-aa57-be1a9fe4567a" '
            'data-sample-rate="0.15" data-mask-level="moderate" '
            'data-max-duration="300000"></script>',
            extrahead,
        )
        combined = template + config
        self.assertNotIn("mc.yandex.ru", combined)
        self.assertNotIn("Yandex.Metrika", combined)
        self.assertNotIn("{% block analytics %}", template)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/python -m unittest -v tests.test_analytics_integration`

Expected: `FAIL` because the `u.ingvar.pro` script tags are absent from `extrahead`.

- [ ] **Step 3: Write the minimal implementation**

Delete the complete `{% block analytics %}` block from `overrides/main.html`. Add these exact lines after `{{ super() }}` in the existing `{% block extrahead %}`:

```html
  <script defer src="https://u.ingvar.pro/script.js" data-website-id="e6d9711e-3090-45e1-aa57-be1a9fe4567a"></script>
  <script defer src="https://u.ingvar.pro/recorder.js" data-website-id="e6d9711e-3090-45e1-aa57-be1a9fe4567a" data-sample-rate="0.15" data-mask-level="moderate" data-max-duration="300000"></script>
```

Delete only this existing TOML line, leaving every other concurrent edit intact:

```toml
analytics = "Yandex.Metrika"
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `.venv/bin/python -m unittest -v tests.test_analytics_integration`

Expected: `OK` with one passing test.

- [ ] **Step 5: Run complete verification**

Run: `VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict`

Expected: exit code `0`.

Run: `.venv/bin/python -m unittest discover -v`

Expected: exit code `0`, except failures proven to originate solely from unrelated concurrent working-tree deletions must be reported explicitly and not hidden.

Run: `.venv/bin/python -c 'from pathlib import Path; from html.parser import HTMLParser; html=next(Path("site").rglob("index.html")).read_text(encoding="utf-8"); head=html.split("</head>", 1)[0]; assert "https://u.ingvar.pro/script.js" in head; assert "https://u.ingvar.pro/recorder.js" in head; assert "mc.yandex.ru" not in html'`

Expected: exit code `0`, proving both scripts render in `<head>` and Yandex is absent from the sampled generated page.

Run: `git diff --check`

Expected: exit code `0`.

- [ ] **Step 6: Commit only the analytics implementation**

```bash
git add -- tests/test_analytics_integration.py overrides/main.html
git add -p -- zensical.toml
git commit -m "feat: migrate analytics to u.ingvar.pro"
```

The staged TOML hunk must contain only deletion of `analytics = "Yandex.Metrika"`; do not stage the unrelated removal of `assets/javascripts/announce.js`.
