import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_ai_artifacts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_ai_artifacts", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GenerateAiArtifactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.index = cls.module.build_site_ai_index(REPO_ROOT)
        cls.pages_by_id = {page["id"]: page for page in cls.index["pages"]}

    def test_extracts_expected_standard_and_diagnostic_aliases(self):
        std437 = self.pages_by_id["std437"]
        bslls = self.pages_by_id["bslls:AssignAliasFieldsInQuery"]
        acc = self.pages_by_id["acc:1245"]
        v8cs = self.pages_by_id["v8cs:common-module-name-client-server"]

        self.assertIn("#std437", std437["aliases"])
        self.assertIn("std 437", std437["aliases"])
        self.assertIn("AssignAliasFieldsInQuery", bslls["aliases"])
        self.assertIn("апк 1245", acc["aliases"])
        self.assertIn("common-module-name-client-server", v8cs["aliases"])

    def test_builds_standard_diagnostic_and_edt_relations_from_markdown_links(self):
        std437 = self.pages_by_id["std437"]
        bslls = self.pages_by_id["bslls:AssignAliasFieldsInQuery"]
        acc = self.pages_by_id["acc:1245"]
        graph = self.index["graph"]

        self.assertIn(
            "bslls:AssignAliasFieldsInQuery",
            [item["id"] for item in std437["related"] if item["relation"] == "diagnostic"],
        )
        self.assertIn(
            "std437",
            [item["id"] for item in bslls["related"] if item["relation"] == "standard"],
        )
        self.assertIn(
            "v8cs:common-module-name-client-server",
            [item["id"] for item in acc["related"] if item["relation"] == "edt_check"],
        )
        self.assertIn("bslls:AssignAliasFieldsInQuery", graph["standards"]["std437"])
        self.assertIn("std469", graph["diagnostics"]["acc:1245"]["standards"])
        self.assertIn("v8cs:common-module-name-client-server", graph["acc_to_edt"]["acc:1245"])

    def test_pages_jsonl_is_valid_and_urls_are_unique(self):
        payload = self.module.build_pages_jsonl(self.index["pages"])
        rows = [json.loads(line) for line in payload.splitlines()]
        urls = [row["url"] for row in rows]

        self.assertEqual(len(urls), len(set(urls)))
        self.assertGreater(len(rows), 1000)
        self.assertTrue(all(row["body_markdown"] for row in rows))

    def test_llms_txt_contains_required_shape_and_acceptance_relation(self):
        payload = self.module.build_llms_txt(self.index)

        self.assertTrue(payload.startswith("# Стандарты разработки 1С\n"))
        self.assertIn("\n> Система стандартов", payload)
        self.assertIn("\n## Machine-Readable Files\n", payload)
        self.assertIn("\n## Standards\n", payload)
        self.assertIn("AssignAliasFieldsInQuery", payload)
        self.assertIn("std437", payload)


if __name__ == "__main__":
    unittest.main()
