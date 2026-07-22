import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import scripts.generate_diagnostic_standard_links as relationship_generator
from scripts.diagnostic_articles import load_catalog as load_source_catalog
from scripts.diagnostic_standard_links import (
    LinkReview,
    SourceProposal,
    heading_anchor,
    load_reviews,
    parse_v8std_url,
    render_diagnostic_relations,
    render_standard_backlinks,
    rewrite_diagnostic_page,
    rewrite_standard_page,
    validate_review_coverage,
)
from scripts.generate_diagnostic_standard_links import (
    load_all_reviews,
    render_registry_index,
)


IMMUTABLE_EVIDENCE = (
    "https://github.com/1c-syntax/bsl-language-server/blob/"
    "f4616cda8a216789ee40529ed857e614b9e2ea25/"
    "docs/diagnostics/UsingModalWindows.md"
)
REPO_ROOT = Path(__file__).resolve().parents[1]


class V8stdUrlTests(unittest.TestCase):
    def test_parse_supported_v8std_urls(self):
        cases = [
            ("https://its.1c.ru/db/v8std#content:455:hdoc", ("std455", None)),
            (
                "https://its.1c.ru/db/v8std#content:455:hdoc:2.4.3",
                ("std455", "2.4.3"),
            ),
            ("https://its.1c.ru/db/v8std#content:441", ("std441", None)),
            (
                "https://its.1c.ru/db/v8std#content:644:hdoc:3.1@49fb4d81",
                ("std644", "3.1"),
            ),
            ("https://its.1c.ru/db/v8std#content:783:hdoc:_top", ("std783", None)),
            ("https://its.1c.ru/db/v8std/content/455/hdoc", ("std455", None)),
            ("https://its.1c.ru/db/v8std/content/455/hdoc/", ("std455", None)),
            (
                "https://its.1c.ru/db/v8std/content/455/hdoc#2.4.3",
                ("std455", "2.4.3"),
            ),
            (
                "https://its.1c.ru/db/v8std/content/783/hdoc/_top/",
                ("std783", None),
            ),
            (
                "https://its.1c.ru/db/v8std/content/726/hdoc?ysclid=l3g3fkmxsx",
                ("std726", None),
            ),
            ("https://its.1c.ru/db/v8std#contrut:761:hdoc", ("std761", None)),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                self.assertEqual(parse_v8std_url(url), expected)

    def test_unknown_v8std_url_is_an_error(self):
        cases = [
            "https://its.1c.ru/db/v8std?content=455",
            "https://example.com/db/v8std#content:455:hdoc",
            "https://its.1c.ru/db/v8std/content/455/other",
        ]
        for url in cases:
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "unsupported v8std URL"):
                    parse_v8std_url(url)

    def test_heading_anchor_matches_zensical_numeric_slug(self):
        self.assertEqual(heading_anchor("2.4.3"), "243")
        self.assertEqual(heading_anchor("6.4.1"), "641")
        self.assertEqual(heading_anchor("std460"), "std460")
        self.assertEqual(heading_anchor("3.1", occurrence=1), "31_1")
        self.assertEqual(heading_anchor("2а", occurrence=1), "2_1")

    def test_heading_anchor_rejects_prose(self):
        with self.assertRaisesRegex(ValueError, "unsupported clause"):
            heading_anchor("раздел 2")


