import json
import tempfile
import unittest
from pathlib import Path

from scripts.acc_diagnostics import (
    build_link_reviews,
    extract_catalog,
    generate,
    load_catalog,
    main,
    merge_site_metadata,
    render_index,
    render_page,
    validate_review_targets,
)


TEMPLATE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Data>
  <CatalogObject.Требования>
    <Ref>requirement-1</Ref>
    <СсылкаНаСтандарт>https://its.1c.ru/db/v8std#content:474:hdoc</СсылкаНаСтандарт>
  </CatalogObject.Требования>
  <CatalogObject.ОбнаруживаемыеОшибки>
    <Ref>error-5</Ref>
    <IsFolder>false</IsFolder>
    <DeletionMark>false</DeletionMark>
    <Code>5</Code>
    <Description>Комментарий должен начинаться с прописной буквы.</Description>
    <Критичность>Совместимо</Критичность>
    <Рекомендация>Исправьте комментарий.</Рекомендация>
    <ПрогнозируемоеВремяИсправления>10</ПрогнозируемоеВремяИсправления>
    <Требования>
      <Row>
        <СсылкаНаСтандарт>https://its.1c.ru/db/v8std#content:474:hdoc:3.2</СсылкаНаСтандарт>
        <Требование>requirement-1</Требование>
      </Row>
    </Требования>
  </CatalogObject.ОбнаруживаемыеОшибки>
  <CatalogObject.ОбнаруживаемыеОшибки>
    <Ref>error-251</Ref>
    <IsFolder>false</IsFolder>
    <DeletionMark>false</DeletionMark>
    <Code>251</Code>
    <Description>Основная роль не установлена.</Description>
    <Критичность>Обязательно</Критичность>
    <Рекомендация />
    <ПрогнозируемоеВремяИсправления>0</ПрогнозируемоеВремяИсправления>
    <Требования>
      <Row>
        <СсылкаНаСтандарт>https://its.1c.ru/db/v8std#content:488:hdoc2.4</СсылкаНаСтандарт>
        <Требование>requirement-1</Требование>
      </Row>
    </Требования>
  </CatalogObject.ОбнаруживаемыеОшибки>
  <CatalogObject.ОбнаруживаемыеОшибки>
    <Ref>folder</Ref>
    <IsFolder>true</IsFolder>
    <DeletionMark>false</DeletionMark>
    <Code>99</Code>
    <Description>Папка</Description>
  </CatalogObject.ОбнаруживаемыеОшибки>
  <CatalogObject.ОбнаруживаемыеОшибки>
    <Ref>generic</Ref>
    <IsFolder>false</IsFolder>
    <DeletionMark>false</DeletionMark>
    <Code>АПК_Аудит</Code>
    <Description>Служебная ошибка аудита</Description>
  </CatalogObject.ОбнаруживаемыеОшибки>
