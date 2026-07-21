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

    def test_source_proposals_require_exactly_one_covering_review(self):
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


if __name__ == "__main__":
    unittest.main()
