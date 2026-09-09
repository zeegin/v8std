import unittest
from html.entities import name2codepoint
from pathlib import Path
from xml.etree import ElementTree as ET

from markdown import Markdown
from zensical.config import parse_config

from scripts.check_article_html import check_html


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = 'scripts.v8std_markdown'
ARTICLE = '<article class="md-content__inner md-typeset">{}</article>'
CASES = [
    ('backticks', 'До\n```bsl\nx = 1;\n```\nПосле', 'До\n\n```bsl\nx = 1;\n```\n\nПосле'),
    ('tildes', 'До\n~~~bsl\nx = 1;\n~~~\nПосле', 'До\n\n~~~bsl\nx = 1;\n~~~\n\nПосле'),
    ('empty', 'До\n```bsl\n```\nПосле', 'До\n\n```bsl\n```\n\nПосле'),
    ('long-fence', 'До\n````text\n```\n<&>\n````\nПосле', 'До\n\n````text\n```\n<&>\n````\n\nПосле'),
    ('adjacent', 'До\n```text\na\n```\n~~~text\nb\n~~~\nПосле', 'До\n\n```text\na\n```\n\n~~~text\nb\n~~~\n\nПосле'),
    ('attributes', 'До\n```{.bsl #sample}\nx = 1;\n```\nПосле', 'До\n\n```{.bsl #sample}\nx = 1;\n```\n\nПосле'),
    ('quote', '> До\n> ```bsl\n> x = 1;\n> ```\n> После', '> До\n>\n> ```bsl\n> x = 1;\n> ```\n>\n> После'),
    ('list', '- До\n\n    ```bsl\n    x = 1;\n    ```\n    После\n\n- Следующий', '- До\n\n    ```bsl\n    x = 1;\n    ```\n\n    После\n\n- Следующий'),
    ('admonition', '!!! note\n    До\n    ```bsl\n    x = 1;\n    ```\n    После', '!!! note\n    До\n\n    ```bsl\n    x = 1;\n    ```\n\n    После'),
    ('tab', '=== "A"\n    До\n    ```bsl\n    x = 1;\n    ```\n    После', '=== "A"\n    До\n\n    ```bsl\n    x = 1;\n    ```\n\n    После'),
    ('mermaid', 'До\n```mermaid\ngraph TD\nA --> B\n```\nПосле', 'До\n\n```mermaid\ngraph TD\nA --> B\n```\n\nПосле'),
]


def renderer(enabled=True):
    config = parse_config(str(ROOT / 'zensical.toml'))
    extensions = [e for e in config['markdown_extensions'] if e != EXTENSION]
    if enabled:
        extensions.append(EXTENSION)
    return Markdown(extensions=extensions, extension_configs=config['mdx_configs'])


def html_tree(html):
    # ElementTree accepts numeric entities but not HTML names such as &para;.
    for name, codepoint in name2codepoint.items():
        html = html.replace(f'&{name};', f'&#{codepoint};')
    return ET.fromstring(f'<root>{html}</root>')


