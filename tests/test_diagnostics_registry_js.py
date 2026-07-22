import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DiagnosticsRegistryJavascriptTests(unittest.TestCase):
    def test_module_supports_navigation_and_plain_dom_initialization(self):
        source = (ROOT / "docs/assets/javascripts/diagnostics-registry.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("document$", source)
        self.assertIn("DOMContentLoaded", source)
        self.assertIn("data-diagnostics-registry", source)

    def test_filter_preserves_open_state_and_respects_empty_toggle(self):
        source = (ROOT / "docs/assets/javascripts/diagnostics-registry.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("initialOpen", source)
        self.assertIn("data-empty", source)
        self.assertIn("showEmpty.checked", source)
        self.assertIn("standard.open = true", source)
        self.assertIn('replace(/^#(?=std\\d)/, "")', source)

    def test_exact_standard_query_keeps_every_clause_visible(self):
        source = (ROOT / "docs/assets/javascripts/diagnostics-registry.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function standardIdFromQuery(query)", source)
        self.assertIn('return `std${query}`;', source)
        self.assertIn("const exactStandardMatch =", source)
        self.assertIn("const visible = exactStandardMatch ||", source)

    def test_zensical_loads_registry_module(self):
        config = (ROOT / "zensical.toml").read_text(encoding="utf-8")

        self.assertIn('"assets/javascripts/diagnostics-registry.js"', config)

    def test_registry_styles_are_scoped_and_responsive(self):
        source = (ROOT / "docs/assets/stylesheets/extra.css").read_text(encoding="utf-8")

        self.assertIn(".diagnostics-registry__controls", source)
        self.assertIn(".diagnostics-standard__summary:focus-visible", source)
        self.assertIn(".diagnostics-standard__summary::before", source)
        self.assertIn("content: none", source)
        self.assertIn(".diagnostic-links", source)
        self.assertIn(".md-typeset .diagnostic-chip", source)
        self.assertIn(".md-typeset .diagnostic-chip:focus-visible", source)
        self.assertIn("max-width: 44.984375em", source)

    def test_registry_uses_the_shared_diagnostic_chip_class(self):
        source = (ROOT / "docs/diagnostics/index.md").read_text(encoding="utf-8")

        self.assertIn('class="diagnostic-chip"', source)
        self.assertNotIn('class="diagnostics-clause__diagnostic"', source)

    def test_help_pages_link_every_canonical_diagnostic_as_a_chip(self):
        pattern = re.compile(
            r"(?:acc:\d+|bslls:[A-Za-z][A-Za-z0-9_-]*|"
            r"v8cs:[A-Za-z0-9][A-Za-z0-9_-]*)"
        )
        anchor = re.compile(
            r'<a class="diagnostic-chip" href="[^"]+">'
            r"(?:acc:\d+|bslls:[A-Za-z][A-Za-z0-9_-]*|"
            r"v8cs:[A-Za-z0-9][A-Za-z0-9_-]*)</a>"
        )

        for relative_path in ("docs/search-help.md", "docs/mcp.md"):
            with self.subTest(path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertNotRegex(anchor.sub("", source), pattern)

        search_help = (ROOT / "docs/search-help.md").read_text(encoding="utf-8")
        mcp_help = (ROOT / "docs/mcp.md").read_text(encoding="utf-8")
        self.assertIn(
            'class="diagnostic-chip" href="diagnostics/acc/1245.md"', search_help
        )
        self.assertIn(
            'class="diagnostic-chip" href="diagnostics/bslls/UsingModalWindows.md"',
            mcp_help,
        )


if __name__ == "__main__":
    unittest.main()
