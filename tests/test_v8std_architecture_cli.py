from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.v8std_architecture import main
from scripts.v8std_architecture_model import (
    build_graph,
    discover_documents,
    load_document,
    load_process_schema,
)
from scripts.v8std_architecture_validation import (
    find_impact_candidates,
    validate_frozen_documents,
    validate_graph,
)


ROOT = Path(__file__).resolve().parents[1]


class RepositoryFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        process = self.root / "spec/process/architecture-artifacts-v1.md"
        process.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "spec/process/architecture-artifacts-v1.md", process)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write(self, relative_path: str, content: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        return path

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            check=True,
            text=True,
            capture_output=True,
        )

    def initialize_git(self) -> None:
        self.git("init")
        self.git("config", "user.name", "Architecture Test")
        self.git("config", "user.email", "architecture@example.invalid")

    def commit_all(self, message: str) -> None:
        self.git("add", ".")
        self.git("commit", "-m", message)

    def valid_design(self, date_prefix: str = "2026-08-14") -> Path:
        return self.write(
            f"spec/designs/{date_prefix}-feature-design.md",
            """
            ---
            schema_version: 1
            kind: design
            id: feature
            scope: product
            requirements:
              introduces: [FEATURE_EXISTS]
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

            ### FEATURE_EXISTS

            The feature exists.
            """,
        )

    def graph(self):
        schema = load_process_schema(self.root)
        return build_graph(discover_documents(self.root, schema))


class FrozenDocumentTest(RepositoryFixture):
    def setUp(self) -> None:
        super().setUp()
        self.initialize_git()
        self.design_path = self.valid_design()
        self.write("spec/legacy-design.md", "# Legacy unstructured design\n")
        self.commit_all("base")
        self.base_ref = self.git("rev-parse", "HEAD").stdout.strip()

    def freeze_codes(self, graph=None) -> set[str]:
        if graph is None:
            graph = self.graph()
        return {
            issue.code
            for issue in validate_frozen_documents(self.root, self.base_ref, graph)
        }

    def test_rejects_editing_structured_document(self) -> None:
        self.design_path.write_text(
            self.design_path.read_text(encoding="utf-8") + "\nChanged.\n",
            encoding="utf-8",
        )

        self.assertIn("FROZEN_DOCUMENT_MODIFIED", self.freeze_codes())

    def test_rejects_deleting_structured_document(self) -> None:
        self.design_path.unlink()

        self.assertIn("FROZEN_DOCUMENT_DELETED", self.freeze_codes())

    def test_rejects_moving_structured_document(self) -> None:
        moved = self.root / "spec/designs/2026-08-15-feature-design.md"
        self.design_path.rename(moved)

        self.assertIn("FROZEN_DOCUMENT_MOVED", self.freeze_codes())

    def test_allows_successor_without_changing_predecessor(self) -> None:
        self.write(
            "spec/designs/2026-08-15-feature-successor-design.md",
            """
            ---
            schema_version: 1
            kind: design
            id: feature-successor
            scope: product
            requirements:
              introduces: []
              uses: [FEATURE_EXISTS]
              replaces: {}
              cancels: []
            decisions: []
            invariants: []
            contracts: []
            plans: []
            supersedes: [design:feature]
            cancels: []
            ---

            # Successor
            """,
        )

        self.assertFalse(self.freeze_codes())

    def test_allows_bootstrap_move_of_unstructured_base_file(self) -> None:
        legacy = self.root / "spec/legacy-design.md"
        moved = self.root / "legacy-archive.md"
        legacy.rename(moved)
        schema = load_process_schema(self.root)
        graph = build_graph(
            [
                load_document(
                    self.root / "spec/process/architecture-artifacts-v1.md",
                    self.root,
                    schema,
                ),
                load_document(self.design_path, self.root, schema),
            ]
        )

        self.assertFalse(self.freeze_codes(graph))

    def test_structured_replacement_freezes_after_commit(self) -> None:
        legacy = self.root / "spec/legacy-design.md"
        legacy.unlink()
        replacement = self.write(
            "spec/designs/2026-08-14-legacy-design.md",
            """
            ---
            schema_version: 1
            kind: design
            id: legacy
            scope: product
            requirements:
              introduces: []
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

            # Structured replacement
            """,
        )
        self.commit_all("bootstrap structured replacement")
        self.base_ref = self.git("rev-parse", "HEAD").stdout.strip()
        replacement.write_text(
            replacement.read_text(encoding="utf-8") + "\nChanged.\n",
            encoding="utf-8",
        )

        self.assertIn("FROZEN_DOCUMENT_MODIFIED", self.freeze_codes())

    def test_unresolved_requested_base_ref_is_an_error(self) -> None:
        issue_codes = {
            issue.code
            for issue in validate_frozen_documents(self.root, "missing-ref", self.graph())
        }

        self.assertEqual(issue_codes, {"BASE_REF_UNRESOLVED"})

    def test_process_schema_cannot_disable_its_own_freeze(self) -> None:
        process = self.root / "spec/process/architecture-artifacts-v1.md"
        process.write_text(
            process.read_text(encoding="utf-8").replace(
                "frozen_kinds: [design, adr, invariant, contract, plan, process]",
                "frozen_kinds: []",
            ),
            encoding="utf-8",
        )

        self.assertIn("FROZEN_DOCUMENT_MODIFIED", self.freeze_codes())


