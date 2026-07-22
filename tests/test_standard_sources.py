import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.standard_sources import load_registry, render_sources, sync_standard_sources


ENGLISH_URL = (
    "https://kb.1ci.com/1C_Enterprise_Platform/Guides/Developer_Guides/"
    "1C_Enterprise_Development_Standards/Code_conventions/"
    "Using_1C_Enterprise_language_structures/Event_log/?language=en"
)
RUSSIAN_URL = "https://its.1c.ru/db/v8std#content:498"
REPO_ROOT = Path(__file__).resolve().parents[1]


class StandardSourceRegistryTests(unittest.TestCase):
    def write_registry(self, root: Path, payload: dict) -> Path:
        path = root / "registry.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_load_registry_accepts_sorted_unique_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_registry(
                Path(temp),
                {
                    "version": 1,
                    "sources": [
                        {"standard": "std498", "english_url": ENGLISH_URL}
                    ],
                },
            )
            self.assertEqual(load_registry(path), {"std498": ENGLISH_URL})

    def test_load_registry_rejects_unknown_fields_duplicates_and_unsorted_ids(self):
        invalid_payloads = [
            {"version": 1, "sources": [], "extra": True},
            {
                "version": 1,
                "sources": [
                    {"standard": "std498", "english_url": ENGLISH_URL},
                    {"standard": "std498", "english_url": ENGLISH_URL + "#copy"},
                ],
            },
            {
                "version": 1,
                "sources": [
                    {"standard": "std499", "english_url": ENGLISH_URL + "#499"},
                    {"standard": "std498", "english_url": ENGLISH_URL},
                ],
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            for index, payload in enumerate(invalid_payloads):
                with self.subTest(index=index):
                    path = self.write_registry(Path(temp), payload)
                    with self.assertRaises(ValueError):
                        load_registry(path)

    def test_load_registry_rejects_noncanonical_english_urls(self):
        invalid_urls = [
            ENGLISH_URL.replace("https://", "http://"),
            ENGLISH_URL.replace("kb.1ci.com", "example.com"),
            "https://kb.1ci.com/1C_Enterprise_Platform/?language=en",
            ENGLISH_URL.replace("?language=en", ""),
        ]
        with tempfile.TemporaryDirectory() as temp:
            for index, url in enumerate(invalid_urls):
                with self.subTest(url=url):
                    path = self.write_registry(
                        Path(temp),
                        {
                            "version": 1,
                            "sources": [
                                {"standard": "std498", "english_url": url}
                            ],
                        },
                    )
                    with self.assertRaises(ValueError):
                        load_registry(path)

    def test_repository_registry_resolves_to_matching_standard_pages(self):
        registry = load_registry(REPO_ROOT / "data/standard-english-sources.json")
        self.assertGreater(len(registry), 0)
        for standard in registry:
            with self.subTest(standard=standard):
                page = REPO_ROOT / "docs/std" / f"{standard[3:]}.md"
                self.assertTrue(page.is_file())
                self.assertIn(
                    f"https://its.1c.ru/db/v8std#content:{standard[3:]}",
                    page.read_text(encoding="utf-8"),
                )


class StandardSourceRenderingTests(unittest.TestCase):
    def test_render_sources_labels_both_language_versions(self):
        self.assertEqual(
            render_sources("std498", RUSSIAN_URL, ENGLISH_URL),
            "###### Источники\n\n"
            f"- [Русская версия — ИТС]({RUSSIAN_URL})\n"
            f"- [English version — 1Ci Knowledge Base]({ENGLISH_URL})\n",
        )

    def test_render_sources_preserves_single_source_format_without_mapping(self):
        self.assertEqual(
            render_sources("std498", RUSSIAN_URL, None),
            f"###### Источник\n\n{RUSSIAN_URL}\n",
        )

    def test_render_sources_rejects_mismatched_its_id(self):
        with self.assertRaises(ValueError):
            render_sources(
                "std498", "https://its.1c.ru/db/v8std#content:499", ENGLISH_URL
            )

    def test_sync_reports_drift_writes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / "std"
            docs.mkdir()
            page = docs / "498.md"
            original = f"# Event log\n\n###### Источник\n\n{RUSSIAN_URL}\n"
            page.write_text(original, encoding="utf-8")
            registry = root / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "sources": [
                            {"standard": "std498", "english_url": ENGLISH_URL}
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(sync_standard_sources(docs, registry, write=False), [page])
            self.assertEqual(page.read_text(encoding="utf-8"), original)
            self.assertEqual(sync_standard_sources(docs, registry, write=True), [page])
            self.assertIn("English version — 1Ci Knowledge Base", page.read_text())
            self.assertEqual(sync_standard_sources(docs, registry, write=False), [])

    def test_sync_rejects_unknown_standard_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / "std"
            docs.mkdir()
            registry = self._registry(root, "std498")
            with self.assertRaises(FileNotFoundError):
                sync_standard_sources(docs, registry, write=True)

    def test_cli_accepts_explicit_check_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / "std"
            docs.mkdir()
            (docs / "498.md").write_text(
                f"# Event log\n\n###### Источник\n\n{RUSSIAN_URL}\n",
                encoding="utf-8",
            )
            registry = self._registry(root, "std498")
            result = subprocess.run(
                [
                    "python3.12",
                    str(REPO_ROOT / "scripts/standard_sources.py"),
                    "--check",
                    "--docs-dir",
                    str(docs),
                    "--registry",
                    str(registry),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("standard sources out of date: 1", result.stdout)

    @staticmethod
    def _registry(root: Path, standard: str) -> Path:
        registry = root / "registry.json"
        registry.write_text(
            json.dumps(
                {
                    "version": 1,
                    "sources": [
                        {"standard": standard, "english_url": ENGLISH_URL}
                    ],
                }
            ),
            encoding="utf-8",
        )
        return registry


if __name__ == "__main__":
    unittest.main()
