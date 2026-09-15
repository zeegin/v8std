"""Presentation changes link nodes, never retrieval input or code literals."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from markdown_it import MarkdownIt

from tests import mcp_snapshot_fixtures as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PUBLIC = "https://v8std.ru/"
LOCAL = "http://localhost:8080/kb/"
PATHS = {"std437": {"site_path": "std/437/", "markdown_path": "std/437.md"},
         "third": {"site_path": "THIRD_PARTY_DIAGNOSTIC_ARTICLES/",
                   "markdown_path": "THIRD_PARTY_DIAGNOSTIC_ARTICLES.md"}}


class PresentationHelpers:
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("v8std_mcp_presentation"))
        return importlib.import_module("v8std_mcp_presentation")

    def present(self, value):
        return self.module().present_result(value, canonical_site_url=PUBLIC,
                                            site_url=LOCAL, page_paths=PATHS)


class PresentationTests(PresentationHelpers, unittest.TestCase):
    def test_link_nodes_and_nested_urls_preserve_literals_and_provenance(self):
        body = ('`https://v8std.ru/std/437/`\n'
                '[link](https://v8std.ru/std/437/?x=1#anchor "title")\n'
                '![image](<https://v8std.ru/std/437.md>)\n'
                '[reference][ref]\n\n[ref]: https://v8std.ru/std/437/ "title"\n'
                '<https://v8std.ru/std/437/>\n'
                '<a href="https://v8std.ru/std/437/?x=1&amp;y=2#z">a</a>\n'
                '<img src=https://v8std.ru/std/437.md>\n\n'
                '```bsl\nx = "https://v8std.ru/std/437/";\n'
                '[code](https://v8std.ru/std/437/)\n```\n\n'
                '    [indented](https://v8std.ru/std/437/)\n\n'
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
        body = '[a `label`][ref]\n\n[ref]:\n  <https://v8std.ru/std/437/> "title"\n'
        self.assertIn('<' + LOCAL + 'std/437/>', self.present({"body_markdown": body})["body_markdown"])

    def test_local_lookup_does_not_escape_prefix(self):
        catalog = self.module().LinkCatalog(PUBLIC, LOCAL, PATHS)
        self.assertEqual(catalog.lookup(LOCAL + "std/437/?view=full#x"), PUBLIC + "std/437/")
        for value in ("http://localhost:8080/other/std/437/", LOCAL + "../std/437/",
                      LOCAL + "std%2f437/", "https://external.invalid/std/437/"):
            self.assertEqual(catalog.lookup(value), value)


class SemanticPresentationTests(PresentationHelpers, unittest.TestCase):
    def markdown(self, text):
        return self.module().present_markdown(text, canonical_site_url=PUBLIC, site_url=LOCAL, page_paths=PATHS)

    def validate(self, text):
        self.module().validate_links(text, canonical_site_url=PUBLIC, page_paths=PATHS)

    def test_image_alt_html_does_not_hide_following_link_destinations(self):
        for alt in ("<code>", "<pre>", "<script>", "<style>",
                    '<a href="https://v8std.ru/std/437/">alt</a>'):
            text = ('![' + alt + '](https://v8std.ru/std/437.md) '
                    '[visible](https://v8std.ru/std/437/?view=full#query)')
            expected = ('![' + alt + '](http://localhost:8080/kb/std/437.md) '
                        '[visible](http://localhost:8080/kb/std/437/?view=full#query)')
            with self.subTest(alt=alt):
                self.assertEqual(self.markdown(text), expected)

    def test_image_alt_html_does_not_hide_unknown_or_unsafe_visible_targets(self):
        for target in ("https://v8std.ru/not-published/", "https://v8std.ru/std%2f437/"):
            text = '![<code>](https://v8std.ru/std/437.md) [visible](' + target + ')'
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "^unresolved_internal_link$"):
                self.validate(text)

    def test_image_alt_closing_tags_do_not_end_real_html_code_protection(self):
        for tag in ("code", "pre", "script", "style"):
            literal = ('prefix <' + tag + '>![</' + tag + '>](https://v8std.ru/std/437.md) '
                       '[literal](https://v8std.ru/missing/)</' + tag + '> ')
            text = literal + '[visible](https://v8std.ru/std/437/)'
            with self.subTest(tag=tag):
                self.assertEqual(self.markdown(text), literal + '[visible](http://localhost:8080/kb/std/437/)')
                self.validate(text)

    def test_image_alt_isolation_preserves_source_offsets_and_canonical_hash(self):
        text = ('> - Начало\x00 `https://v8std.ru/std/437/`\r\n>\r\n'
                '> ![<code>](https://v8std.ru/std/437.md) '
                '[visible](https://v8std.ru/std/437/)\r\n')
        expected = ('> - Начало\x00 `https://v8std.ru/std/437/`\r\n>\r\n'
                    '> ![<code>](http://localhost:8080/kb/std/437.md) '
                    '[visible](http://localhost:8080/kb/std/437/)\r\n')
        original = {**fixture.page_fixture(), "body_markdown": text}
        canonical_bytes = fixture.json_bytes(original)
        canonical_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        result = self.present(original)
        self.assertEqual(result["body_markdown"], expected)
        self.assertEqual(fixture.json_bytes(original), canonical_bytes)
        self.assertEqual(hashlib.sha256(original["body_markdown"].encode("utf-8")).hexdigest(), canonical_hash)

    def test_pinned_parser_dependency_is_shared_but_pure_format_stays_independent(self):
        from importlib.metadata import version
        self.assertEqual(version("markdown-it-py"), "4.0.0")
        self.assertEqual(version("mcp"), "1.27.0")
        for name in ("requirements.txt", "requirements-mcp.txt"):
            self.assertIn("markdown-it-py==4.0.0", (ROOT / name).read_text().splitlines())

    def test_parser_source_maps_are_released_without_waiting_for_cyclic_gc(self):
        import gc
        import weakref
        from unittest.mock import patch
        references = []
        def parser(*args, **kwargs):
            instance = MarkdownIt(*args, **kwargs)
            references.append(weakref.ref(instance))
            return instance
        enabled = gc.isenabled()
        gc.disable()
        try:
            with patch.object(self.module(), "MarkdownIt", side_effect=parser):
                self.markdown("> [x](https://v8std.ru/std/437/)\n")
            self.assertTrue(references)
            self.assertTrue(all(reference() is None for reference in references),
                            "parser closure retains the document tree/source map")
        finally:
            if enabled:
                gc.enable()
            gc.collect()

    def test_publisher_uses_semantics_for_nested_code_definitions_and_literal_fragments(self):
        from generate_mcp_snapshot import build_snapshot
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root)
            for body, rejected in (
                ('> [r]: https://v8std.ru/missing/\n>\n> [x][r]', True),
                ('- [r]: https://v8std.ru/missing/\n\n  [x][r]', True),
                ('> - ~~~bsl\n>   [x](https://v8std.ru/missing/)', False),
                ('[x](https://v8std.ru/missing/ "unfinished)', False),
                ('[r]: https://v8std.ru/missing/ "title" extra', False),
            ):
                with self.subTest(body=body):
                    (root / "llms.txt").write_text(body)
                    if rejected:
                        with self.assertRaisesRegex(ValueError, "unresolved_internal_link"):
                            build_snapshot(root, fixture.SOURCE_SHA, PUBLIC)
                    else:
                        build_snapshot(root, fixture.SOURCE_SHA, PUBLIC)

    def test_valid_autolink_inside_incomplete_outer_link_and_literal_entity_suffix(self):
        text = '[x](<https://v8std.ru/std/437/?a=&amp;> "unfinished)'
        result = self.markdown(text)
        self.assertEqual(result, text.replace(PUBLIC, LOCAL))
        links = [child for token in MarkdownIt("commonmark").parse(result)
                 for child in (token.children or []) if child.type == "link_open"]
        self.assertEqual([token.attrGet("href") for token in links], [LOCAL + "std/437/?a=&amp;"])
        with self.assertRaisesRegex(ValueError, "unresolved_internal_link"):
            self.validate(text.replace("std/437/", "missing/"))

    def test_multiline_titles_duplicate_references_headings_and_literal_source_bytes(self):
        text = ('# Заголовок\x00 [link](https://v8std.ru/std/437/ "title")\r\n\r\n'
                '[link](https://v8std.ru/std/437/ "a\r\nb")\r\n\r\n'
                '> - [r]:\r\n>     <https://v8std.ru/std/437/> "title"\r\n>\r\n>   [x][r]\r\n\r\n'
                '[r]: https://v8std.ru/std/437.md\r\n\r\n'
                '[same `https://v8std.ru/std/437/`](https://v8std.ru/std/437/)\r\n')
        expected = text.replace('https://v8std.ru/std/437/', LOCAL + 'std/437/')
        expected = expected.replace('`' + LOCAL + 'std/437/`', '`https://v8std.ru/std/437/`')
        expected = expected.replace('https://v8std.ru/std/437.md', LOCAL + 'std/437.md')
        self.assertEqual(self.markdown(text), expected)
        value = {"related": [{"url": PUBLIC + "std/437/?a=&amp;\\)"}]}
        self.assertEqual(self.present(value)["related"][0]["url"], LOCAL + "std/437/?a=&amp;\\)")

    def test_nested_containers_use_commonmark_code_and_reference_semantics(self):
        for prefix, continuation in (("> ", "> "), ("- ", "  "), ("> - ", ">   "),
                                     ("1. > ", "   > "), ("> > ", "> > ")):
            for fence in ("~~~", "```"):
                for closed in (False, True):
                    text = prefix + fence + "bsl\n" + continuation + '[code](https://v8std.ru/missing/)\n'
                    if closed:
                        text += continuation + fence + "\n"
                    with self.subTest(prefix=prefix, fence=fence, closed=closed):
                        self.assertEqual(self.markdown(text), text)
                        self.validate(text)
            text = prefix + '[r]: https://v8std.ru/std/437/ "title"\n\n' + prefix + '[use][r]\n'
            with self.subTest(reference=prefix):
                result = self.markdown(text)
                self.assertEqual(result, text.replace(PUBLIC, LOCAL))
                self.assertIn('href="' + LOCAL + 'std/437/"', MarkdownIt("commonmark").render(result))
                with self.assertRaisesRegex(ValueError, "unresolved_internal_link"):
                    self.validate(text.replace("std/437/", "missing/"))

    def test_only_complete_links_and_titles_are_rewritten_or_validated(self):
        literals = ('[x]({url}', '[x]({url} "unfinished)', '[x]({url} "title" extra)',
                    '![x]({url}', '[r]: {url} "bad" trailing\n')
        for template in literals:
            for path in ("std/437/", "missing/"):
                text = template.format(url=PUBLIC + path)
                with self.subTest(text=text):
                    self.assertEqual(self.markdown(text), text)
                    self.validate(text)
        # Valid fallback reference: only its definition is a destination.
        text = '[x](https://v8std.ru/missing/\n\n[x]: https://v8std.ru/std/437/\n'
        result = self.markdown(text)
        self.assertEqual(result, '[x](https://v8std.ru/missing/\n\n[x]: ' + LOCAL + 'std/437/\n')
        self.validate(text)

    def test_reparsed_markdown_preserves_interpreted_destinations_and_titles(self):
        samples = (
            ('[x](https://v8std.ru/std/437/?q=foo\\)#end "title")', LOCAL + 'std/437/?q=foo)#end'),
            ('[x](https://v8std.ru/std/437/?q=a&amp;b=2)', LOCAL + 'std/437/?q=a&b=2'),
            ('![x](<https://v8std.ru/std/437/?q=hello&#32;world>)', LOCAL + 'std/437/?q=hello%20world'),
            ('> [r]: https://v8std.ru/std/437/?q=foo\\) "title"\n>\n> [x][r]', LOCAL + 'std/437/?q=foo)'),
        )
        for text, expected in samples:
            with self.subTest(text=text):
                rendered = MarkdownIt("commonmark").parse(self.markdown(text))
                links = [child for block in rendered for child in (block.children or [])
                         if child.type in {"link_open", "image"}]
                self.assertEqual(len(links), 1)
                self.assertEqual(links[0].attrGet("href") or links[0].attrGet("src"), expected)
                if '"title"' in text:
                    self.assertEqual(links[0].attrGet("title"), "title")

    def test_html_escaping_uses_actual_attribute_context_and_does_not_decode_backslashes(self):
        class Attributes(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []
            def handle_starttag(self, tag, attrs):
                self.tags.append((tag, dict(attrs)))
        for quote in ('', '"', "'"):
            for suffix, expected in (("?q=hello&#32;world", "?q=hello world"),
                                     ("?q=foo\\)&amp;x=2", "?q=foo\\)&x=2"),
                                     ("?q=&quot;hi&quot;&#39;", '?q="hi"\'')):
                text = '<a href=' + quote + PUBLIC + 'std/437/' + suffix + quote + ' title="keep">x</a>'
                with self.subTest(text=text):
                    parser = Attributes()
                    parser.feed(self.markdown(text))
                    self.assertEqual(parser.tags, [("a", {"href": LOCAL + "std/437/" + expected, "title": "keep"})])

    def test_source_offsets_survive_containers_crlf_tabs_and_repeated_literals(self):
        text = ('> - `https://v8std.ru/std/437/`\r\n>\r\n'
                '>\t[r]: <https://v8std.ru/std/437/?q=a&amp;b=2>\r\n>\r\n'
                '> - [label `literal`][r]\r\n')
        expected = text.replace('[r]: <' + PUBLIC, '[r]: <' + LOCAL)
        self.assertEqual(self.markdown(text), expected)

    def test_multiline_html_code_tags_inside_containers_protect_their_contents(self):
        for tag in ("pre", "code", "script", "style"):
            text = ('> <' + tag + '\r\n> class="sample">\r\n'
                    '> <a href="https://v8std.ru/std/437/">literal</a>\r\n'
                    '> </' + tag + '>\r\n')
            with self.subTest(tag=tag):
                self.assertEqual(self.markdown(text), text)
                self.validate(text.replace("std/437/", "missing/"))

    def test_multiline_html_destination_retains_container_and_line_endings(self):
        text = '> <a href="https://v8std.ru/std/437/?q=hello\r\n> world">x</a>\r\n'
        result = self.markdown(text)
        self.assertEqual(result, text.replace(PUBLIC, LOCAL))
        self.assertIn('href="' + LOCAL + 'std/437/?q=hello\nworld"',
                      MarkdownIt("commonmark").render(result))
        with self.assertRaisesRegex(ValueError, "unresolved_internal_link"):
            self.validate(text.replace("std/437/", "missing/"))


if __name__ == "__main__":
    unittest.main()
