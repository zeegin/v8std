from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.v8std_architecture_model import (
    ArchitectureModelError,
    ArtifactRef,
    build_graph,
    discover_documents,
    load_document,
    load_process_schema,
)


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_process_schema(ROOT)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write(self, relative_path: str, content: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        return path

    def valid_adr(self, path: str = "spec/adr/2026-08-14-page-reading-via-resources.md") -> Path:
        return self.write(
            path,
            """
            ---
            schema_version: 1
            kind: adr
            id: PAGE_READING_VIA_RESOURCES
            scope: product
            design: design:mcp-v3-resource-contract
            requirements: [RESOURCE_PAGES_ARE_READABLE]
            aliases: [ADR-0004]
            supersedes: []
            cancels: []
            invariants: []
            contracts: [contract:MCP_RESOURCE_READING@3.0]
            ---

            # Page reading via resources
            """,
        )

    def test_loads_valid_adr_with_canonical_key_and_date(self) -> None:
        document = load_document(self.valid_adr(), self.root, self.schema)

        self.assertEqual(document.key, "adr:PAGE_READING_VIA_RESOURCES")
        self.assertEqual(document.created_on.isoformat(), "2026-08-14")
        self.assertIn(
            ArtifactRef.parse("contract:MCP_RESOURCE_READING@3.0"),
            document.references,
        )

    def test_rejects_invalid_gregorian_date(self) -> None:
        path = self.valid_adr("spec/adr/2026-02-30-page-reading-via-resources.md")

        with self.assertRaisesRegex(ArchitectureModelError, "Gregorian date"):
            load_document(path, self.root, self.schema)

    def test_rejects_filename_identity_mismatch(self) -> None:
        path = self.valid_adr("spec/adr/2026-08-14-different-decision.md")

        with self.assertRaisesRegex(ArchitectureModelError, "does not match id"):
            load_document(path, self.root, self.schema)

    def test_rejects_forbidden_status(self) -> None:
        path = self.valid_adr()
        content = path.read_text(encoding="utf-8").replace(
            "scope: product", "scope: product\nstatus: accepted"
        )
        path.write_text(content, encoding="utf-8")

        with self.assertRaisesRegex(ArchitectureModelError, "forbidden field 'status'"):
            load_document(path, self.root, self.schema)

    def test_contract_reference_round_trips(self) -> None:
        reference = ArtifactRef.parse("contract:MCP_RESOURCE_READING@3.2")

        self.assertEqual(reference.kind, "contract")
        self.assertEqual(reference.identity, "MCP_RESOURCE_READING")
        self.assertEqual(reference.version, 3)
        self.assertEqual(reference.revision, 2)
        self.assertEqual(str(reference), "contract:MCP_RESOURCE_READING@3.2")

    def test_graph_records_duplicate_canonical_keys(self) -> None:
        first = load_document(self.valid_adr(), self.root, self.schema)
        second_path = self.root / "copy" / first.path.name
        second_path.parent.mkdir(parents=True)
        second_path.write_text(
            (self.root / first.path).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        second = load_document(second_path, self.root, self.schema, validate_path=False)

        graph = build_graph([first, second])

        self.assertEqual(graph.duplicate_keys, ("adr:PAGE_READING_VIA_RESOURCES",))

    def test_rejects_duplicate_yaml_key(self) -> None:
        path = self.valid_adr()
        content = path.read_text(encoding="utf-8").replace(
            "scope: product", "scope: product\nscope: process"
        )
        path.write_text(content, encoding="utf-8")

        with self.assertRaisesRegex(ArchitectureModelError, "duplicate YAML key"):
            load_document(path, self.root, self.schema)

    def test_plan_completion_is_derived_from_checkboxes(self) -> None:
        incomplete_path = self.write(
            "spec/plans/2026-08-14-candidate-plan.md",
            """
            ---
            schema_version: 1
            kind: plan
            id: candidate
            design: design:candidate
            implements: [design:candidate]
            ---

            - [x] Done
            - [ ] Pending
            """,
        )
        complete_path = self.write(
            "spec/plans/2026-08-14-complete-plan.md",
            """
            ---
            schema_version: 1
            kind: plan
            id: complete
            design: design:complete
            implements: [design:complete]
            ---

            - [x] Done
            """,
        )

        incomplete_plan = load_document(incomplete_path, self.root, self.schema)
        complete_plan = load_document(complete_path, self.root, self.schema)

        self.assertFalse(incomplete_plan.is_complete_plan)
        self.assertTrue(complete_plan.is_complete_plan)

    def test_discovery_extracts_requirement_headings_only_in_requirements_section(self) -> None:
        self.write(
            "spec/designs/2026-08-14-example-design.md",
            """
            ---
            schema_version: 1
            kind: design
            id: example
            scope: product
            requirements:
              introduces: [REAL_REQUIREMENT]
              uses: []
              replaces: {}
              cancels: []
            decisions: []
            invariants: []
            contracts: []
            plans: []
            supersedes: []
            cancels: []
            ---

            ## Требования

            ### REAL_REQUIREMENT

            Definition.

            ## Notes

            ### NOT_A_REQUIREMENT
            """,
        )

        graph = build_graph(discover_documents(self.root, self.schema))

        self.assertEqual(
            graph.requirements,
            {"REAL_REQUIREMENT": "design:example"},
        )


if __name__ == "__main__":
    unittest.main()