</Data>
"""


class AccCatalogExtractionTests(unittest.TestCase):
    def test_extracts_only_active_numeric_checks_and_exact_standard_clauses(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Template.bin"
            source.write_text(TEMPLATE_XML, encoding="utf-8")

            catalog = extract_catalog(source, product_version="1.2.9.80")

        self.assertEqual([item["code"] for item in catalog["diagnostics"]], ["5", "251"])
        check = catalog["diagnostics"][0]
        self.assertEqual(check["description"], "Комментарий должен начинаться с прописной буквы.")
        self.assertNotIn("title", check)
        self.assertEqual(check["severity"], "Совместимо")
        self.assertEqual(check["recommendation"], "Исправьте комментарий.")
        self.assertEqual(check["estimated_fix_minutes"], 10)
        self.assertEqual(
            check["standards"],
            [
                {
                    "standard": "std474",
                    "clause": "3.2",
                    "source_url": "https://its.1c.ru/db/v8std#content:474:hdoc:3.2",
                }
            ],
        )
        self.assertRegex(catalog["source"]["sha256"], r"^[0-9a-f]{64}$")

    def test_repairs_the_known_missing_separator_in_acc_251_source_url(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Template.bin"
            source.write_text(TEMPLATE_XML, encoding="utf-8")
            catalog = extract_catalog(source, product_version="1.2.9.80")

        check = catalog["diagnostics"][1]
        self.assertEqual(check["standards"][0]["standard"], "std488")
        self.assertEqual(check["standards"][0]["clause"], "2.4")
        self.assertEqual(
            check["standards"][0]["source_url"],
            "https://its.1c.ru/db/v8std#content:488:hdoc2.4",
        )

    def test_load_catalog_rejects_duplicate_codes(self):
        payload = {
            "version": 1,
            "source": {
                "product_version": "1.2.9.80",
                "sha256": "a" * 64,
            },
            "diagnostics": [
                {"code": "5", "description": "A", "severity": "Обязательно", "standards": []},
                {"code": "5", "description": "B", "severity": "Обязательно", "standards": []},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate ACC code: 5"):
                load_catalog(path)

    def test_load_catalog_requires_a_non_empty_description_for_each_code(self):
        payload = {
            "version": 1,
            "source": {"product_version": "1.2.9.80", "sha256": "a" * 64},
            "diagnostics": [
                {"code": "5", "description": "", "severity": "Обязательно", "standards": []},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ACC diagnostic 5 requires a non-empty description"):
                load_catalog(path)

    def test_extract_cli_writes_a_reproducible_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Template.bin"
            source.write_text(TEMPLATE_XML, encoding="utf-8")
            site = root / "acc"
            site.mkdir()
            output = root / "acc-diagnostics.json"

            exit_code = main(
                [
                    "extract",
                    str(source),
                    "--product-version",
                    "1.2.9.80",
                    "--site-acc-directory",
                    str(site),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(load_catalog(output)["diagnostics"]), 2)


class AccRenderingTests(unittest.TestCase):
    def test_review_and_page_use_the_current_exact_local_clause(self):
        diagnostic = {
            "code": "5",
            "description": "Комментарий должен начинаться с прописной буквы.",
            "severity": "Совместимо",
            "recommendation": "Исправьте комментарий.",
            "estimated_fix_minutes": 10,
            "standards": [
                {
                    "standard": "std474",
                    "clause": "3.2",
                    "source_url": "https://its.1c.ru/db/v8std#content:474:hdoc:3.2",
                }
            ],
            "external_sources": [],
            "edt_codes": [],
        }
        reviews = build_link_reviews(
            {"version": 1, "source": {"product_version": "1.2.9.80", "sha256": "a" * 64}, "diagnostics": [diagnostic]},
            overrides=(),
        )

        page = render_page(
            diagnostic,
            reviews,
            standard_titles={"std474": "Имя, синоним, комментарий"},
            product_version="1.2.9.80",
            source_sha256="a" * 64,
        )

        self.assertIn("Критичность АПК: `Совместимо`", page)
        self.assertIn("Прогнозируемое время исправления: `10 мин.`", page)
        self.assertIn("../../std/474.md#32", page)
        self.assertIn("#std474, п. 3.2", page)
        self.assertIn("Исправьте комментарий.", page)
        self.assertIn("АПК 1.2.9.80", page)
        self.assertIn("## Описание диагностики\n\nКомментарий должен начинаться с прописной буквы.", page)
        self.assertLess(page.index("## Описание диагностики"), page.index("## Рекомендация АПК"))

    def test_zero_fix_time_is_treated_as_unspecified_not_zero_minutes(self):
        diagnostic = {
            "code": "1",
            "description": "Проверка",
            "severity": "Совместимо",
            "recommendation": "",
            "estimated_fix_minutes": 0,
            "standards": [],
            "external_sources": [],
            "edt_codes": [],
        }

        page = render_page(
            diagnostic,
            (),
            standard_titles={},
            product_version="1.2.9.80",
            source_sha256="a" * 64,
        )

        self.assertNotIn("Прогнозируемое время исправления", page)
        self.assertIn("## Описание диагностики\n\nПроверка", page)
        self.assertNotIn("## Рекомендация АПК", page)

    def test_override_can_remap_or_reject_a_stale_source_clause(self):
        catalog = {
            "version": 1,
            "source": {"product_version": "1.2.9.80", "sha256": "a" * 64},
            "diagnostics": [
                {
                    "code": "70",
                    "description": "Полное соединение",
                    "severity": "Рекомендация",
                    "standards": [
                        {
                            "standard": "std435",
                            "clause": "1",
                            "source_url": "https://its.1c.ru/db/v8std#content:435:hdoc:1",
                        },
                        {
                            "standard": "std499",
                            "clause": "3.6",
                            "source_url": "https://its.1c.ru/db/v8std#content:499:hdoc:3.6",
                        },
                    ],
                }
            ],
        }
        overrides = (
            {
                "code": "70",
                "standard": "std435",
                "source_clause": "1",
                "review": "confirmed",
                "clause": "1.1",
                "reason": "В текущей редакции это пункт 1.1.",
            },
            {
                "code": "70",
                "standard": "std499",
                "source_clause": "3.6",
                "review": "rejected",
                "clause": None,
                "reason": "Пункт отсутствует и не описывает проверку.",
            },
        )

        reviews = build_link_reviews(catalog, overrides)

        self.assertEqual([(item.standard, item.clause, item.review) for item in reviews], [("std435", "1.1", "confirmed"), ("std499", None, "rejected")])

    def test_site_metadata_merge_preserves_issue_source_but_excludes_acc_index(self):
        catalog = {
            "version": 1,
            "source": {"product_version": "1.2.9.80", "sha256": "a" * 64},
            "diagnostics": [
                {
                    "code": "5",
                    "description": "Проверка",
                    "severity": "Совместимо",
                    "recommendation": "",
                    "estimated_fix_minutes": 0,
                    "standards": [],
                    "edt_codes": [],
                    "external_sources": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            acc = root / "docs/diagnostics/acc"
            acc.mkdir(parents=True)
            (acc / "5.md").write_text(
                """###### acc:5

