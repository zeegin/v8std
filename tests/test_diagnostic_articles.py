import unittest

from scripts.diagnostic_articles import (
    SourceFamily,
    content_sha256,
    immutable_source_url,
    normalize_article,
)


class DiagnosticArticleCoreTests(unittest.TestCase):
    def test_normalize_article_removes_only_first_h1(self):
        title, body = normalize_article(
            '# Заголовок диагностики\n\nОписание.\n\n## Примеры\n\n```bsl\nСообщить("x");\n```\n'
        )

        self.assertEqual(title, "Заголовок диагностики")
        self.assertEqual(
            body,
            'Описание.\n\n## Примеры\n\n```bsl\nСообщить("x");\n```\n',
        )

    def test_normalize_article_rejects_missing_h1(self):
        with self.assertRaisesRegex(ValueError, "first non-empty line must be H1"):
            normalize_article("## Описание\n")

    def test_immutable_source_url_uses_full_revision(self):
        family = SourceFamily(
            family="bslls",
            repository="https://github.com/1c-syntax/bsl-language-server",
            revision="f4616cda8a216789ee40529ed857e614b9e2ea25",
            license="LGPL-3.0-or-later",
            source_root="docs/diagnostics",
        )

        self.assertEqual(
            immutable_source_url(family, "docs/diagnostics/UsingModalWindows.md"),
            "https://github.com/1c-syntax/bsl-language-server/blob/"
            "f4616cda8a216789ee40529ed857e614b9e2ea25/"
            "docs/diagnostics/UsingModalWindows.md",
        )

    def test_content_hash_is_stable_for_normalized_body(self):
        self.assertEqual(
            content_sha256("Описание.\n"),
            "0c0dec5dbd13824c66a2a7d2b3c39cc501a331c88430b10e9bb829ef4764839b",
        )


if __name__ == "__main__":
    unittest.main()
