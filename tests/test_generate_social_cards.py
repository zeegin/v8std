import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_social_cards.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_social_cards", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StripMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_strips_inlinehilite_bsl_prefix(self):
        self.assertEqual(self.module.strip_markdown("`#!bsl Пустой`"), "Пустой")

    def test_strips_inlinehilite_sdbl_prefix(self):
        self.assertEqual(self.module.strip_markdown("`#!sdbl РАЗРЕШЕННЫЕ`"), "РАЗРЕШЕННЫЕ")

    def test_preserves_meaningful_symbols_inside_inlinehilite(self):
        self.assertEqual(self.module.strip_markdown("`#!bsl #Если Сервер`"), "#Если Сервер")

    def test_preserves_bare_inlinehilite_literal(self):
        self.assertEqual(self.module.strip_markdown("`#!sdbl`"), "#!sdbl")

    def test_flattens_inline_code_and_links(self):
        value = "Обычный `код` и [ссылка](https://example.com) с **выделением**."
        self.assertEqual(self.module.strip_markdown(value), "Обычный код и ссылка с выделением.")

    def test_list_summary_stops_before_plural_source_section(self):
        value = (
            "Краткое описание.\n\n"
            "###### Источники\n\n"
            "- [Русская версия — ИТС](https://its.1c.ru/example)\n"
            "- [English version — 1Ci Knowledge Base](https://kb.1ci.com/example)\n"
        )
        self.assertEqual(self.module.extract_list_summary(value), "")


class BuildPageMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.project = cls.module.load_project(REPO_ROOT)
        cls.docs_dir = REPO_ROOT / cls.project.get("docs_dir", "docs")

    def build_page(self, relative_path: str) -> dict:
        source = self.docs_dir / relative_path
        return self.module.build_page_metadata(source, self.docs_dir, self.project)

    def test_std438_description_removes_bsl_prefix(self):
        page = self.build_page("std/438.md")

        self.assertIn("Пустой", page["description"])
        self.assertIn("Пустой", page["card_description"])
        self.assertNotIn("!bsl", page["description"])
        self.assertNotIn("!bsl", page["card_description"])

    def test_std415_metadata_removes_sdbl_prefix(self):
        page = self.build_page("std/415.md")

        for key in ("title", "seo_title", "description", "card_description"):
            self.assertIn("РАЗРЕШЕННЫЕ", page[key])
            self.assertNotIn("!sdbl", page[key])

    def test_std762_description_preserves_bare_inlinehilite_literal(self):
        page = self.build_page("std/762.md")

        self.assertIn("#!sdbl", page["description"])
        self.assertIn("#!sdbl", page["card_description"])


class SocialCardSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.project = cls.module.load_project(REPO_ROOT)
        cls.docs_dir = REPO_ROOT / cls.project.get("docs_dir", "docs")
        plugins = cls.project.get("plugins", {})
        social = plugins.get("social", {})
        layout_options = social.get("cards_layout_options", {})
        cls.colors = {
            "background": layout_options.get("background_color", "#303F8F"),
            "foreground": layout_options.get("color", "#FFFFFF"),
        }
        cls.logo_path = REPO_ROOT / layout_options.get(
            "logo",
            "docs/assets/images/logo-social.png",
        )

    def build_page(self, relative_path: str) -> dict:
        source = self.docs_dir / relative_path
        return self.module.build_page_metadata(source, self.docs_dir, self.project)

    def assert_card_is_rendered(self, page: dict) -> None:
        image = self.module.render_card(page, self.project, self.colors, self.logo_path)

        self.assertEqual("RGB", image.mode)
        self.assertEqual((1200, 630), image.size)
        colors = image.convert("RGB").getcolors(maxcolors=1_000_000)
        self.assertIsNotNone(colors)
        self.assertGreater(len(colors), 10)

    def test_render_card_smoke_for_homepage(self):
        self.assert_card_is_rendered(self.build_page("index.md"))

    def test_render_card_smoke_for_std437(self):
        self.assert_card_is_rendered(self.build_page("std/437.md"))

    def test_page_meta_partial_references_social_cards(self):
        pages = [
            self.build_page("index.md"),
            self.build_page("std/437.md"),
        ]
        payload = self.module.build_page_meta_partial(pages, self.project)

        self.assertIn('{% set page_meta_locale = "ru_RU" %}', payload)
        self.assertIn("https://v8std.ru/assets/social/index.png", payload)
        self.assertIn("https://v8std.ru/assets/social/std/437/index.png", payload)


if __name__ == "__main__":
    unittest.main()