# Проверка (ACC 5)

###### Источник

- [acc_index.md](https://github.com/example/acc_index.md)
- [Описание проверки (issue)](https://github.com/example/issues/5)
""",
                encoding="utf-8",
            )
            (acc / "index.md").write_text(
                "| Диагностика | Код EDT | Стандарт |\n"
                "|---|---|---|\n"
                "| [АПК:5](5.md) | `comment-capital-letter` | — |\n",
                encoding="utf-8",
            )

            merged = merge_site_metadata(catalog, acc)

        check = merged["diagnostics"][0]
        self.assertEqual(check["edt_codes"], ["comment-capital-letter"])
        self.assertEqual(
            check["external_sources"],
            [
                {"label": "Описание проверки (issue)", "url": "https://github.com/example/issues/5"},
            ],
        )

    def test_page_never_renders_acc_index_as_an_external_source(self):
        diagnostic = {
            "code": "5",
            "description": "Проверка",
            "severity": "Совместимо",
            "recommendation": "",
            "estimated_fix_minutes": 0,
            "standards": [],
            "edt_codes": [],
            "external_sources": [
                {
                    "label": "acc_index.md",
                    "url": "https://github.com/1C-Company/v8-code-style/blob/master/docs/checks/acc_index.md",
                },
                {
                    "label": "Описание проверки (issue)",
                    "url": "https://github.com/1C-Company/v8-code-style/issues/114",
                },
            ],
        }

        page = render_page(
            diagnostic,
            (),
            standard_titles={},
            product_version="1.2.9.80",
            source_sha256="a" * 64,
        )

        self.assertNotIn("acc_index.md", page)
        self.assertIn("Описание проверки (issue)", page)

    def test_review_target_validation_requires_a_real_current_clause(self):
        catalog = {
            "version": 1,
            "source": {"product_version": "1.2.9.80", "sha256": "a" * 64},
            "diagnostics": [
                {
                    "code": "70",
                    "description": "Проверка",
                    "severity": "Рекомендация",
                    "standards": [
                        {
                            "standard": "std435",
                            "clause": "1",
                            "source_url": "https://its.1c.ru/db/v8std#content:435:hdoc:1",
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            standards = Path(directory)
            (standards / "435.md").write_text(
                "###### #std435\n\n# Полное соединение\n\n###### 1.1.\n\nТекст.\n",
                encoding="utf-8",
            )
            stale = build_link_reviews(catalog, overrides=())
            with self.assertRaisesRegex(ValueError, r"acc:70 -> std435 / 1"):
                validate_review_targets(stale, standards)

            corrected = build_link_reviews(
                catalog,
                overrides=(
                    {
                        "code": "70",
                        "standard": "std435",
                        "source_clause": "1",
                        "review": "confirmed",
                        "clause": "1.1",
                        "reason": "Текущий пункт.",
                    },
                ),
            )
            validate_review_targets(corrected, standards)

    def test_index_is_rendered_from_the_same_catalog_and_exact_reviews(self):
        diagnostic = {
            "code": "5",
            "description": "Комментарий",
            "severity": "Совместимо",
            "standards": [
                {
                    "standard": "std474",
                    "clause": "3.2",
                    "source_url": "https://its.1c.ru/db/v8std#content:474:hdoc:3.2",
                }
            ],
            "edt_codes": ["comment-capital-letter"],
        }
        catalog = {
            "version": 1,
            "source": {"product_version": "1.2.9.80", "sha256": "a" * 64},
            "diagnostics": [diagnostic],
        }
        reviews = build_link_reviews(catalog, overrides=())

        index = render_index(catalog, reviews, {"std474": "Имя, синоним, комментарий"})

        self.assertIn("АПК 1.2.9.80", index)
        self.assertIn("[АПК:5](5.md)", index)
        self.assertIn("`comment-capital-letter`", index)
        self.assertIn("../../std/474.md#32", index)

    def test_generate_reports_missing_and_stale_pages_without_mutating_in_check_mode(self):
        catalog = {
            "version": 1,
            "source": {
                "product_version": "1.2.9.80",
                "sha256": "4302557c70d119c8945cf42372693b93c0495f850ec37e60596402aa1884de4f",
            },
            "diagnostics": [
                {
                    "code": "5",
                    "description": "Проверка",
                    "severity": "Совместимо",
                    "recommendation": "",
                    "estimated_fix_minutes": 0,
                    "standards": [],
                    "edt_codes": [],
                    "external_sources": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "docs/diagnostics/acc").mkdir(parents=True)
            (root / "docs/std").mkdir(parents=True)
            (root / "data/acc-diagnostics.json").write_text(json.dumps(catalog), encoding="utf-8")
            (root / "data/acc-standard-link-overrides.json").write_text(
                json.dumps({"version": 1, "overrides": []}), encoding="utf-8"
            )
            stale = root / "docs/diagnostics/acc/456.md"
            stale.write_text("historical", encoding="utf-8")

            result = generate(root, write=False)

            self.assertEqual(result, (1, 1, 1, True))
            self.assertFalse((root / "docs/diagnostics/acc/5.md").exists())
            self.assertTrue(stale.exists())

    def test_generate_rejects_an_unpinned_acc_product_version_before_writing(self):
        catalog = {
            "version": 1,
            "source": {"product_version": "1.2.9.81", "sha256": "a" * 64},
            "diagnostics": [
                {
                    "code": "5",
                    "description": "Проверка",
                    "severity": "Совместимо",
                    "recommendation": "",
                    "estimated_fix_minutes": 0,
                    "standards": [],
                    "edt_codes": [],
                    "external_sources": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "docs/diagnostics/acc").mkdir(parents=True)
            (root / "docs/std").mkdir(parents=True)
            (root / "data/acc-diagnostics.json").write_text(json.dumps(catalog), encoding="utf-8")
            (root / "data/acc-standard-link-overrides.json").write_text(
                json.dumps({"version": 1, "overrides": []}), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "ACC catalog product version must be 1.2.9.80"):
                generate(root, write=True)

            self.assertFalse((root / "docs/diagnostics/acc/5.md").exists())

    def test_generate_rejects_an_unpinned_acc_sha_before_writing(self):
        catalog = {
            "version": 1,
            "source": {"product_version": "1.2.9.80", "sha256": "a" * 64},
            "diagnostics": [
                {
                    "code": "5",
                    "description": "Проверка",
                    "severity": "Совместимо",
                    "recommendation": "",
                    "estimated_fix_minutes": 0,
                    "standards": [],
                    "edt_codes": [],
                    "external_sources": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "docs/diagnostics/acc").mkdir(parents=True)
            (root / "docs/std").mkdir(parents=True)
            (root / "data/acc-diagnostics.json").write_text(json.dumps(catalog), encoding="utf-8")
            (root / "data/acc-standard-link-overrides.json").write_text(
                json.dumps({"version": 1, "overrides": []}), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "ACC catalog source SHA-256 must be 4302557c70d119c8945cf42372693b93c0495f850ec37e60596402aa1884de4f"):
                generate(root, write=True)

            self.assertFalse((root / "docs/diagnostics/acc/5.md").exists())


if __name__ == "__main__":
    unittest.main()
