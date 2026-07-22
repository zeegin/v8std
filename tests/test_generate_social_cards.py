import importlib.util
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

from jinja2 import DictLoader, Environment


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_social_cards.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_social_cards", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StartTagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)


class MetadataTemplateEscapingTests(unittest.TestCase):
    def find_tag(self, markup: str, tag: str, **selector: str) -> dict[str, str | None]:
        parser = StartTagCollector()
        parser.feed(markup)
        matches = [
            attrs
            for candidate, attrs in parser.tags
            if candidate == tag and all(attrs.get(key) == value for key, value in selector.items())
        ]
        self.assertEqual(len(matches), 1, (tag, selector, matches))
        return matches[0]

    def test_main_template_round_trips_dynamic_attribute_values(self):
        quoted_text = 'Данные "в кавычках" & <детали>'
        quoted_title = 'Заголовок "в кавычках" & <ИмяОбъекта>'
        quoted_url = 'https://example.test/?query="значение"&mode=full'
        base_template = """\
{% block site_meta %}{% endblock %}
{% block htmltitle %}{% endblock %}
{% block analytics %}{% endblock %}
{% block extrahead %}{% endblock %}
"""
        environment = Environment(
            loader=DictLoader(
                {
                    "main.html": (REPO_ROOT / "overrides" / "main.html").read_text(
                        encoding="utf-8"
                    ),
                    "base.html": base_template,
                    "partials/page_meta.html": "",
                    "partials/social_meta.html": "",
                }
            ),
            autoescape=False,
        )
        environment.filters["url"] = lambda value: value

        markup = environment.get_template("main.html").render(
            config=SimpleNamespace(
                site_description="Резервное описание",
                site_author="Резервный автор",
                site_name="Тест",
                extra=SimpleNamespace(alternate=[]),
                theme=SimpleNamespace(favicon="icon.png"),
            ),
            generator=quoted_text,
            lang=SimpleNamespace(t=lambda _: "ru"),
            page=SimpleNamespace(
                canonical_url=quoted_url,
                is_homepage=True,
                meta=SimpleNamespace(description="Описание страницы", author=quoted_text),
                next_page=None,
                previous_page=None,
                title="Заголовок",
                url="",
            ),
            page_meta=SimpleNamespace(description=quoted_text, seo_title=quoted_title),
        )

        self.assertEqual(
            self.find_tag(markup, "meta", name="description")["content"], quoted_text
        )
        self.assertEqual(self.find_tag(markup, "meta", name="author")["content"], quoted_text)
        self.assertEqual(self.find_tag(markup, "link", rel="canonical")["href"], quoted_url)
        self.assertEqual(
            self.find_tag(markup, "meta", name="generator")["content"], quoted_text
        )
        parser = StartTagCollector()
        parser.feed(markup)
        self.assertEqual("".join(parser.title_parts).strip(), quoted_title)

    def test_social_meta_round_trips_dynamic_attribute_values(self):
        title = 'Стандарт "в кавычках" & смысл'
        description = 'Описание "в кавычках" & <детали>'
        page_url = 'https://example.test/page/?query="значение"&mode=full'
        image_url = 'https://example.test/image.png?query="значение"&mode=full'
        site_name = 'Сайт "Стандарты" & практики'
        locale = 'ru_"RU"&test'
        environment = Environment(
            loader=DictLoader(
                {
                    "partials/social_meta.html": (
                        REPO_ROOT / "overrides" / "partials" / "social_meta.html"
                    ).read_text(encoding="utf-8"),
                    "partials/page_meta.html": "",
                }
            ),
            autoescape=False,
        )

        markup = environment.get_template("partials/social_meta.html").render(
            config=SimpleNamespace(site_url="https://example.test", site_name=site_name),
            page_meta=SimpleNamespace(
                description=description,
                image=image_url,
                seo_title=title,
                url=page_url,
            ),
            page_meta_locale=locale,
        )

        expected_properties = {
            "og:site_name": site_name,
            "og:locale": locale,
            "og:title": title,
            "og:description": description,
            "og:url": page_url,
            "og:image": image_url,
            "og:image:alt": title,
        }
        for property_name, expected in expected_properties.items():
            with self.subTest(property=property_name):
                self.assertEqual(
                    self.find_tag(markup, "meta", property=property_name)["content"], expected
                )

        expected_names = {
            "twitter:title": title,
            "twitter:description": description,
            "twitter:url": page_url,
            "twitter:image": image_url,
            "twitter:image:alt": title,
        }
        for name, expected in expected_names.items():
            with self.subTest(name=name):
                self.assertEqual(self.find_tag(markup, "meta", name=name)["content"], expected)


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

    def test_description_limit_counts_decoded_visible_characters(self):
        prefix = "А" * 155
        expected = f"{prefix} Модуль<ИмяОбъекта>"

        self.assertEqual(
            self.module.normalize_description(
                f"{prefix} Модуль&lt;ИмяОбъекта&gt;"
            ),
            expected,
        )

    def test_uniquify_descriptions_preserves_plain_angle_placeholders(self):
        pages = [
            {
                "seo_title": "Первая<Имя>",
                "description": "Модуль<ИмяОбъекта>",
            },
            {
                "seo_title": "Вторая<Имя>",
                "description": "Модуль<ИмяОбъекта>",
            },
        ]

        self.module.uniquify_descriptions(pages)

        self.assertEqual(
            [page["description"] for page in pages],
            [
                "Первая<Имя>. Модуль<ИмяОбъекта>",
                "Вторая<Имя>. Модуль<ИмяОбъекта>",
            ],
        )


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

    def test_diagnostic_provenance_comment_is_not_used_as_description(self):
        page = self.build_page("diagnostics/bslls/CompareWithBoolean.md")

        for key in ("description", "card_description"):
            with self.subTest(key=key):
                self.assertIn("Сравнение выражения с булевой константой", page[key])
                self.assertNotIn("sourceurl=", page[key])
                self.assertNotIn("sourcepath=", page[key])

    def test_markdown_entities_are_decoded_before_html_context_escaping(self):
        page = self.build_page("diagnostics/acc/1383.md")

        for key in ("title", "seo_title", "description", "card_description"):
            with self.subTest(key=key):
                self.assertIn("Модуль<ИмяОбъекта>", page[key])
                self.assertNotIn("&lt;", page[key])


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
