from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path

import yaml

from scripts.v8std_architecture_model import (
    build_graph,
    discover_documents,
    load_process_schema,
)
from scripts.v8std_architecture_validation import compute_states, validate_graph


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_process_schema(ROOT)
        cls.graph = build_graph(discover_documents(ROOT, cls.schema))
        cls.states = compute_states(
            cls.graph,
            accepted_keys=frozenset(cls.graph.documents),
        )

    def test_complete_corpus_uses_one_valid_model(self) -> None:
        self.assertEqual(validate_graph(self.graph), [])
        self.assertEqual(
            sorted(path.name for path in (ROOT / "spec").glob("*.md")),
            ["README.md"],
        )

    def test_mcp_design_lifecycle_reflects_monitoring_retirement(self) -> None:
        superseded = {
            "design:mcp-v3-resource-contract",
            "design:mcp-100k-agent-capacity",
            "design:mcp-monitoring-dashboard",
            "design:mcp-container-monitor-input",
        }

        for reference in superseded:
            self.assertIn("SUPERSEDED", self.states[reference])

        planned = {
            "design:mcp-openmetrics-generation",
        }

        for reference in planned:
            self.assertEqual(self.states[reference], frozenset({"ACCEPTED"}))

    def test_evidence_backed_july_designs_are_implemented(self) -> None:
        expected_implemented = {
            "design:diagnostics-by-standard-clause",
            "design:english-standard-sources",
            "design:unified-diagnostic-chips",
        }

        for reference in expected_implemented:
            self.assertIn("IMPLEMENTED", self.states[reference])

    def test_numeric_adr_paths_and_current_references_are_absent(self) -> None:
        numeric_paths = sorted(
            path
            for path in (ROOT / "spec/adr").glob("*.md")
            if re.fullmatch(r"\d{4}-(?!\d{2}-).+\.md", path.name)
        )
        self.assertEqual(numeric_paths, [])

        for document in self.graph.documents.values():
            for reference in document.references:
                self.assertNotIn(reference.identity, self.graph.aliases)

        self.assertEqual(
            self.graph.aliases,
            {
                "ADR-0001": "adr:MCP_VERSION_ENDPOINT_ISOLATION",
                "ADR-0002": "adr:PUBLIC_MCP_MONITORING",
                "ADR-0003": "adr:LOCAL_OPENMETRICS_EXPOSITION",
                "ADR-0004": "adr:PAGE_READING_VIA_RESOURCES",
            },
        )

    def test_each_adr_has_one_decision_and_complete_impact_sections(self) -> None:
        required_sections = {
            "## Входные требования",
            "## Решение",
            "## Влияние на инварианты",
            "## Влияние на контракты",
            "## Отклонённые альтернативы",
        }
        impact_keys = {"introduces", "preserves", "replaces", "cancels"}

        for document in self.graph.documents.values():
            if document.kind != "adr":
                continue
            headings = {
                line for line in document.body.splitlines() if line.startswith("## ")
            }
            self.assertEqual(headings, required_sections, document.key)
            self.assertEqual(document.body.count("## Решение"), 1, document.key)
            self.assertEqual(
                set(document.front_matter["invariants"]), impact_keys, document.key
            )
            self.assertEqual(
                set(document.front_matter["contracts"]), impact_keys, document.key
            )

    def test_mandatory_architecture_policy_is_visible_before_skill_invocation(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn(
            "Прямые коммиты в `main` и push feature-ветки непосредственно",
            agents,
        )
        self.assertIn(".agents/skills/v8std-architecture/SKILL.md", agents)
        self.assertIn("локальный merge", agents)
        self.assertIn(
            "Push локального `main` выполняй только по явному запросу",
            agents,
        )
        self.assertIn(
            "автоматически запускает сборку и публикацию сайта",
            agents,
        )
        self.assertIn("Deploy MCP-сервера выполняй отдельно", agents)
        self.assertNotIn("Deploy выполняется только по явному запросу", agents)

    def test_repo_skill_uses_process_schema_without_copying_it(self) -> None:
        skill_path = ROOT / ".agents/skills/v8std-architecture/SKILL.md"
        self.assertTrue(skill_path.is_file(), skill_path)
        skill = skill_path.read_text(encoding="utf-8")

        self.assertIn("spec/process/architecture-artifacts-v2.md", skill)
        self.assertNotIn("semantic_id_pattern", skill)
        for name in (
            "impact-check.md",
            "document-triggers.md",
            "failure-recovery.md",
            "pressure-scenarios.md",
        ):
            self.assertTrue(
                (skill_path.parent / "references" / name).is_file(),
                name,
            )

    def test_repo_skill_is_not_hidden_by_gitignore(self) -> None:
        skill_path = ROOT / ".agents/skills/v8std-architecture/SKILL.md"
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(skill_path)],
            cwd=ROOT,
            check=False,
        )

        self.assertEqual(ignored.returncode, 1, skill_path)

    def test_ai_index_does_not_publish_internal_specifications(self) -> None:
        script_path = ROOT / "scripts/generate_ai_artifacts.py"
        module_spec = importlib.util.spec_from_file_location(
            "architecture_publication_boundary",
            script_path,
        )
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        index = module.build_site_ai_index(ROOT)

        for page in index["pages"]:
            for field in (
                "source_path",
                "title",
                "url",
                "markdown_url",
                "body_markdown",
            ):
                self.assertNotIn("spec/", str(page.get(field, "")), (page["id"], field))

    def test_ci_validates_complete_architecture_before_build(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        validation = ".venv/bin/python scripts/v8std_architecture.py validate"

        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn('--base-ref "$BASE_REF" --merge-ready', workflow)
        self.assertNotIn("HEAD^", workflow)
        self.assertLess(workflow.index(validation), workflow.index("docker buildx build"))

    def test_site_deployment_is_triggered_by_main_after_all_gates(self) -> None:
        workflow = yaml.load(
            (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )

        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        self.assertIn("pull_request", workflow["on"])
        jobs = workflow["jobs"]
        self.assertEqual(jobs["publish"]["needs"], "validate")
        self.assertIn("needs.validate.result == 'success'", jobs["publish"]["if"])
        steps = jobs["validate"]["steps"]
        for required_name in (
            "Validate architecture graph",
            "Build",
            "Test MCP retrieval",
            "Behavioral and generated-artifact gates",
        ):
            self.assertTrue(any(step.get("name") == required_name for step in steps), required_name)
        publication = jobs["publish"]["steps"]
        prepared = next(i for i, step in enumerate(publication) if "prepare-pages" in step.get("run", ""))
        deployed = next(i for i, step in enumerate(publication) if step.get("uses", "").startswith("actions/deploy-pages@"))
        finished = next(i for i, step in enumerate(publication) if "publish_mcp_artifacts.py finish" in step.get("run", ""))
        self.assertLess(prepared, deployed)
        self.assertLess(deployed, finished)

    def test_ci_runs_build_and_tests_as_checkout_owner(self) -> None:
        workflow = yaml.load(
            (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        steps = workflow["jobs"]["validate"]["steps"]
        build = next(step for step in steps if step.get("name") == "Build")
        self.assertIn('--user "$(id -u):$(id -g)"', build["run"])
        tests = next(step for step in steps if step.get("name") == "Test MCP retrieval")
        self.assertIn(".venv/bin/python -m unittest discover -v", tests["run"])
        self.assertNotIn("docker run", tests["run"])
        self.assertLess(steps.index(build), steps.index(tests))
        self.assertNotIn("docker.sock", json.dumps(workflow))


if __name__ == "__main__":
    unittest.main()
