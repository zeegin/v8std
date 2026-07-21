import importlib.util
import json
import tempfile
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_ai_artifacts.py"
UI_DESIGN_NAV_SECTIONS = {
    "Общее",
    "Проектирование интерфейсов для 8.3",
    "Проектирование интерфейсов для 8.2",
    "Проектирование интерфейсов для обычного приложения",
}


def load_module():
    spec = importlib.util.spec_from_file_location("generate_ai_artifacts", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def iter_nav_items(node, path=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from iter_nav_items(value, path + (key,))
    elif isinstance(node, list):
        for item in node:
            yield from iter_nav_items(item, path)
    elif isinstance(node, str):
        yield path, node


def collect_ui_design_standard_ids():
    with (REPO_ROOT / "zensical.toml").open("rb") as handle:
        config = tomllib.load(handle)

    result = []
    for path, target in iter_nav_items(config["project"]["nav"]):
        if "Разработка пользовательских интерфейсов" not in path:
            continue

        section_index = path.index("Разработка пользовательских интерфейсов") + 1
        if section_index >= len(path) or path[section_index] not in UI_DESIGN_NAV_SECTIONS:
            continue

        if target.startswith("std/") and target.endswith(".md"):
            page_id = f"std{Path(target).stem}"
            if page_id not in result:
                result.append(page_id)

    return result


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

    def test_legacy_v8cs_typos_are_aliases_of_canonical_diagnostics(self):
        expected_aliases = {
            "v8cs:event-handler-boolean-param": "v8cs:event-heandler-boolean-param",
            "v8cs:structure-constructor-too-many-keys": "v8cs:structure-consructor-too-many-keys",
            "v8cs:structure-constructor-value-type": "v8cs:structure-consructor-value-type",
        }

        for canonical_id, legacy_id in expected_aliases.items():
            self.assertIn(legacy_id, self.pages_by_id[canonical_id]["aliases"])

    def test_builds_standard_diagnostic_and_edt_relations_from_markdown_links(self):
        std437 = self.pages_by_id["std437"]
        bslls = self.pages_by_id["bslls:AssignAliasFieldsInQuery"]
        acc = self.pages_by_id["acc:1245"]

        self.assertIn(
            "bslls:AssignAliasFieldsInQuery",
            [item["id"] for item in std437["related"] if item["relation"] == "diagnostic"],
        )
        self.assertIn(
            "https://v8std.ru/diagnostics/bslls/AssignAliasFieldsInQuery.md",
            [item["markdown_url"] for item in std437["related"]],
        )
        self.assertIn(
            "std437",
            [item["id"] for item in bslls["related"] if item["relation"] == "standard"],
        )
        self.assertIn(
            "v8cs:common-module-name-client-server",
            [item["id"] for item in acc["related"] if item["relation"] == "edt_check"],
        )

    def test_pages_jsonl_is_valid_and_urls_are_unique(self):
        payload = self.module.build_pages_jsonl(self.index["pages"])
        rows = [json.loads(line) for line in payload.splitlines()]
        urls = [row["url"] for row in rows]

        self.assertEqual(len(urls), len(set(urls)))
        self.assertGreater(len(rows), 1000)
        self.assertTrue(all(row["body_markdown"] for row in rows))
        self.assertTrue(all("aliases" in row for row in rows))
        self.assertTrue(all("related" in row for row in rows))
        self.assertTrue(all("markdown_url" in row for row in rows))
        self.assertEqual(
            self.pages_by_id["std437"]["markdown_url"],
            "https://v8std.ru/std/437.md",
        )

    def test_writer_removes_retired_machine_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            ai_dir = docs_dir / self.module.AI_DIR
            ai_dir.mkdir()
            retired_paths = [
                ai_dir / "graph.json",
                ai_dir / "search-aliases.json",
            ]
            for path in retired_paths:
                path.write_text("{}\n", encoding="utf-8")

            self.module.write_ai_artifacts(
                {
                    "project": {
                        "site_name": "Test",
                        "site_description": "Test docs",
                        "site_url": "https://example.test",
                    },
                    "docs_dir": docs_dir,
                    "pages": [],
                }
            )

            self.assertTrue((docs_dir / self.module.LLMS_TXT).is_file())
            self.assertTrue((docs_dir / self.module.LLMS_FULL_TXT).is_file())
            self.assertTrue((ai_dir / self.module.PAGES_JSONL).is_file())
            for path in retired_paths:
                self.assertFalse(path.exists())

    def test_llms_ignore_excludes_service_pages_from_mcp_index(self):
        llms_txt = self.module.build_llms_txt(self.index)
        llms_full = self.module.build_llms_full_txt(self.index)
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
            page = self.pages_by_id[page_id]
            self.assertTrue(page["_llms_ignored"])
            self.assertNotIn(f"]({page['url']})", llms_txt)
            self.assertNotIn(f"]({page['markdown_url']})", llms_txt)
            self.assertNotIn(f"### {page_id} - ", llms_full)
            self.assertNotIn(page_id, jsonl_ids)

        self.assertIn("### std437 - ", llms_full)
        self.assertIn("### bslls:AssignAliasFieldsInQuery - ", llms_full)
        self.assertIn("std437", jsonl_ids)

    def test_llms_ignore_excludes_ui_design_standards_from_llms_but_keeps_them_searchable_by_mcp(self):
        llms_txt = self.module.build_llms_txt(self.index)
        llms_full = self.module.build_llms_full_txt(self.index)
        jsonl_rows = [
            json.loads(line)
            for line in self.module.build_pages_jsonl(self.index["pages"]).splitlines()
        ]
        jsonl_ids = {row["id"] for row in jsonl_rows}
        page_ids = collect_ui_design_standard_ids()

        self.assertGreater(len(page_ids), 100)
        for page_id in page_ids:
            page = self.pages_by_id[page_id]
            self.assertTrue(page["_llms_ignored"])
            self.assertNotIn(f"#{page_id}", llms_txt)
            self.assertNotIn(f"#{page_id}", llms_full)
            self.assertNotIn(page["url"], llms_txt)
            self.assertNotIn(page["url"], llms_full)
            self.assertNotIn(f"### {page_id} - ", llms_full)
            self.assertIn(page_id, jsonl_ids)

        ignored_id_set = set(page_ids)
        self.assertTrue(
            any(
                any(item["id"] in ignored_id_set for item in row["related"])
                for row in jsonl_rows
            )
        )

    def test_normalizes_internal_markdown_links_to_absolute_urls(self):
        std437 = self.pages_by_id["std437"]["body_markdown"]
        search_help = self.pages_by_id["search_help"]["body_markdown"]

        self.assertIn(
            "[#bslls:AssignAliasFieldsInQuery](https://v8std.ru/diagnostics/bslls/AssignAliasFieldsInQuery/)",
            std437,
        )
        self.assertIn("[/llms.txt](https://v8std.ru/llms.txt)", search_help)
        self.assertNotIn("../diagnostics/bslls/AssignAliasFieldsInQuery.md", std437)

    def test_writes_public_per_page_markdown_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)
            self.module.write_site_markdown_pages(self.index, site_dir)

            std437 = site_dir / "std" / "437.md"
            self.assertTrue(std437.is_file())
            payload = std437.read_text(encoding="utf-8")

            self.assertIn("# Оформление текстов запросов #std437", payload)
            self.assertIn("Canonical HTML: https://v8std.ru/std/437/", payload)
            self.assertIn("Markdown URL: https://v8std.ru/std/437.md", payload)
            self.assertIn("## Content", payload)
            self.assertIn("ID: #std437", payload)

            ignored_id = collect_ui_design_standard_ids()[0]
            ignored_source_path = self.pages_by_id[ignored_id]["source_path"]
            self.assertFalse((site_dir / ignored_source_path).exists())

    def test_llms_full_uses_readable_metadata_and_has_no_relative_links(self):
        payload = self.module.build_llms_full_txt(self.index)

        self.assertIn("Markdown URL: https://v8std.ru/std/437.md", payload)
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
        self.assertNotIn("graph.json", payload)
        self.assertNotIn("search-aliases.json", payload)
        self.assertIn("[#std437](https://v8std.ru/std/437.md)", payload)
        self.assertIn("HTML: https://v8std.ru/std/437/", payload)
        self.assertIn("AssignAliasFieldsInQuery", payload)
        self.assertIn("std437", payload)


if __name__ == "__main__":
    unittest.main()
