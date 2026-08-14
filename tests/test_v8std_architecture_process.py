from __future__ import annotations

import tomllib
import unittest
from pathlib import Path
from typing import Any, Iterator

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "spec/process/architecture-artifacts-v1.md"


def load_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"{path} has no YAML front matter")
    _, payload, _ = text.split("---", 2)
    loaded = yaml.safe_load(payload)
    if not isinstance(loaded, dict):
        raise AssertionError(f"{path} front matter is not a mapping")
    return loaded


def iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, nested in value.items():
            yield from iter_strings(key)
            yield from iter_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_strings(nested)


class ArchitectureProcessTest(unittest.TestCase):
    def test_process_schema_is_versioned_and_machine_readable(self) -> None:
        payload = load_front_matter(PROCESS)

        self.assertEqual(payload["kind"], "process")
        self.assertEqual(payload["id"], "architecture-artifacts")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["version"], 1)
        self.assertNotIn("status", payload)
        self.assertEqual(
            payload["schema"]["semantic_id_pattern"], r"^[A-Z][A-Z_]*$"
        )
        self.assertEqual(
            payload["schema"]["adr_filename_pattern"],
            r"^\d{4}-\d{2}-\d{2}-[a-z]+(?:-[a-z]+)*\.md$",
        )

    def test_internal_spec_is_absent_from_site_navigation(self) -> None:
        config = tomllib.loads((ROOT / "zensical.toml").read_text(encoding="utf-8"))
        nav_values = list(iter_strings(config["project"]["nav"]))

        self.assertFalse(
            any(value == "spec" or value.startswith("spec/") for value in nav_values),
            "internal spec/ must not be published through Zensical navigation",
        )


if __name__ == "__main__":
    unittest.main()