class LinkReviewTests(unittest.TestCase):
    def test_confirmed_review_requires_clause_anchor_reason_and_evidence(self):
        invalid = {
            "diagnostic": "bslls:UsingModalWindows",
            "standard": "std703",
            "clause": None,
            "anchor": None,
            "evidence": [],
            "reason": "",
            "review": "confirmed",
        }
        with self.assertRaisesRegex(ValueError, "confirmed review requires clause"):
            LinkReview.from_dict(invalid)

    def test_confirmed_review_requires_derived_anchor(self):
        invalid = {
            "diagnostic": "bslls:UsingModalWindows",
            "standard": "std703",
            "clause": "1.2",
            "anchor": "wrong",
            "evidence": [IMMUTABLE_EVIDENCE],
            "reason": "Диагностика проверяет пункт 1.2.",
            "review": "confirmed",
        }
        with self.assertRaisesRegex(ValueError, "anchor must be 12"):
            LinkReview.from_dict(invalid)

    def test_confirmed_review_accepts_rendered_duplicate_heading_anchor(self):
        review = LinkReview.from_dict(
            {
                "diagnostic": "bslls:MissingTemporaryFileDeletion",
                "standard": "std542",
                "clause": "3.1",
                "anchor": "31_1",
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Проверяет удаление созданных временных файлов.",
                "review": "confirmed",
            }
        )
        self.assertEqual(review.anchor, "31_1")

    def test_acc_diagnostic_is_a_supported_review_family(self):
        review = LinkReview.from_dict(
            {
                "diagnostic": "acc:5",
                "standard": "std474",
                "clause": "3.2",
                "anchor": "32",
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "АПК связывает проверку с пунктом 3.2.",
                "review": "confirmed",
            }
        )
        self.assertEqual(review.diagnostic, "acc:5")

    def test_rejected_review_may_have_no_clause(self):
        review = LinkReview.from_dict(
            {
                "diagnostic": "bslls:UsingModalWindows",
                "standard": "std456",
                "clause": None,
                "anchor": None,
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Стандарт не описывает модальные вызовы.",
                "review": "rejected",
                "notes": "Upstream reference is generic.",
            }
        )
        self.assertEqual(review.review, "rejected")

    def test_load_reviews_rejects_unknown_fields_and_duplicate_relationships(self):
        valid = {
            "diagnostic": "bslls:UsingModalWindows",
            "standard": "std703",
            "clause": "1",
            "anchor": "1",
            "evidence": [IMMUTABLE_EVIDENCE],
            "reason": "Пункт 1 запрещает модальные вызовы.",
            "review": "confirmed",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.json"
            path.write_text(
                json.dumps({"version": 1, "reviews": [valid, valid]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate relationship"):
                load_reviews(path)

            path.write_text(
                json.dumps({"version": 1, "reviews": [{**valid, "extra": True}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unknown review fields: extra"):
                load_reviews(path)

    def test_one_diagnostic_standard_pair_may_confirm_multiple_clauses(self):
        base = {
            "diagnostic": "bslls:DeprecatedCurrentDate",
            "standard": "std643",
            "evidence": [IMMUTABLE_EVIDENCE],
            "reason": "Диагностика проверяет контекст использования текущей даты.",
            "review": "confirmed",
        }
        payload = {
            "version": 1,
            "reviews": [
                {**base, "clause": "2.1", "anchor": "21"},
                {**base, "clause": "3.1", "anchor": "31"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            reviews = load_reviews(path)

        self.assertEqual([review.clause for review in reviews], ["2.1", "3.1"])
        proposal = SourceProposal(
            diagnostic="bslls:DeprecatedCurrentDate",
            standard="std643",
            proposed_clause=None,
            source_url=IMMUTABLE_EVIDENCE,
            referenced_url="https://its.1c.ru/db/v8std/content/643/hdoc",
        )
        validate_review_coverage({proposal}, reviews)

    def test_pair_cannot_mix_confirmed_and_rejected_reviews(self):
        base = {
            "diagnostic": "bslls:DeprecatedCurrentDate",
            "standard": "std643",
            "evidence": [IMMUTABLE_EVIDENCE],
            "reason": "Reviewed.",
        }
        payload = {
            "version": 1,
            "reviews": [
                {
                    **base,
                    "clause": None,
                    "anchor": None,
                    "review": "rejected",
                },
                {
                    **base,
                    "clause": "2.1",
                    "anchor": "21",
                    "review": "confirmed",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mixed review decisions"):
                load_reviews(path)

    def test_source_proposals_require_a_covering_review(self):
        proposal = SourceProposal(
            diagnostic="bslls:UsingModalWindows",
            standard="std703",
            proposed_clause=None,
            source_url=IMMUTABLE_EVIDENCE,
            referenced_url="https://its.1c.ru/db/v8std#content:703:hdoc",
        )
        review = LinkReview.from_dict(
            {
                "diagnostic": proposal.diagnostic,
                "standard": proposal.standard,
                "clause": "1",
                "anchor": "1",
                "evidence": [proposal.source_url],
                "reason": "Пункт 1 запрещает модальные вызовы.",
                "review": "confirmed",
            }
        )
        validate_review_coverage({proposal}, (review,))

        with self.assertRaisesRegex(ValueError, "unreviewed source proposal"):
            validate_review_coverage({proposal}, ())


class RelationshipRenderingTests(unittest.TestCase):
    def confirmedReview(self, diagnostic="bslls:UsingModalWindows", standard="std703", clause="1"):
        return LinkReview.from_dict(
            {
                "diagnostic": diagnostic,
                "standard": standard,
                "clause": clause,
                "anchor": heading_anchor(clause),
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Пункт запрещает диагностируемое использование.",
                "review": "confirmed",
            }
        )

    def test_forward_and_reverse_links_are_generated_from_same_record(self):
        review = self.confirmedReview()

        forward = render_diagnostic_relations(
            [review], standard_titles={"std703": "Ограничение модальных окон"}
        )
        reverse = render_standard_backlinks([review])

        self.assertIn("../../std/703.md#1", forward)
        self.assertIn("п. 1", forward)
        self.assertIn(
            "../diagnostics/bslls/UsingModalWindows.md", reverse["std703"]["1"]
        )
        self.assertIn(
            '<div class="diagnostic-links" aria-label="Проверки">',
            reverse["std703"]["1"],
        )
        self.assertIn(
            '<a class="diagnostic-chip" href="../diagnostics/bslls/UsingModalWindows.md">'
            "bslls:UsingModalWindows</a>",
            reverse["std703"]["1"],
        )
        self.assertNotIn("###### Проверки", reverse["std703"]["1"])
        self.assertNotIn("~[#", reverse["std703"]["1"])

    def test_acc_reverse_link_uses_the_acc_directory(self):
        review = self.confirmedReview(
            diagnostic="acc:5", standard="std474", clause="3.2"
        )

        reverse = render_standard_backlinks([review])

        self.assertIn("../diagnostics/acc/5.md", reverse["std474"]["32"])

    def test_rewrite_diagnostic_page_uses_managed_region_and_reason(self):
        source = """###### bslls:UsingModalWindows

# Использование модальных окон

<!-- diagnostic-source:start
-->
Полная статья.
<!-- diagnostic-source:end -->

## Соответствие стандартам

- [старая ссылка](../../std/703.md)

## Источник диагностики

- Источник
"""
        rewritten = rewrite_diagnostic_page(
            source,
            "bslls:UsingModalWindows",
            [self.confirmedReview()],
            {"std703": "Ограничение модальных окон"},
        )

        self.assertIn("<!-- diagnostic-standards:start -->", rewritten)
        self.assertIn("../../std/703.md#1", rewritten)
        self.assertIn("Пункт запрещает диагностируемое использование.", rewritten)
        self.assertNotIn("старая ссылка", rewritten)
        self.assertEqual(rewrite_diagnostic_page(
            rewritten,
            "bslls:UsingModalWindows",
            [self.confirmedReview()],
            {"std703": "Ограничение модальных окон"},
        ), rewritten)

    def test_rewrite_standard_page_places_backlink_at_exact_clause(self):
        source = """###### #std703

# Ограничение модальных окон

###### 1.

Первый пункт.

###### 2.

Второй пункт.

###### Источник

source
"""
        rewritten = rewrite_standard_page(source, "std703", [self.confirmedReview()])

        first_block = rewritten.index("<!-- diagnostic-backlinks:start clause=1 -->")
        second_heading = rewritten.index("###### 2.")
        self.assertLess(first_block, second_heading)
        self.assertIn("../diagnostics/bslls/UsingModalWindows.md", rewritten)
        self.assertEqual(rewrite_standard_page(rewritten, "std703", [self.confirmedReview()]), rewritten)

    def test_numeric_clause_ends_before_a_new_higher_level_section(self):
        source = """###### #std703

# Стандарт

###### 1.

Пункт.

## Новый самостоятельный раздел

Текст раздела.
"""
        rewritten = rewrite_standard_page(source, "std703", [self.confirmedReview()])

        self.assertLess(
            rewritten.index("<!-- diagnostic-backlinks:start clause=1 -->"),
            rewritten.index("## Новый самостоятельный раздел"),
        )

    def test_whole_standard_backlink_is_placed_after_normative_content(self):
        review = self.confirmedReview(
            diagnostic="acc:1354", standard="std762", clause="std762"
        )
        source = """###### #std762

# Локализация запросов

###### 1.

Нормативный текст.

###### Источник

source
"""

        rewritten = rewrite_standard_page(source, "std762", [review])

        self.assertLess(rewritten.index("Нормативный текст."), rewritten.index("acc:1354"))
        self.assertLess(rewritten.index("acc:1354"), rewritten.index("###### Источник"))

    def test_whole_standard_and_last_clause_blocks_share_a_boundary_without_corruption(self):
        whole = self.confirmedReview(
            diagnostic="acc:68", standard="std409", clause="std409"
        )
        exact = self.confirmedReview(
            diagnostic="v8cs:using-form-data-to-value", standard="std409", clause="1"
        )
        source = """###### #std409

# Преобразование данных формы

###### 1.

Нормативный текст.

###### Источник

source
"""

        rewritten = rewrite_standard_page(source, "std409", [whole, exact])

        self.assertEqual(rewritten.count("<!-- diagnostic-backlinks:start"), 2)
        self.assertNotIn("\n!-- diagnostic-backlinks:start", rewritten)
        self.assertEqual(
            rewrite_standard_page(rewritten, "std409", [whole, exact]), rewritten
        )

    def test_rewrite_standard_page_moves_acc_links_into_the_exact_managed_clause(self):
        source = """###### #std703

# Ограничение модальных окон

###### 1.

Текст.

###### Проверки
~[#bslls:UsingModalWindows](../diagnostics/bslls/UsingModalWindows.md)~
~[#acc:17](../diagnostics/acc/17.md)~

###### Источник
source
"""
        acc_review = self.confirmedReview(
            diagnostic="acc:17", standard="std703", clause="1"
        )
        rewritten = rewrite_standard_page(
            source, "std703", [self.confirmedReview(), acc_review]
        )

        self.assertEqual(rewritten.count(">bslls:UsingModalWindows</a>"), 1)
        self.assertEqual(rewritten.count(">acc:17</a>"), 1)
        managed = re.search(
            r"<!-- diagnostic-backlinks:start clause=1 -->(.*?)"
            r"<!-- diagnostic-backlinks:end clause=1 -->",
            rewritten,
            re.DOTALL,
        )
        self.assertIsNotNone(managed)
        self.assertIn(">acc:17</a>", managed.group(1))

    def test_rewrite_standard_page_rejects_unreviewed_legacy_managed_link(self):
        source = """###### #std703

# Ограничение модальных окон

###### Проверки
~[#v8cs:unknown](../diagnostics/v8-code-style/unknown.md)~
"""
        with self.assertRaisesRegex(ValueError, "unreviewed legacy backlink"):
            rewrite_standard_page(source, "std703", [self.confirmedReview()])

    def test_rewrite_standard_page_removes_obsolete_acc_link_not_in_catalog_reviews(self):
        source = """###### #std703

# Ограничение модальных окон

###### 1.

Текст.

###### Проверки
~[#acc:17](../diagnostics/acc/17.md)~
"""

        rewritten = rewrite_standard_page(source, "std703", [self.confirmedReview()])

        self.assertNotIn("#acc:17", rewritten)


class GeneratedRelationshipGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reviews = load_reviews(REPO_ROOT / "data/diagnostic-standard-links.json")

    def test_generator_loads_acc_reviews_from_the_extracted_catalog(self):
        reviews = load_all_reviews(REPO_ROOT)
        acc_reviews = [review for review in reviews if review.diagnostic.startswith("acc:")]

        self.assertEqual(len(acc_reviews), 600)
        self.assertEqual(sum(review.review == "confirmed" for review in acc_reviews), 598)

    def test_standard_clause_parser_is_available(self):
        self.assertIsNotNone(
            getattr(relationship_generator, "load_standard_pages", None),
            "registry generation must parse exact standard clauses",
        )

    def test_registry_index_groups_confirmed_reviews_by_exact_clause(self):
        confirmed = LinkReview.from_dict(
            {
                "diagnostic": "acc:5",
                "standard": "std474",
                "clause": "3.2",
                "anchor": "32",
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Confirmed.",
                "review": "confirmed",
            }
        )
        rejected = LinkReview.from_dict(
            {
                "diagnostic": "acc:6",
                "standard": "std474",
                "clause": None,
                "anchor": None,
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Rejected.",
                "review": "rejected",
            }
        )

        whole_standard = LinkReview.from_dict(
            {
                "diagnostic": "bslls:Example",
                "standard": "std474",
                "clause": "std474",
                "anchor": "std474",
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Confirmed for the whole standard.",
                "review": "confirmed",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            standards = Path(directory)
            (standards / "474.md").write_text(
                "###### #std474\n\n# Имя, синоним, комментарий\n\n"
                "###### 3.2.\nПервое требование пункта. Вторая фраза.\n",
                encoding="utf-8",
            )
            pages = relationship_generator.load_standard_pages(standards)
            rendered = render_registry_index([confirmed, rejected, whole_standard], pages)

        self.assertIn('href="acc/5.md">acc:5</a>', rendered)
        self.assertNotIn("acc:6", rendered)
        self.assertIn("п. 3.2 — Первое требование пункта", rendered)
        self.assertIn("../std/474.md#32", rendered)
        self.assertIn("Стандарт в целом", rendered)
        self.assertLess(rendered.index("п. 3.2"), rendered.index("Стандарт в целом"))
        self.assertIn(
            'data-search="std474 имя, синоним, комментарий acc:5 bslls:example"',
            rendered,
        )

    def test_standard_parser_orders_nested_clauses_and_skips_code_as_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            standards = Path(directory)
            (standards / "640.md").write_text(
                "###### #std640\n\n# Параметры процедур и функций\n\n"
                "###### 6.10.\nДесятый подпункт.\n\n"
                "###### 6.2.\nСекция `#!bsl // Описание`» (англ. `#!bsl // Description`) содержит назначение.\n\n"
                "###### 7.\n```bsl\nМетод();\n```\n",
                encoding="utf-8",
            )
            page = relationship_generator.load_standard_pages(standards)["std640"]

        self.assertEqual([clause.clause for clause in page.clauses], ["6.2", "6.10", "7"])
        self.assertEqual(page.clauses[0].summary, "Секция // Описание")
        self.assertIsNone(page.clauses[2].summary)

    def test_registry_uses_readable_russian_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            standards = Path(directory)
            (standards / "474.md").write_text(
                "###### #std474\n\n# Заголовок\n\n###### 1.\nТребование.\n",
                encoding="utf-8",
            )
            review = LinkReview.from_dict(
                {
                    "diagnostic": "acc:5",
                    "standard": "std474",
                    "clause": "1",
                    "anchor": "1",
                    "evidence": [IMMUTABLE_EVIDENCE],
                    "reason": "Confirmed.",
                    "review": "confirmed",
                }
            )
            rendered = render_registry_index(
                [review], relationship_generator.load_standard_pages(standards)
            )

        self.assertIn("1 проверка · 1 пункт", rendered)

    def test_registry_rejects_confirmed_clause_missing_from_standard(self):
        confirmed = LinkReview.from_dict(
            {
                "diagnostic": "acc:5",
                "standard": "std474",
                "clause": "9",
                "anchor": "9",
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Confirmed.",
                "review": "confirmed",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            standards = Path(directory)
            (standards / "474.md").write_text(
                "###### #std474\n\n# Имя, синоним, комментарий\n\n###### 1.\nТекст.\n",
                encoding="utf-8",
            )
            pages = relationship_generator.load_standard_pages(standards)

        with self.assertRaisesRegex(ValueError, "missing clause std474:9#9"):
            render_registry_index([confirmed], pages)

    def test_family_index_renderer_keeps_metadata_and_uses_only_exact_confirmed_links(self):
        renderer = getattr(relationship_generator, "render_family_index", None)
        self.assertIsNotNone(renderer, "family indexes must be generated with the relationship graph")
        if renderer is None:
            return

        confirmed = LinkReview.from_dict(
            {
                "diagnostic": "bslls:Example",
                "standard": "std437",
                "clause": "2.1",
                "anchor": "21",
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Confirmed.",
                "review": "confirmed",
            }
        )
        rejected = LinkReview.from_dict(
            {
                "diagnostic": "bslls:Example",
                "standard": "std456",
                "clause": None,
                "anchor": None,
                "evidence": [IMMUTABLE_EVIDENCE],
                "reason": "Rejected.",
                "review": "rejected",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "Example.md").write_text(
                "###### bslls:Example\n\n# Example\n\n"
                "- Тип: Дефект кода\n- Важность: Важный\n",
                encoding="utf-8",
            )
            rendered = renderer(
                "bslls",
                [SimpleNamespace(id="Example")],
                [confirmed, rejected],
                {"std437": "Запросы", "std456": "Текст модулей"},
                pages,
            )

        self.assertIn("| Дефект кода | Важный |", rendered)
        self.assertIn("../../std/437.md#21", rendered)
        self.assertNotIn("std456", rendered)

    def test_every_family_index_row_exactly_matches_confirmed_registry_records(self):
        expected_by_diagnostic = {}
        for review in self.reviews:
            if review.review != "confirmed":
                continue
            expected_by_diagnostic.setdefault(review.diagnostic, []).append(review)

        for directory, prefix in (("bslls", "bslls"), ("v8-code-style", "v8cs")):
            index = (
                REPO_ROOT / "docs/diagnostics" / directory / "index.md"
            ).read_text(encoding="utf-8")
            rows = {}
            for line in index.splitlines():
                if not line.startswith("| ["):
                    continue
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                match = re.fullmatch(r"\[([^]]+)\]\([^)]+\.md\)", cells[0])
                self.assertIsNotNone(match, line)
                exact_links = re.findall(
                    r"\(\.\./\.\./std/(\d+)\.md#([^)]+)\)", cells[-1]
                )
                all_standard_links = re.findall(
                    r"\(\.\./\.\./std/[^)]+\)", cells[-1]
                )
                self.assertEqual(len(all_standard_links), len(exact_links), line)
                rows[match.group(1)] = exact_links

            catalog = load_source_catalog(REPO_ROOT / "data/diagnostic-sources.json")
            self.assertEqual(set(rows), catalog.ids(directory), directory)

            for identifier, actual in rows.items():
                diagnostic = f"{prefix}:{identifier}"
                reviews = sorted(
                    expected_by_diagnostic.get(diagnostic, ()),
                    key=lambda item: (item.standard, item.clause or "", item.anchor or ""),
                )
                expected = [(item.standard[3:], item.anchor) for item in reviews]
                self.assertEqual(actual, expected, diagnostic)

    def test_relationship_generator_checks_and_writes_family_index_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").symlink_to(REPO_ROOT / "data", target_is_directory=True)
            (root / "docs/diagnostics").mkdir(parents=True)
            (root / "docs/std").symlink_to(
                REPO_ROOT / "docs/std", target_is_directory=True
            )
            for family in ("bslls", "v8-code-style"):
                shutil.copytree(
                    REPO_ROOT / "docs/diagnostics" / family,
                    root / "docs/diagnostics" / family,
                )
            shutil.copy2(
                REPO_ROOT / "docs/diagnostics/index.md",
                root / "docs/diagnostics/index.md",
            )
            index = root / "docs/diagnostics/bslls/index.md"
            index.write_text(index.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            check_result = relationship_generator.generate(root, write=False)
            write_result = relationship_generator.generate(root, write=True)
            clean_result = relationship_generator.generate(root, write=False)

        self.assertEqual(len(check_result), 5)
        self.assertEqual(check_result[4], 1)
        self.assertEqual(write_result[4], 1)
        self.assertEqual(clean_result[4], 0)

    def diagnosticPath(self, diagnostic):
        family, identifier = diagnostic.split(":", 1)
        directory = "bslls" if family == "bslls" else "v8-code-style"
        return REPO_ROOT / "docs/diagnostics" / directory / f"{identifier}.md"

    def test_every_registry_decision_is_materialized_in_the_forward_graph(self):
        by_diagnostic = {}
        for review in self.reviews:
            by_diagnostic.setdefault(review.diagnostic, []).append(review)
        for diagnostic, reviews in by_diagnostic.items():
            source = self.diagnosticPath(diagnostic).read_text(encoding="utf-8")
            managed = re.search(
                r"<!-- diagnostic-standards:start -->(.*?)<!-- diagnostic-standards:end -->",
                source,
                re.DOTALL,
            )
            self.assertIsNotNone(managed, diagnostic)
            body = managed.group(1)
            for review in reviews:
                local_url = f"../../std/{review.standard[3:]}.md"
                if review.review == "confirmed":
                    local_url += f"#{review.anchor}"
                    self.assertIn(local_url, body, diagnostic)
                    self.assertIn(review.reason, body, diagnostic)
                else:
                    self.assertNotIn(local_url + "#", body, diagnostic)

    def test_every_confirmed_review_has_one_exact_reverse_backlink(self):
        for review in self.reviews:
            if review.review != "confirmed":
                continue
            family, identifier = review.diagnostic.split(":", 1)
            directory = "bslls" if family == "bslls" else "v8-code-style"
            backlink = f"../diagnostics/{directory}/{identifier}.md"
            standard = (REPO_ROOT / "docs/std" / f"{review.standard[3:]}.md").read_text(
                encoding="utf-8"
            )
            blocks = re.findall(
                rf"<!-- diagnostic-backlinks:start clause={re.escape(review.clause)} -->"
                rf"(.*?)"
                rf"<!-- diagnostic-backlinks:end clause={re.escape(review.clause)} -->",
                standard,
                re.DOTALL,
            )
            self.assertTrue(blocks, f"{review.diagnostic} -> {review.standard}/{review.clause}")
            self.assertTrue(any(backlink in block for block in blocks), review.diagnostic)

    def test_no_managed_family_backlink_remains_outside_generated_regions(self):
        pattern = re.compile(r"\[#(?:acc|bslls|v8cs):")
        for path in sorted((REPO_ROOT / "docs/std").glob("*.md")):
            source = path.read_text(encoding="utf-8")
            unmanaged = re.sub(
                r"<!-- diagnostic-backlinks:start clause=[^\n]+ -->.*?"
                r"<!-- diagnostic-backlinks:end clause=[^\n]+ -->",
                "",
                source,
                flags=re.DOTALL,
            )
            self.assertIsNone(pattern.search(unmanaged), path.name)


class BsllsSemanticReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reviews = tuple(
            review
            for review in load_reviews(REPO_ROOT / "data/diagnostic-standard-links.json")
            if review.diagnostic.startswith("bslls:")
        )

    def assertClauses(self, diagnostic, standard, expected):
        actual = {
            review.clause
            for review in self.reviews
            if review.diagnostic == diagnostic
            and review.standard == standard
            and review.review == "confirmed"
        }
        self.assertEqual(actual, set(expected))

    def assertRejected(self, diagnostic, standard):
        matches = [
            review
            for review in self.reviews
            if review.diagnostic == diagnostic and review.standard == standard
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].review, "rejected")

    def test_all_bslls_source_proposals_are_semantically_reviewed(self):
        unreviewed = [
            review.diagnostic + " -> " + review.standard
            for review in self.reviews
            if review.reason == "Unreviewed bootstrap record"
        ]
        self.assertEqual(unreviewed, [])

    def test_known_clause_corrections_and_multi_clause_mapping(self):
        expected = {
            ("bslls:AssignAliasFieldsInQuery", "std437"): {"2", "2а", "2б"},
            ("bslls:CompareWithBoolean", "std441"): {"4"},
            ("bslls:DeprecatedCurrentDate", "std643"): {"2.1", "3.1"},
            ("bslls:FullOuterJoinQuery", "std435"): {"1.1"},
            ("bslls:FunctionNameStartsWithGet", "std647"): {"6.1"},
            ("bslls:MissingTempStorageDeletion", "std487"): {"8.3"},
            ("bslls:NumberOfValuesInStructureConstructor", "std693"): {"1"},
            ("bslls:SelectTopWithoutOrderBy", "std412"): {"1.1"},
            ("bslls:TimeoutsInExternalResources", "std748"): {"1"},
        }
        for (diagnostic, standard), clauses in expected.items():
            with self.subTest(diagnostic=diagnostic, standard=standard):
                self.assertClauses(diagnostic, standard, clauses)

    def test_audit_missing_links_are_resolved_at_normative_clauses(self):
        expected = {
            ("bslls:BeginTransactionBeforeTryCatch", "std783"): {"1.3"},
            ("bslls:CodeBlockBeforeSub", "std455"): {"1.1"},
            ("bslls:CommandModuleExportMethods", "std544"): {"std544"},
            ("bslls:DeprecatedMethodCall", "std453"): {"5.7"},
            ("bslls:GetFormMethod", "std404"): {"1"},
            ("bslls:IncorrectUseLikeInQuery", "std726"): {"1"},
            ("bslls:QueryNestedFieldsByDot", "std654"): {"1.2"},
            ("bslls:RefOveruse", "std654"): {"1.1"},
            ("bslls:SetPermissionsForNewObjects", "std532"): {"2"},
            ("bslls:UsingGoto", "std547"): {"1"},
            ("bslls:UsingModalWindows", "std703"): {"1"},
            ("bslls:UsingSynchronousCalls", "std703"): {"5"},
        }
        for (diagnostic, standard), clauses in expected.items():
            with self.subTest(diagnostic=diagnostic, standard=standard):
                self.assertClauses(diagnostic, standard, clauses)

    def test_semantically_broad_or_stale_source_references_are_rejected(self):
        rejected = {
            ("bslls:DisableSafeMode", "std485"),
            ("bslls:DisableSafeMode", "std678"),
            ("bslls:DisableSafeMode", "std770"),
            ("bslls:ExternalAppStarting", "std669"),
            ("bslls:FieldsFromJoinsWithoutIsNull", "std412"),
            ("bslls:FileSystemAccess", "std774"),
            ("bslls:IncorrectUseOfStrTemplate", "std763"),
            ("bslls:MultilingualStringHasAllDeclaredLanguages", "std763"),
            ("bslls:MultilingualStringUsingWithTemplate", "std763"),
            ("bslls:ReservedParameterNames", "std454"),
            ("bslls:ReservedParameterNames", "std640"),
            ("bslls:UnsafeFindByCode", "std456"),
            ("bslls:UsingLikeInQuery", "std726"),
            ("bslls:VirtualTableCallWithoutParameters", "std733"),
        }
        for diagnostic, standard in rejected:
            with self.subTest(diagnostic=diagnostic, standard=standard):
                self.assertRejected(diagnostic, standard)

    def test_std456_is_reviewed_individually_not_bulk_confirmed(self):
        confirmed = {
            review.diagnostic: review.clause
            for review in self.reviews
            if review.standard == "std456" and review.review == "confirmed"
        }
        self.assertEqual(
            confirmed,
            {
                "bslls:CommentedCode": "3",
                "bslls:ExcessiveAutoTestCheck": "3",
                "bslls:InvalidCharacterInFile": "1.2",
                "bslls:LineLength": "6",
                "bslls:OneStatementPerLine": "4",
                "bslls:SpaceAtStartComment": "7.3",
                "bslls:UnusedLocalMethod": "2",
                "bslls:YoLetterUsage": "1.1",
            },
        )


class V8CodeStyleSemanticReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reviews = tuple(
            review
            for review in load_reviews(REPO_ROOT / "data/diagnostic-standard-links.json")
            if review.diagnostic.startswith("v8cs:")
        )

    def assertClauses(self, diagnostic, standard, expected):
        actual = {
            review.clause
            for review in self.reviews
            if review.diagnostic == diagnostic
            and review.standard == standard
            and review.review == "confirmed"
        }
        self.assertEqual(actual, set(expected))

    def assertRejected(self, diagnostic, standard):
        matches = [
            review
            for review in self.reviews
            if review.diagnostic == diagnostic and review.standard == standard
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].review, "rejected")

    def test_all_v8_code_style_source_proposals_are_semantically_reviewed(self):
        unreviewed = [
            review.diagnostic + " -> " + review.standard
            for review in self.reviews
            if review.reason == "Unreviewed bootstrap record"
        ]
        self.assertEqual(unreviewed, [])

    def test_known_clause_corrections(self):
        expected = {
            ("v8cs:bsl-canonical-pragma", "std441"): {"1"},
            ("v8cs:common-module-name-cached", "std469"): {"3.2.3"},
            ("v8cs:common-module-name-client-cached", "std469"): {"3.2.3"},
            ("v8cs:common-module-name-server-call-cached", "std469"): {"3.2.3"},
            ("v8cs:data-composition-variant-name-default", "std674"): {"4"},
            ("v8cs:db-object-anyref-type", "std728"): {"2.1"},
            ("v8cs:db-object-ref-non-ref-type", "std728"): {"1.1"},
            ("v8cs:empty-except-statement", "std499"): {"3.2"},
            ("v8cs:md-standard-attribute-synonym-empty", "std474"): {"1.5"},
            ("v8cs:md-list-object-presentation", "std468"): {"4"},
            ("v8cs:module-attachable-event-handler-name", "std492"): {"1"},
            ("v8cs:public-method-caching", "std644"): {"3.6"},
            ("v8cs:ql-temp-table-index", "std777"): {"3"},
            ("v8cs:secure-password-storage", "std740"): {"3.3"},
            ("v8cs:structure-constructor-too-many-keys", "std640"): {"6.2"},
            ("v8cs:subsystem-synonym-too-long", "std712"): {"2.1"},
        }
        for (diagnostic, standard), clauses in expected.items():
            with self.subTest(diagnostic=diagnostic, standard=standard):
                self.assertClauses(diagnostic, standard, clauses)

    def test_transaction_links_use_current_transaction_standard(self):
        for name in ("begin-transaction", "commit-transaction", "lock-out-of-try", "rollback-transaction"):
            diagnostic = "v8cs:" + name
            with self.subTest(diagnostic=diagnostic):
                self.assertRejected(diagnostic, "std499")
                self.assertClauses(diagnostic, "std783", {"1.3"})

    def test_semantically_broad_stale_or_indirect_references_are_rejected(self):
        rejected = {
            ("v8cs:common-module-missing-api", "std455"),
            ("v8cs:event-handler-boolean-param", "std400"),
            ("v8cs:export-method-in-command-form-module", "std404"),
            ("v8cs:extension-md-object-prefix", "std469"),
            ("v8cs:module-accessibility-at-client", "std746"),
            ("v8cs:ql-constants-in-binary-operation", "std658"),
            ("v8cs:right-all-functions-mode", "std488"),
            ("v8cs:using-isinrole", "std689"),
        }
        for diagnostic, standard in rejected:
            with self.subTest(diagnostic=diagnostic, standard=standard):
                self.assertRejected(diagnostic, standard)

    def test_form_list_checks_point_to_the_reorganized_normative_clause(self):
        for name in (
            "form-list-field-ref-not-added",
            "form-list-ref-use-always-flag-disabled",
            "form-list-ref-user-visibility-enabled",
        ):
            with self.subTest(diagnostic=name):
                self.assertClauses("v8cs:" + name, "std702", {"1"})

    def test_standard_role_checks_point_to_specific_role_clauses(self):
        expected = {
            "right-active-users": "3.1",
            "right-administration": "3.1",
            "right-configuration-extensions-administration": "3.1",
            "right-data-administration": "3.1",
            "right-exclusive-mode": "2.1",
            "right-interactive-open-external-data-processors": "2.3",
            "right-interactive-open-external-reports": "2.3",
            "right-output-to-printer-file-clipboard": "3.2",
            "right-save-user-data": "3.12",
            "right-start-automation": "3.3",
            "right-start-external-connection": "3.5",
            "right-start-thick-client": "3.6",
            "right-start-thin-client": "3.7",
            "right-start-web-client": "3.4",
            "right-update-database-configuration": "3.9",
            "right-view-event-log": "3.10",
        }
        for name, clause in expected.items():
            with self.subTest(diagnostic=name):
                self.assertClauses("v8cs:" + name, "std488", {clause})
        self.assertClauses("v8cs:right-delete", "std488", {"5"})

    def test_locally_proven_missing_links_are_registered(self):
        expected = {
            ("v8cs:common-module-name-client", "std469"): {"2.3"},
            ("v8cs:common-module-name-client-server", "std469"): {"2.4"},
            ("v8cs:common-module-name-global", "std469"): {"3.2.1"},
            ("v8cs:configuration-data-lock-mode", "std460"): {"std460"},
            ("v8cs:mdo-name-length", "std474"): {"2.3"},
            ("v8cs:ql-join-to-sub-query", "std655"): {"1.1"},
            ("v8cs:right-interactive-delete", "std488"): {"5"},
            ("v8cs:right-interactive-delete-predefined-data", "std488"): {"5"},
            ("v8cs:right-interactive-set-deletion-mark-predefined-data", "std488"): {"5"},
            ("v8cs:right-interactive-clear-deletion-mark-predefined-data", "std488"): {"5"},
            ("v8cs:right-interactive-delete-marked-predefined-data", "std488"): {"5"},
            ("v8cs:structure-key-modification", "std693"): {"4.1"},
            ("v8cs:structure-constructor-too-many-keys", "std693"): {"1"},
        }
        for (diagnostic, standard), clauses in expected.items():
            with self.subTest(diagnostic=diagnostic, standard=standard):
                self.assertClauses(diagnostic, standard, clauses)


if __name__ == "__main__":
    unittest.main()
