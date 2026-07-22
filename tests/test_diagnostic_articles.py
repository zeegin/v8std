import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.diagnostic_articles import (
    SourceEntry,
    SourceFamily,
    content_sha256,
    discover_family,
    extract_local_shell,
    hash_tree,
    immutable_source_url,
    load_catalog,
    normalize_article,
    render_article,
    synchronize_articles,
    verify_checkout_revision,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

BSLLS_FAMILY = SourceFamily(
    family="bslls",
    repository="https://github.com/1c-syntax/bsl-language-server",
    revision="f4616cda8a216789ee40529ed857e614b9e2ea25",
    license="LGPL-3.0-or-later",
    source_root="docs/diagnostics",
)
SOURCE_ENTRY = SourceEntry(
    id="UsingModalWindows",
    source_path="docs/diagnostics/UsingModalWindows.md",
    source_url=(
        "https://github.com/1c-syntax/bsl-language-server/blob/"
        "f4616cda8a216789ee40529ed857e614b9e2ea25/"
        "docs/diagnostics/UsingModalWindows.md"
    ),
    content_sha256="c" * 64,
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

    def test_normalize_article_accepts_upstream_compact_h1(self):
        title, body = normalize_article("#Заголовок без пробела\n\nОписание.\n")

        self.assertEqual(title, "Заголовок без пробела")
        self.assertEqual(body, "Описание.\n")

    def test_normalize_article_removes_trailing_whitespace_from_source(self):
        title, body = normalize_article(
            "# Заголовок  \n\nСтрока с пробелами.  \n\t\n```bsl\nЗначение = 1;\t\n```\n"
        )

        self.assertEqual(title, "Заголовок")
        self.assertEqual(
            body,
            "Строка с пробелами.\n\n```bsl\nЗначение = 1;\n```\n",
        )

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


class DiagnosticArticleRenderingTests(unittest.TestCase):
    def test_verify_checkout_revision_rejects_wrong_sha(self):
        checkout = Path("/tmp/source-checkout")
        with patch("scripts.diagnostic_articles.subprocess.run") as run:
            run.return_value.stdout = "1" * 40 + "\n"

            with self.assertRaisesRegex(ValueError, "checkout revision mismatch"):
                verify_checkout_revision(checkout, "0" * 40)

        run.assert_called_once_with(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_render_article_preserves_metadata_and_marks_imported_body(self):
        rendered = render_article(
            marker="bslls:UsingModalWindows",
            title="Использование модальных окон (UsingModalWindows)",
            metadata=["- Тип: Дефект кода", "- Важность: Важный"],
            body="## Описание диагностики\n\nПолный текст.\n",
            entry=SOURCE_ENTRY,
            family=BSLLS_FAMILY,
            standards_markdown=(
                "- [#std703, п. 1](../../std/703.md#1) — Запрещает модальные вызовы.\n"
            ),
        )

        self.assertIn("###### bslls:UsingModalWindows", rendered)
        self.assertIn("- Тип: Дефект кода", rendered)
        self.assertIn("<!-- diagnostic-source:start", rendered)
        self.assertIn("sha256=" + "c" * 64, rendered)
        self.assertIn("SPDX-License-Identifier: LGPL-3.0-or-later", rendered)
        self.assertIn("## Описание диагностики", rendered)
        self.assertIn("## Соответствие стандартам", rendered)
        self.assertIn("../../std/703.md#1", rendered)
        self.assertIn(SOURCE_ENTRY.source_url, rendered)

    def test_hash_tree_changes_only_when_file_content_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "1.md").write_text("one\n", encoding="utf-8")
            before = hash_tree(root)
            (root / "1.md").write_text("two\n", encoding="utf-8")
            after = hash_tree(root)

        self.assertNotEqual(before, after)

    def test_extract_local_shell_reads_legacy_metadata_and_standard_links(self):
        shell = extract_local_shell(
            """###### bslls:UsingModalWindows

# Использование модальных окон (UsingModalWindows)

- Тип: Дефект кода
- Важность: Важный

###### Стандарт

- [#std703: Ограничение модальных окон](../../std/703.md)

###### Источник

https://example.com/source
"""
        )

        self.assertEqual(shell.marker, "bslls:UsingModalWindows")
        self.assertEqual(shell.metadata, ("- Тип: Дефект кода", "- Важность: Важный"))
        self.assertEqual(
            shell.standards_markdown,
            "- [#std703: Ограничение модальных окон](../../std/703.md)\n",
        )

    def test_load_catalog_rejects_unknown_fields(self):
        payload = {
            "version": 1,
            "families": [
                {
                    "family": "bslls",
                    "repository": BSLLS_FAMILY.repository,
                    "revision": BSLLS_FAMILY.revision,
                    "license": BSLLS_FAMILY.license,
                    "source_root": BSLLS_FAMILY.source_root,
                    "diagnostics": [],
                    "unexpected": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unknown family fields: unexpected"):
                load_catalog(path)

    def test_discover_family_normalizes_and_hashes_source_articles(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            source_dir = checkout / "docs/diagnostics"
            source_dir.mkdir(parents=True)
            (source_dir / "One.md").write_text("# Первая\n\nПолное описание.\n", encoding="utf-8")
            (source_dir / "index.md").write_text("# Индекс\n", encoding="utf-8")

            discovered = discover_family(checkout, BSLLS_FAMILY)

        self.assertEqual(set(discovered), {"One"})
        path, title, body = discovered["One"]
        self.assertEqual(path.as_posix(), "docs/diagnostics/One.md")
        self.assertEqual(title, "Первая")
        self.assertEqual(body, "Полное описание.\n")

    def test_synchronize_articles_writes_deterministic_pages_and_preserves_acc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            bslls = root / "bslls"
            edt = root / "edt"
            for checkout in (bslls, edt):
                checkout.mkdir()

            (bslls / "docs/diagnostics").mkdir(parents=True)
            (bslls / "docs/diagnostics/One.md").write_text(
                "# Первая (One)\n\n## Описание диагностики\n\nПолная статья BSL LS.\n",
                encoding="utf-8",
            )
            (edt / "bundles/example/markdown/ru").mkdir(parents=True)
            (edt / "bundles/example/markdown/ru/Two.md").write_text(
                "# Вторая\n\nПолная статья EDT.\n",
                encoding="utf-8",
            )
            bslls_revision = "1" * 40
            edt_revision = "2" * 40
            families = (
                SourceFamily(
                    "bslls",
                    "https://github.com/example/bslls",
                    bslls_revision,
                    "LGPL-3.0-or-later",
                    "docs/diagnostics",
                ),
                SourceFamily(
                    "v8-code-style",
                    "https://github.com/example/edt",
                    edt_revision,
                    "EPL-2.0",
                    "bundles",
                ),
            )
            (repo / "docs/diagnostics/bslls").mkdir(parents=True)
            (repo / "docs/diagnostics/v8-code-style").mkdir(parents=True)
            (repo / "docs/diagnostics/acc").mkdir(parents=True)
            (repo / "docs/diagnostics/bslls/One.md").write_text(
                "###### bslls:One\n\n# Старая\n\n- Тип: Дефект кода\n",
                encoding="utf-8",
            )
            (repo / "docs/diagnostics/v8-code-style/Two.md").write_text(
                "###### v8cs:Two\n\n# Старая\n\n- Категория: `bsl`\n",
                encoding="utf-8",
            )
            acc_path = repo / "docs/diagnostics/acc/1.md"
            acc_path.write_text("ACC remains unchanged.\n", encoding="utf-8")
            acc_before = acc_path.read_bytes()

            with patch("scripts.diagnostic_articles.verify_checkout_revision") as verify:
                written = synchronize_articles(
                    repo_root=repo,
                    checkouts={"bslls": bslls, "v8-code-style": edt},
                    families=families,
                    write=True,
                )
                drift = synchronize_articles(
                    repo_root=repo,
                    checkouts={"bslls": bslls, "v8-code-style": edt},
                    families=families,
                    write=False,
                )

            self.assertEqual(verify.call_count, 4)

            self.assertEqual(len(written), 3)
            self.assertEqual(drift, [])
            self.assertEqual(acc_path.read_bytes(), acc_before)
            self.assertIn(
                "Полная статья BSL LS.",
                (repo / "docs/diagnostics/bslls/One.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "# Вторая (Two)",
                (repo / "docs/diagnostics/v8-code-style/Two.md").read_text(encoding="utf-8"),
            )
            catalog = load_catalog(repo / "data/diagnostic-sources.json")
            self.assertEqual(catalog.ids("bslls"), {"One"})
            self.assertEqual(catalog.ids("v8-code-style"), {"Two"})


class DiagnosticArticleRepositoryTests(unittest.TestCase):
    def test_offline_integrity_verifier_checks_all_committed_articles_and_proposals(self):
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/check_diagnostic_articles.py"),
                "--root",
                str(REPO_ROOT),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertRegex(
            result.stdout,
            r"diagnostic article integrity clean: families=2, pages=358, proposals=\d+",
        )

    def test_offline_integrity_verifier_rejects_a_tampered_managed_body(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            for name in ("diagnostic-sources.json", "diagnostic-standard-links.json"):
                shutil.copy2(REPO_ROOT / "data" / name, root / "data" / name)
            for family in ("bslls", "v8-code-style"):
                shutil.copytree(
                    REPO_ROOT / "docs/diagnostics" / family,
                    root / "docs/diagnostics" / family,
                )
            page = root / "docs/diagnostics/bslls/UsingModalWindows.md"
            page.write_text(
                page.read_text(encoding="utf-8").replace(
                    "Модальные и всплывающие окна", "Изменённые модальные окна", 1
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts/check_diagnostic_articles.py"),
                    "--root",
                    str(root),
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("content hash mismatch", result.stderr + result.stdout)

    def test_manifest_and_local_catalogs_have_matching_composition(self):
        catalog = load_catalog(REPO_ROOT / "data/diagnostic-sources.json")

        self.assertEqual(catalog.ids("bslls"), self._markdown_ids("bslls"))
        self.assertEqual(
            catalog.ids("v8-code-style"),
            self._markdown_ids("v8-code-style"),
        )

    def test_every_managed_body_is_nonempty(self):
        for family in ("bslls", "v8-code-style"):
            for path in sorted((REPO_ROOT / "docs/diagnostics" / family).glob("*.md")):
                if path.name == "index.md":
                    continue
                content = path.read_text(encoding="utf-8")
                match = re.search(
                    r"<!-- diagnostic-source:start.*?-->\n(?P<body>.*?)"
                    r"<!-- diagnostic-source:end -->",
                    content,
                    re.DOTALL,
                )
                self.assertIsNotNone(match, path)
                self.assertGreater(len(match.group("body").strip()), 20, path)

    @staticmethod
    def _markdown_ids(family: str) -> set[str]:
        return {
            path.stem
            for path in (REPO_ROOT / "docs/diagnostics" / family).glob("*.md")
            if path.name != "index.md"
        }


if __name__ == "__main__":
    unittest.main()
