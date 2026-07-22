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

    def test_zensical_loads_registry_module(self):
        config = (ROOT / "zensical.toml").read_text(encoding="utf-8")

        self.assertIn('"assets/javascripts/diagnostics-registry.js"', config)


if __name__ == "__main__":
    unittest.main()
