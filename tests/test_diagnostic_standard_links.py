import json
import tempfile
import unittest
from pathlib import Path

from scripts.diagnostic_standard_links import (
    LinkReview,
    SourceProposal,
    heading_anchor,
    load_reviews,
    parse_v8std_url,
    validate_review_coverage,
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


if __name__ == "__main__":
    unittest.main()
