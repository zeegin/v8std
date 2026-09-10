"""Presentation changes link nodes, never retrieval input or code literals."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from tests import mcp_snapshot_fixtures as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PUBLIC = "https://v8std.ru/"
LOCAL = "http://localhost:8080/kb/"
PATHS = {"std437": {"site_path": "std/437/", "markdown_path": "std/437.md"},
         "third": {"site_path": "THIRD_PARTY_DIAGNOSTIC_ARTICLES/",
                   "markdown_path": "THIRD_PARTY_DIAGNOSTIC_ARTICLES.md"}}


class PresentationTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("v8std_mcp_presentation"))
        return importlib.import_module("v8std_mcp_presentation")

    def present(self, value):
        return self.module().present_result(value, canonical_site_url=PUBLIC,
                                            site_url=LOCAL, page_paths=PATHS)

    def test_link_nodes_and_nested_urls_preserve_literals_and_provenance(self):
        body = ('`https://v8std.ru/std/437/`\n'
                '[link](https://v8std.ru/std/437/?x=1#anchor "title")\n'
                '![image](<https://v8std.ru/std/437.md>)\n'
                '[reference][ref]\n[ref]: https://v8std.ru/std/437/ "title"\n'
                '<https://v8std.ru/std/437/>\n'
                '<a href="https://v8std.ru/std/437/?x=1&amp;y=2#z">a</a>\n'
                '<img src=https://v8std.ru/std/437.md>\n'
                '```bsl\nx = "https://v8std.ru/std/437/";\n'
                '[code](https://v8std.ru/std/437/)\n```\n'
                '    [indented](https://v8std.ru/std/437/)\n'
                '<code>[literal](https://v8std.ru/std/437/)</code>\n'
                '<pre><a href="https://v8std.ru/std/437/">literal</a></pre>\n'
                'ordinary https://v8std.ru/std/437/\n')
        original = {"page": {**fixture.page_fixture(), "body_markdown": body,
                    "source_urls": ["https://its.1c.ru/db/v8std/content/437/hdoc"]},
                    "related": [{"url": PUBLIC + "std/437/"}]}
        result = self.present(original)
        self.assertEqual(original["page"]["body_markdown"], body)
        self.assertEqual(result["page"]["url"], LOCAL + "std/437/")
        self.assertEqual(result["page"]["source_urls"], ["https://its.1c.ru/db/v8std/content/437/hdoc"])
        rendered = result["page"]["body_markdown"]
        for literal in ('`https://v8std.ru/std/437/`', '[code](https://v8std.ru/std/437/)',
                        '    [indented](https://v8std.ru/std/437/)',
                        '<code>[literal](https://v8std.ru/std/437/)</code>',
                        '<pre><a href="https://v8std.ru/std/437/">literal</a></pre>',
                        'ordinary https://v8std.ru/std/437/'):
            self.assertIn(literal, rendered)
        self.assertIn('[link](' + LOCAL + 'std/437/?x=1#anchor "title")', rendered)
        self.assertIn('![image](<' + LOCAL + 'std/437.md>)', rendered)
        self.assertIn('[ref]: ' + LOCAL + 'std/437/ "title"', rendered)
        self.assertIn('<' + LOCAL + 'std/437/>', rendered)
        self.assertIn('href="' + LOCAL + 'std/437/?x=1&amp;y=2#z"', rendered)
        self.assertIn('src=' + LOCAL + 'std/437.md', rendered)
        self.assertEqual(result["related"][0]["url"], LOCAL + "std/437/")

    def test_relative_license_catalog_and_unknown_internal_validation(self):
        module = self.module()
        page = {"id": "third", "url": PUBLIC + PATHS["third"]["site_path"],
                "body_markdown": '[L](../LICENSES/LGPL-3.0.txt) [G](../LICENSES/GPL-3.0.txt) '
                                 '[E](../LICENSES/EPL-2.0.txt) [D](../LICENSES/)'}
        rendered = self.present(page)["body_markdown"]
        for path in ("LGPL-3.0.txt", "GPL-3.0.txt", "EPL-2.0.txt", ""):
            self.assertIn(LOCAL + "LICENSES/" + path, rendered)
        with self.assertRaisesRegex(ValueError, "unresolved_internal_link"):
            module.validate_links('[bad](https://v8std.ru/not-published/)',
                                  canonical_site_url=PUBLIC, page_paths=PATHS)
        for text in ('`[code](https://v8std.ru/not-published/)`', '[source](https://its.1c.ru/x)',
                     '[R](https://v8std.ru/llms.txt)', '[R](https://v8std.ru/llms-full.txt)',
                     '[R](https://v8std.ru/ai/pages.jsonl)'):
            module.validate_links(text, canonical_site_url=PUBLIC, page_paths=PATHS)

    def test_generated_fields_and_page_context_only_in_resource_mode(self):
        text = ('URL: https://v8std.ru/THIRD_PARTY_DIAGNOSTIC_ARTICLES/\n'
                'Markdown URL: https://v8std.ru/THIRD_PARTY_DIAGNOSTIC_ARTICLES.md\n'
                '[license](../LICENSES/EPL-2.0.txt)\n'
                '- [std](https://v8std.ru/std/437.md): HTML: https://v8std.ru/std/437/. Title.\n'
                '`HTML: https://v8std.ru/std/437/`\n'
                'value = "URL: https://v8std.ru/std/437/ ";\n'
                'External sources: <https://v8std.ru/std/437/>\n\n'
                'External sources: https://its.1c.ru/example\n')
        rendered = self.module().present_markdown(text, canonical_site_url=PUBLIC,
                          site_url=LOCAL, page_paths=PATHS, generated_fields=True)
        self.assertIn('URL: ' + LOCAL + 'THIRD_PARTY_DIAGNOSTIC_ARTICLES/', rendered)
        self.assertIn('HTML: ' + LOCAL + 'std/437/. Title.', rendered)
        self.assertIn('[license](' + LOCAL + 'LICENSES/EPL-2.0.txt)', rendered)
        self.assertIn('`HTML: https://v8std.ru/std/437/`', rendered)
        self.assertIn('value = "URL: https://v8std.ru/std/437/ ";', rendered)
        self.assertIn('External sources: <https://v8std.ru/std/437/>', rendered)
        self.assertIn('External sources: https://its.1c.ru/example', rendered)

    def test_publisher_rejects_unresolved_links_using_shared_catalog(self):
        from generate_mcp_snapshot import build_snapshot
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root)
            (root / "llms.txt").write_text('[bad](https://v8std.ru/not-published/)', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unresolved_internal_link"):
                build_snapshot(root, fixture.SOURCE_SHA, PUBLIC)

    def test_structured_url_suffixes_and_escaped_balanced_destinations(self):
        result = self.present({"id": "std437", "url": PUBLIC + "std/437/?view=full#section"})
        self.assertEqual(result["url"], LOCAL + "std/437/?view=full#section")
        body = '[a `label`][ref]\n[ref]:\n  <https://v8std.ru/std/437/> "title"\n'
        self.assertIn('<' + LOCAL + 'std/437/>', self.present({"body_markdown": body})["body_markdown"])

    def test_local_lookup_does_not_escape_prefix(self):
        catalog = self.module().LinkCatalog(PUBLIC, LOCAL, PATHS)
        self.assertEqual(catalog.lookup(LOCAL + "std/437/?view=full#x"), PUBLIC + "std/437/")
        for value in ("http://localhost:8080/other/std/437/", LOCAL + "../std/437/",
                      LOCAL + "std%2f437/", "https://external.invalid/std/437/"):
            self.assertEqual(catalog.lookup(value), value)


if __name__ == "__main__":
    unittest.main()
