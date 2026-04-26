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

    def test_llms_full_excludes_pages_with_front_matter_flag_only(self):
        payload = self.module.build_llms_full_txt(self.index)
        jsonl_rows = [
            json.loads(line)
            for line in self.module.build_pages_jsonl(self.index["pages"]).splitlines()
        ]
        jsonl_ids = {row["id"] for row in jsonl_rows}

        excluded_ids = {
            "home",
            "diagnostics",
            "diagnostics:acc",
            "diagnostics:bslls",
            "diagnostics:v8_code_style",
        }

        for page_id in excluded_ids:
            self.assertNotIn(f"### {page_id} - ", payload)
            self.assertIn(page_id, jsonl_ids)

        self.assertIn("### std437 - ", payload)
        self.assertIn("### bslls:AssignAliasFieldsInQuery - ", payload)

    def test_normalizes_internal_markdown_links_to_absolute_urls(self):
        std437 = self.pages_by_id["std437"]["body_markdown"]
        search_help = self.pages_by_id["search_help"]["body_markdown"]

        self.assertIn(
            "[#bslls:AssignAliasFieldsInQuery](https://v8std.ru/diagnostics/bslls/AssignAliasFieldsInQuery/)",
            std437,
        )
        self.assertIn("[/llms.txt](https://v8std.ru/llms.txt)", search_help)
        self.assertNotIn("../diagnostics/bslls/AssignAliasFieldsInQuery.md", std437)

    def test_llms_full_uses_readable_metadata_and_has_no_relative_links(self):
        payload = self.module.build_llms_full_txt(self.index)

        self.assertNotIn("#!bsl", payload)
        self.assertNotIn('=== ":fontawesome-brands-linux: linux"', payload)
        self.assertNotIn("!!! success", payload)
        self.assertNotIn("{ width=", payload)
        self.assertNotIn("\ntype=\"button\"\n", payload)
        self.assertNotRegex(payload, r"\]\((?!https?://|mailto:)[^)]+\.md(?:#[^)]+)?\)")
        self.assertLess(max(len(line) for line in payload.splitlines()), 500)

    def test_cleans_theme_markup_for_public_llm_body(self):
        raw = """###### #std999

Текст `#!bsl &НаКлиенте` и `#!sdbl РАЗРЕШЕННЫЕ`.

=== ":fontawesome-brands-linux: linux"

    !!! failure "Неправильно"

        ```bsl hl_lines="1 9"
        Сообщить("Плохо");
        ```

~[#bslls:AssignAliasFieldsInQuery](../diagnostics/bslls/AssignAliasFieldsInQuery.md)~

![Карта маршрута](480.img1.jpg){ width="565" }
| ++ctrl+shift+f++<br>++enter++ | Действие |
<span class="std-rgb-dot" title="RGB: 1,2,3"></span>
"""

        cleaned = self.module.clean_llm_markdown(raw)

        self.assertIn("ID: #std999", cleaned)
        self.assertIn("`&НаКлиенте`", cleaned)
        self.assertIn("`РАЗРЕШЕННЫЕ`", cleaned)
        self.assertIn("#### linux", cleaned)
        self.assertIn("#### Неправильно", cleaned)
        self.assertIn("```bsl\nСообщить", cleaned)
        self.assertIn("[#bslls:AssignAliasFieldsInQuery]", cleaned)
        self.assertIn("Изображение: Карта маршрута (480.img1.jpg)", cleaned)
        self.assertIn("Ctrl+Shift+F; Enter", cleaned)
        self.assertNotIn("#!bsl", cleaned)
        self.assertNotIn("===", cleaned)
        self.assertNotIn("!!!", cleaned)
        self.assertNotIn("fontawesome", cleaned)
        self.assertNotIn("{ width=", cleaned)
        self.assertNotIn("<span", cleaned)

    def test_public_pages_use_cleaned_markdown_body(self):
        std437 = self.pages_by_id["std437"]["body_markdown"]
        support = self.pages_by_id["support"]["body_markdown"]

        self.assertIn("`КАК`", std437)
        self.assertIn("#### Правильно", std437)
        self.assertIn("#### linux", support)
        self.assertNotIn("#!sdbl", std437)
        self.assertNotIn("!!! success", std437)
        self.assertNotIn('=== ":fontawesome-brands-linux: linux"', support)

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