class ArchitectureCliTest(RepositoryFixture):
    def write_candidate(self) -> None:
        design_path = self.valid_design()
        design_path.write_text(
            design_path.read_text(encoding="utf-8").replace(
                "plans: []", "plans: [plan:feature]"
            ),
            encoding="utf-8",
        )
        self.write(
            "spec/plans/2026-08-14-feature-plan.md",
            """
            ---
            schema_version: 1
            kind: plan
            id: feature
            design: design:feature
            implements: [design:feature]
            ---

            - [x] First step
            - [ ] Second step
            """,
        )

    def run_cli(self, *arguments: str) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main([*arguments])
        return exit_code, output.getvalue()

    def test_validate_accepts_incomplete_candidate_but_merge_ready_rejects_it(self) -> None:
        self.write_candidate()

        exit_code, output = self.run_cli("validate", "--root", str(self.root))
        ready_code, ready_output = self.run_cli(
            "validate", "--root", str(self.root), "--merge-ready"
        )

        self.assertEqual((exit_code, output), (0, ""))
        self.assertEqual(ready_code, 1)
        self.assertIn("INCOMPLETE_PLAN spec/plans/2026-08-14-feature-plan.md:", ready_output)

    def test_validate_prints_stable_issue_format(self) -> None:
        self.write_candidate()
        plan = self.root / "spec/plans/2026-08-14-feature-plan.md"
        plan.write_text(
            plan.read_text(encoding="utf-8").replace(
                "design: design:feature", "design: design:missing"
            ),
            encoding="utf-8",
        )

        exit_code, output = self.run_cli("validate", "--root", str(self.root))

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "DANGLING_REFERENCE spec/plans/2026-08-14-feature-plan.md:",
            output,
        )

    def test_status_uses_main_ref_instead_of_treating_branch_files_as_accepted(self) -> None:
        self.initialize_git()
        self.valid_design()
        self.commit_all("accepted design")
        base_ref = self.git("rev-parse", "HEAD").stdout.strip()
        self.write(
            "spec/plans/2026-08-14-feature-plan.md",
            """
            ---
            schema_version: 1
            kind: plan
            id: feature
            design: design:feature
            implements: [design:feature]
            ---

            - [ ] Candidate step
            """,
        )

        exit_code, output = self.run_cli(
            "status", "--root", str(self.root), "--main-ref", base_ref
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("design:feature\tACCEPTED\n", output)
        self.assertIn("plan:feature\tCANDIDATE\n", output)

    def test_impact_reports_governed_change_without_validation_error(self) -> None:
        self.initialize_git()
        design_path = self.valid_design()
        design_path.write_text(
            design_path.read_text(encoding="utf-8").replace(
                "contracts: []", "contracts: [contract:MCP_API@2.0]"
            ),
            encoding="utf-8",
        )
        self.write(
            "spec/contracts/mcp-api-v2-r0.md",
            """
            ---
            schema_version: 1
            kind: contract
            id: MCP_API
            scope: product
            version: 2
            revision: 0
            compatibility: backward-compatible
            design: design:feature
            producer: MCP server
            consumers: [MCP clients]
            requirements: [FEATURE_EXISTS]
            governs: [scripts/v8std_mcp_server.py]
            conformance:
              module: tests.test_v8std_architecture_cli
            required_when: accepted
            supersedes: []
            deprecates: []
            ---

            # MCP API v2
            """,
        )
        script = self.write("scripts/v8std_mcp_server.py", "VERSION = 1\n")
        self.commit_all("base")
        base_ref = self.git("rev-parse", "HEAD").stdout.strip()
        script.write_text("VERSION = 2\n", encoding="utf-8")

        working_code, working_output = self.run_cli(
            "impact", "--root", str(self.root), "--base-ref", base_ref
        )
        self.assertEqual(working_code, 0)
        self.assertIn(
            "contract:MCP_API@2.0\tspec/contracts/mcp-api-v2-r0.md",
            working_output,
        )

        self.commit_all("change governed script")
        graph = self.graph()

        self.assertFalse(validate_graph(graph))
        self.assertEqual(
            find_impact_candidates(graph, ["scripts/v8std_mcp_server.py"]),
            [("contract:MCP_API@2.0", "spec/contracts/mcp-api-v2-r0.md")],
        )

        exit_code, output = self.run_cli(
            "impact", "--root", str(self.root), "--base-ref", base_ref
        )
        self.assertEqual(exit_code, 0)
        self.assertIn(
            "contract:MCP_API@2.0\tspec/contracts/mcp-api-v2-r0.md",
            output,
        )


if __name__ == "__main__":
    unittest.main()
