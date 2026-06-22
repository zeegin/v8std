import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from v8std_search_features import (  # noqa: E402
    canonical_search_terms,
    code_lookup_variants,
    generated_aliases_for_page,
    split_identifier_tokens,
)


class V8StdSearchFeaturesTests(unittest.TestCase):
    def test_normalizes_standard_code_variants_and_keyboard_layout(self):
        self.assertIn("std437", code_lookup_variants("Std 437"))
        self.assertIn("std437", code_lookup_variants("#437"))
        self.assertIn("std437", code_lookup_variants("ыев437"))

    def test_normalizes_acc_code_variants_and_keyboard_layout(self):
        self.assertIn("acc:361", code_lookup_variants("АПК 361"))
        self.assertIn("acc:361", code_lookup_variants("acc361"))
        self.assertIn("acc:361", code_lookup_variants("фсс361"))

    def test_splits_identifier_styles_to_common_tokens(self):
        expected = {"query", "nested", "fields", "by", "dot"}

        self.assertTrue(expected.issubset(split_identifier_tokens("QueryNestedFieldsByDot")))
        self.assertTrue(expected.issubset(split_identifier_tokens("query-nested-fields-by-dot")))
        self.assertTrue(expected.issubset(split_identifier_tokens("query_nested_fields_by_dot")))

    def test_canonical_terms_cover_camel_case_and_ru_endings(self):
        self.assertTrue({"клиент", "сервер"}.issubset(canonical_search_terms("КлиентСервер")))
        self.assertIn("видимост", canonical_search_terms("видимость элементов"))
        self.assertIn("видимост", canonical_search_terms("настройка видимости"))
        self.assertIn("рол", canonical_search_terms("по ролям"))
        self.assertIn("рол", canonical_search_terms("много ролей"))

    def test_generates_aliases_from_page_fields_without_manual_rules(self):
        aliases = generated_aliases_for_page(
            {
                "id": "bslls:QueryNestedFieldsByDot",
                "type": "diagnostic",
                "title": "Обращение к вложенным полям запроса через точку (QueryNestedFieldsByDot)",
                "url": "https://v8std.ru/diagnostics/bslls/QueryNestedFieldsByDot/",
                "markdown_url": "https://v8std.ru/diagnostics/bslls/QueryNestedFieldsByDot.md",
                "source_path": "diagnostics/bslls/QueryNestedFieldsByDot.md",
                "body_markdown": "# Обращение к вложенным полям запроса через точку\n\n## Стандарт",
            }
        )

        self.assertIn("QueryNestedFieldsByDot", aliases)
        self.assertIn("query nested fields by dot", aliases)
        self.assertIn("query-nested-fields-by-dot", aliases)
        self.assertIn("Обращение к вложенным полям запроса через точку", aliases)

    def test_generated_aliases_skip_generic_and_numeric_headings(self):
        aliases = generated_aliases_for_page(
            {
                "id": "std791",
                "type": "standard",
                "title": "Дополнительные индексы #std791",
                "url": "https://v8std.ru/std/791/",
                "markdown_url": "https://v8std.ru/std/791.md",
                "source_path": "std/791.md",
                "body_markdown": "# Дополнительные индексы\n\n#### 1.\n\n#### Источник\n",
            }
        )

        self.assertIn("Дополнительные индексы", aliases)
        self.assertNotIn("1", aliases)
        self.assertNotIn("1.", aliases)
        self.assertNotIn("791", aliases)
        self.assertNotIn("Источник", aliases)

    def test_generated_aliases_skip_section_headings(self):
        aliases = generated_aliases_for_page(
            {
                "id": "patterns:gof:strategy",
                "type": "pattern",
                "title": "Strategy / Стратегия",
                "url": "https://v8std.ru/patterns/gof/strategy/",
                "markdown_url": "https://v8std.ru/patterns/gof/strategy.md",
                "source_path": "patterns/gof/strategy.md",
                "body_markdown": (
                    "# Strategy / Стратегия\n\n"
                    "## Применение\n\n"
                    "## Когда полезен\n\n"
                    "## Пример на 1С\n"
                ),
            }
        )

        self.assertIn("Strategy / Стратегия", aliases)
        self.assertNotIn("Применение", aliases)
        self.assertNotIn("Когда полезен", aliases)
        self.assertNotIn("Пример на 1С", aliases)

    def test_generated_acc_aliases_do_not_include_bare_number(self):
        aliases = generated_aliases_for_page(
            {
                "id": "acc:443",
                "type": "diagnostic",
                "title": (
                    "Ошибка выполнения проверки: не удалось получить назначение "
                    "ролей пользователей. АПК:443"
                ),
                "url": "https://v8std.ru/diagnostics/acc/443/",
                "markdown_url": "https://v8std.ru/diagnostics/acc/443.md",
                "source_path": "diagnostics/acc/443.md",
                "body_markdown": "# Ошибка выполнения проверки (ACC 443)\n",
            }
        )

        self.assertIn("acc 443", aliases)
        self.assertIn("апк 443", aliases)
        self.assertNotIn("443", aliases)


if __name__ == "__main__":
    unittest.main()
