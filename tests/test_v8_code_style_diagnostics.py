import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = REPO_ROOT / "docs" / "diagnostics" / "v8-code-style"
CANONICAL_IDS = {
    "common-module-server-call",
    "event-handler-boolean-param",
    "restriction-execute-external-code",
    "restriction-execute-external-component-code",
    "secure-password-storage",
    "security-software-call",
    "structure-constructor-too-many-keys",
    "structure-constructor-value-type",
}
LEGACY_IDS = {
    "event-heandler-boolean-param": "event-handler-boolean-param",
    "structure-consructor-too-many-keys": "structure-constructor-too-many-keys",
    "structure-consructor-value-type": "structure-constructor-value-type",
}


class V8CodeStyleDiagnosticsTests(unittest.TestCase):
    def diagnostic_paths(self):
        return sorted(path for path in CATALOG_DIR.glob("*.md") if path.name != "index.md")

    def expected_ids(self):
        catalog = json.loads(
            (REPO_ROOT / "data" / "diagnostic-sources.json").read_text(encoding="utf-8")
        )
        family = next(
            family
            for family in catalog["families"]
            if family["family"] == "v8-code-style"
        )
        return {diagnostic["id"] for diagnostic in family["diagnostics"]}

    def test_catalog_contains_current_canonical_diagnostics(self):
        ids = {path.stem for path in self.diagnostic_paths()}

        self.assertEqual(ids, self.expected_ids())
        self.assertTrue(CANONICAL_IDS <= ids)
        self.assertTrue(LEGACY_IDS.keys().isdisjoint(ids))

    def test_page_markers_and_sources_use_canonical_id(self):
        for path in self.diagnostic_paths():
            content = path.read_text(encoding="utf-8")
            marker = re.search(r"^###### v8cs:([A-Za-z0-9_-]+)$", content, re.MULTILINE)

            self.assertIsNotNone(marker, path)
            self.assertEqual(marker.group(1), path.stem, path)
            self.assertIn(f"/markdown/ru/{path.stem}.md", content, path)

    def test_legacy_ids_are_aliases_of_canonical_pages(self):
        rules = (REPO_ROOT / "retrieval-rules.yml").read_text(encoding="utf-8")

        for legacy_id, canonical_id in LEGACY_IDS.items():
            rule = re.search(
                rf'primary: "v8cs:{re.escape(canonical_id)}"(?P<body>.*?)(?=\n  - id:|\Z)',
                rules,
                re.DOTALL,
            )
            self.assertIsNotNone(rule, canonical_id)
            self.assertIn(f'- "v8cs:{legacy_id}"', rule.group("body"))
            self.assertIn(f'- "{legacy_id}"', rule.group("body"))

    def test_site_exposes_canonical_links(self):
        diagnostics_index = (REPO_ROOT / "docs" / "diagnostics" / "index.md").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "v8-code-style/event-handler-boolean-param.md",
            diagnostics_index,
        )
        self.assertNotIn("v8-code-style/event-heandler-boolean-param.md", diagnostics_index)


if __name__ == "__main__":
    unittest.main()