class MarkdownRenderingTests(unittest.TestCase):
    def test_project_config_loads_extension(self):
        config = parse_config(str(ROOT / 'zensical.toml'))
        self.assertIn(EXTENSION, config['markdown_extensions'])
        md = Markdown(extensions=config['markdown_extensions'],
                      extension_configs=config['mdx_configs'])
        self.assertEqual(check_html(ARTICLE.format(md.convert(CASES[0][1])))[1], [])

    def assert_valid(self, html):
        self.assertEqual(check_html(ARTICLE.format(html))[1], [])

    def assert_pair(self, compact, separated):
        actual = renderer().convert(compact)
        expected = renderer(False).convert(separated)
        self.assertEqual(actual, expected)
        self.assert_valid(actual)
        self.assertEqual(renderer().convert(separated), expected)
        return actual

    def test_context_matrix(self):
        for name, compact, separated in CASES:
            with self.subTest(name=name):
                self.assert_pair(compact, separated)

    def test_code_preservation_and_fence_recognition(self):
        body = '\n<&>\n\twith_tab\n    four_spaces\n\n```\n~~~\nend\n'
        for marker in ('`', '~'):
            for length in (3, 4, 5):
                # Short and different-marker fences remain code inside this fence.
                payload = body if length > 3 else '\n<&>\n\twith_tab\n    four_spaces\n\nend\n'
                if length == 5:
                    payload += marker * 4 + '\nstill code\n'
                fence = marker * length
                with self.subTest(marker=marker, length=length):
                    actual = self.assert_pair(
                        f'До\n{fence}text\n{payload}\n{fence}\nПосле',
                        f'До\n\n{fence}text\n{payload}\n{fence}\n\nПосле',
                    )
                    code = ET.fromstring(f'<root>{actual}</root>').find('.//pre/code')
                    self.assertIsNotNone(code)
                    self.assertIn('<&>', ''.join(code.itertext()))

    def test_document_edges_and_adjacent_fences(self):
        for compact, separated in (
            ('```text\nx\n```', '```text\nx\n```'),
            ('```text\nx\n```\nПосле', '```text\nx\n```\n\nПосле'),
            ('До\n```text\nx\n```', 'До\n\n```text\nx\n```'),
            ('```text\na\n```\n~~~text\nb\n~~~', '```text\na\n```\n\n~~~text\nb\n~~~'),
        ):
            with self.subTest(source=compact):
                self.assert_pair(compact, separated)

    def test_recognized_fence_cannot_become_a_setext_heading(self):
        compact = 'Intro\n\n```text\nx\n```\n---\nAfter'
        reference = 'Intro\n\n```text\nx\n```\n\n---\nAfter'
        actual = self.assert_pair(compact, reference)
        root = html_tree(actual)
        self.assertEqual([node.tag for node in root], ['p', 'div', 'hr', 'p'])
        self.assertEqual(''.join(root.find('./div/pre/code').itertext()), 'x\n')
        for fence in ('```text', '~~~text', '```{.text #sample}'):
            for underline in ('---', '===', '-', '='):
                with self.subTest(fence=fence, underline=underline):
                    source = f'{fence}\nx\n{fence[:3]}\n{underline}\nAfter'
                    separated = source.replace(f'\n{underline}', f'\n\n{underline}')
                    self.assert_pair(source, separated)

    def test_fence_setext_guard_preserves_container_ownership(self):
        compact = 'Intro\n\n```text\nx\n```\n---\nAfter'
        reference = compact.replace('\n---', '\n\n---')
        for prefix, indent, path in (
            ('', '> ', './blockquote'),
            ('- Item\n\n', '    ', './ul/li'),
            ('1. Item\n\n', '    ', './ol/li'),
            ('!!! note\n', '    ', './div'),
            ('=== "A"\n', '    ', './/div[@class="tabbed-block"]'),
            ('- Item\n\n', '    > ', './ul/li/blockquote'),
        ):
            with self.subTest(prefix=prefix, indent=indent):
                wrap = lambda source: prefix + '\n'.join(indent + line for line in source.split('\n'))
                root = html_tree(self.assert_pair(wrap(compact), wrap(reference)))
                container = root.find(path)
                self.assertIsNotNone(container.find('./div/pre/code'))
                self.assertEqual(len(container.findall('./hr')), 1)
                self.assertEqual(len(root.findall('.//h2')), 0)

    def test_setext_and_hr_without_recognized_fence_are_unchanged(self):
        for source in (
            'Title\n===\n\nSubtitle\n---\n\nAfter',
            'Intro\n\n---\nAfter\n\n***\n\n___',
            '> Title\n> ---',
            '- Item\n\n    Title\n    ===',
            'Intro\n\n    ```text\n    x\n    ```\n---\nAfter',
            'Intro\n\n    ```text\n    x\n    ```\n    ---\nAfter',
            '```text\nx\n---\nAfter',
            '<div>raw</div>\n---\nAfter',
            'Intro\n\n```text\nx\n```\n\nTitle\n---\nAfter',
        ):
            with self.subTest(source=source):
                self.assertEqual(renderer().convert(source), renderer(False).convert(source))

    def test_setext_guard_is_idempotent_and_preserves_working_source_and_stashes(self):
        from pymdownx.superfences import SuperFencesCodeExtension

        md = renderer()
        lines = '```text\nx\n```\n---\nAfter'.split('\n')
        for processor in md.preprocessors:
            lines = processor.run(lines)
        block = '\n'.join(lines).strip('\n')
        extension = next(e for e in md.registeredExtensions if isinstance(e, SuperFencesCodeExtension))
        before_html = list(md.htmlStash.rawHtmlBlocks)
        before_code = dict(extension.stash.stash)
        processor = md.parser.blockprocessors['v8std_setext_fence_boundary']
        parent = ET.Element('div')
        blocks = [block]
        self.assertTrue(processor.test(parent, block))
        processor.run(parent, blocks)
        self.assertEqual(len(blocks), 2)
        self.assertEqual('\n'.join(blocks), block)
        self.assertTrue(all(not processor.test(parent, part) for part in blocks))
        self.assertEqual(md.htmlStash.rawHtmlBlocks, before_html)
        self.assertEqual(extension.stash.stash, before_code)
        token = blocks[0]
        for unchanged in ('    ' + block, '> ' + block, 'prefix ' + block,
                          token + '\nAfter', 'Title\n---',
                          md.htmlStash.store('<div>raw</div>') + '\n---'):
            with self.subTest(block=unchanged):
                self.assertFalse(processor.test(parent, unchanged))

    def test_combined_nested_containers(self):
        for compact, separated in (
            ('- Item\n\n    > До\n    > ```text\n    > x\n    > ```\n    > После',
             '- Item\n\n    > До\n    >\n    > ```text\n    > x\n    > ```\n    >\n    > После'),
            ('> !!! note\n>     До\n>     ```text\n>     x\n>     ```\n>     После',
             '> !!! note\n>     До\n>\n>     ```text\n>     x\n>     ```\n>\n>     После'),
            ('- Outer\n\n    - До\n\n        ```text\n        x\n        ```\n        После\n\n    - Next',
             '- Outer\n\n    - До\n\n        ```text\n        x\n        ```\n\n        После\n\n    - Next'),
        ):
            with self.subTest(source=compact):
                self.assert_pair(compact, separated)

    def test_unaffected_markdown_is_byte_identical(self):
        sources = [
            'До `~~~bsl` и `` ``` `` после',
            'До\n\n    x = "<&>"\n    ```bsl\n    x = 1;\n    ```\n\nПосле',
            'До\n```bsl\nx = 1;\nПосле',
            'До\n~~~~text\nx\n~~~\nПосле',
            '<div class="raw">сырой <em>HTML</em></div>\n\nДо <span>После</span>',
            'До\n\n<!-- comment -->\n\n<hr>\n\nПосле',
            '1. До <span>raw</span>\nПосле\n\n2. Следующий',
        ]
        for source in sources:
            with self.subTest(source=source):
                self.assertEqual(renderer().convert(source), renderer(False).convert(source))

    def test_tight_and_loose_lists_preserve_items_code_and_parent(self):
        compact = '- До\n    ```bsl\n    x = 1;\n    ```\n    После\n- Следующий'
        loose = CASES[7][2]
        expected = ET.fromstring(f'<root>{renderer(False).convert(loose)}</root>')
        for source in (compact, CASES[7][1], loose):
            with self.subTest(source=source):
                html = renderer().convert(source)
                self.assert_valid(html)
                root = ET.fromstring(f'<root>{html}</root>')
                items = root.findall('./ul/li')
                self.assertEqual(len(items), 2)
                self.assertEqual(len(root.findall('.//pre')), 1)
                self.assertIsNotNone(items[0].find('./div/pre/code'))
                self.assertIsNone(items[1].find('.//pre'))
                self.assertEqual(
                    ''.join(items[0].find('.//code').itertext()),
                    ''.join(expected.find('.//code').itertext()),
                )
                self.assertEqual(
                    [' '.join(''.join(li.itertext()).split()) for li in items],
                    [' '.join(''.join(li.itertext()).split()) for li in expected.findall('./ul/li')],
                )

    def test_later_loose_item_does_not_wrap_earlier_fence(self):
        reference = '1. До\n\n    ```text\n    x <&>\n    ```\n\n    После\n\n2. Следующий'
        for indent in ('', '    '):
            compact = f'1. До\n{indent}```text\n{indent}x <&>\n{indent}```\n{indent}После\n\n2. Следующий'
            with self.subTest(indent=indent):
                actual = self.assert_pair(compact, reference)
                root = ET.fromstring(f'<root>{actual}</root>')
                self.assertEqual(len(root.findall('./ol/li')), 2)
                self.assertEqual(len(root.findall('./ol/li/div/pre/code')), 1)
                self.assertEqual(''.join(root.find('./ol/li/div/pre/code').itertext()), 'x <&>\n')

    def test_later_loose_item_does_not_wrap_fence_in_child_tail(self):
        compact = '1. # До\n```text\nx\n```\nПосле\n\n2. Следующий'
        reference = '1. # До\n\n    ```text\n    x\n    ```\n\n    После\n\n2. Следующий'
        self.assert_pair(compact, reference)

    def test_tight_lists_with_unindented_fences_remain_byte_identical(self):
        for marker in ('1.', '-'):
            for prefix in ('До', '# До'):
                source = f'{marker} {prefix}\n```text\nx\n```\nПосле\n{marker} Следующий'
                with self.subTest(marker=marker, prefix=prefix):
                    baseline = renderer(False).convert(source)
                    self.assert_valid(baseline)
                    self.assertEqual(renderer().convert(source), baseline)

    def test_loose_transition_with_adjacent_and_terminal_fences(self):
        for marker in ('1.', '-'):
            for suffix in ('', '\nПосле'):
                compact = f'{marker} До\n```text\nx\n```\n~~~text\ny\n~~~{suffix}\n\n{marker} Следующий'
                reference = (
                    f'{marker} До\n\n    ```text\n    x\n    ```\n\n    ~~~text\n    y\n    ~~~'
                    + ('\n\n    После' if suffix else '') + f'\n\n{marker} Следующий'
                )
                with self.subTest(marker=marker, suffix=suffix):
                    self.assert_pair(compact, reference)

    def test_nested_loose_transition_preserves_inline_markup(self):
        compact = '> 1. **До**\n> ```text\n> x\n> ```\n> [После](https://example.com)\n>\n> 2. Следующий'
        reference = '> 1. **До**\n>\n>     ```text\n>     x\n>     ```\n>\n>     [После](https://example.com)\n>\n> 2. Следующий'
        actual = self.assert_pair(compact, reference)
        root = html_tree(actual)
        self.assertEqual(len(root.findall('./blockquote/ol/li')), 2)
        self.assertEqual(root.find('.//li/p/a').get('href'), 'https://example.com')

    def test_list_boundary_pass_is_idempotent_and_preserves_stashes(self):
        from pymdownx.superfences import SuperFencesCodeExtension

        md = renderer()
        lines = '1. До\n```text\nx\n```\nПосле\n\n2. Следующий'.split('\n')
        for processor in md.preprocessors:
            lines = processor.run(lines)
        root = md.parser.parseDocument(lines).getroot()
        extension = next(e for e in md.registeredExtensions if isinstance(e, SuperFencesCodeExtension))
        html_stash = list(md.htmlStash.rawHtmlBlocks)
        code_stash = dict(extension.stash.stash)
        processor = md.treeprocessors['v8std_list_fence_boundary']
        processor.run(root)
        self.assertEqual(len(root.findall('./ol/li/p')), 4)
        once = ET.tostring(root)
        processor.run(root)
        self.assertEqual(ET.tostring(root), once)
        self.assertEqual(md.htmlStash.rawHtmlBlocks, html_stash)
        self.assertEqual(extension.stash.stash, code_stash)

    def test_real_loose_list_article_preserves_code_and_source(self):
        path = ROOT / 'docs/diagnostics/bslls/TransferringParametersBetweenClientAndServer.md'
        before = path.read_bytes()
        source = before.decode('utf-8')
        actual = renderer().convert(source)
        self.assert_valid(actual)
        root = html_tree(actual)
        baseline = html_tree(renderer(False).convert(source))
        self.assertEqual(
            [''.join(code.itertext()) for code in root.findall('.//pre/code')],
            [''.join(code.itertext()) for code in baseline.findall('.//pre/code')],
        )
        items = root.findall('./ol/li')
        self.assertEqual(len(items), 2)
        self.assertEqual(len(items[0].findall('./div/pre/code')), 2)
        self.assertEqual(len(items[1].findall('./div/pre/code')), 1)
        self.assertEqual(path.read_bytes(), before)

    def test_extension_registration_order(self):
        for position in (0, 1, -1):
            config = parse_config(str(ROOT / 'zensical.toml'))
            extensions = [e for e in config['markdown_extensions'] if e != EXTENSION]
            extensions.insert(position, EXTENSION)
            md = Markdown(extensions=extensions, extension_configs=config['mdx_configs'])
            with self.subTest(position=position):
                self.assertEqual(md.convert(CASES[0][1]), renderer(False).convert(CASES[0][2]))
                source = '1. До\n```text\nx\n```\nПосле\n\n2. Следующий'
                self.assertEqual(md.reset().convert(source), renderer().convert(source))

    def test_reset_clears_document_state(self):
        md = renderer()
        for source in (CASES[4][1], '<div>raw</div>\n\nplain', CASES[0][1], CASES[9][1],
                       '1. До\n```text\nx\n```\nПосле\n\n2. Следующий'):
            with self.subTest(source=source):
                self.assertEqual(md.reset().convert(source), renderer().convert(source))

    def test_partition_is_idempotent_and_does_not_edit_stash(self):
        from scripts.v8std_markdown import split_fence_blocks
        from pymdownx.superfences import SuperFencesCodeExtension

        md = renderer()
        lines = CASES[0][1].split('\n')
        for processor in md.preprocessors:
            lines = processor.run(lines)
        block = '\n'.join(lines).strip('\n')
        extension = next(e for e in md.registeredExtensions if isinstance(e, SuperFencesCodeExtension))
        before_html = list(md.htmlStash.rawHtmlBlocks)
        before_code = dict(extension.stash.stash)
        first = split_fence_blocks(md, block)
        self.assertEqual(len(first), 3)
        self.assertEqual(first[0], 'До')
        self.assertEqual(first[-1], 'После')
        second = [part for value in first for part in split_fence_blocks(md, value)]
        self.assertEqual(first, second)
        self.assertEqual(md.htmlStash.rawHtmlBlocks, before_html)
        self.assertEqual(extension.stash.stash, before_code)
        token = first[1]
        for unchanged in ('', 'plain', token, '    ' + token,
                          f'prefix {token} suffix', 'До\n' + md.htmlStash.store('<div>raw</div>') + '\nПосле'):
            with self.subTest(block=unchanged):
                self.assertEqual(split_fence_blocks(md, unchanged), [unchanged])

    def test_missing_superfences_fails_explicitly(self):
        from scripts.v8std_markdown import split_fence_blocks

        with self.assertRaisesRegex(RuntimeError, 'requires pymdownx.superfences'):
            split_fence_blocks(Markdown(), 'plain')

    def test_compact_fence_equals_separated_reference(self):
        source = 'До\n```bsl\nЗначение = "<&>";\n```\nПосле'
        reference = 'До\n\n```bsl\nЗначение = "<&>";\n```\n\nПосле'
        actual = renderer().convert(source)
        self.assertEqual(actual, renderer(False).convert(reference))
        self.assertEqual(check_html(ARTICLE.format(actual))[1], [])

    def test_real_issue_has_valid_structure_without_source_change(self):
        path = ROOT / 'docs/diagnostics/bslls/SetPrivilegedMode.md'
        before = path.read_bytes()
        actual = renderer().convert(before.decode('utf-8'))
        self.assertEqual(check_html(ARTICLE.format(actual))[1], [])
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
