import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_article_html import Violation, check_html, check_site, main


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = '<article class="md-content__inner md-typeset">{}</article>'


class ArticleHTMLTests(unittest.TestCase):
    def test_block_inside_paragraph(self):
        count, issues = check_html(
            ARTICLE.format('<p>До<div><pre>x</pre></div>После</p>'), 'bad.html'
        )
        self.assertEqual(count, 1)
        self.assertEqual([v.code for v in issues], ['BLOCK_IN_PARAGRAPH'] * 2)
        self.assertTrue(all(v.path == 'bad.html' and v.line > 0 and v.column > 0 for v in issues))

    def test_every_non_phrasing_tag_inside_paragraph(self):
        tags = (
            'address article aside blockquote body caption center col colgroup dd details '
            'dialog dir div dl dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 '
            'head header hgroup hr html legend li main menu nav ol p pre search section style summary '
            'table tbody td tfoot th thead title tr ul'
        ).split()
        for tag in tags:
            with self.subTest(tag=tag):
                _, issues = check_html(ARTICLE.format(f'<p><{tag}>x</{tag}></p>'))
                self.assertEqual([v.code for v in issues], ['BLOCK_IN_PARAGRAPH'])
                self.assertEqual(issues[0].message, f'<{tag}> inside <p>')

    def test_block_beneath_inline_element_inside_paragraph(self):
        _, issues = check_html(ARTICLE.format('<p><span><div>x</div></span></p>'))
        self.assertEqual([v.code for v in issues], ['BLOCK_IN_PARAGRAPH'])

    def test_inline_links_entities_and_void_elements(self):
        body = '<p>До<a href="?a=1&amp;b=2"><em>link</em></a><br><img src="x">&lt;div&gt;</p>'
        body += '<hr><h6>1</h6><p>После</p>'
        self.assertEqual(check_html(ARTICLE.format(body)), (1, []))

    def test_void_tags_do_not_hide_direct_text(self):
        for tag in 'area base br col embed hr img input link meta param source track wbr'.split():
            for ending in ('>', '/>'):
                with self.subTest(tag=tag, ending=ending):
                    body = f'<{tag}{ending}Текст<h6>1</h6>'
                    self.assertEqual(
                        [v.code for v in check_html(ARTICLE.format(body))[1]],
                        ['DIRECT_ARTICLE_TEXT'],
                    )

    def test_direct_text_is_rejected_even_before_h6(self):
        for body in ('Текст<h6>1</h6>', '<h6>1</h6>Текст'):
            with self.subTest(body=body):
                self.assertEqual(
                    [v.code for v in check_html(ARTICLE.format(body))[1]],
                    ['DIRECT_ARTICLE_TEXT'],
                )

    def test_non_grid_text_and_nested_h6_are_allowed(self):
        for body in ('Текст', '<section><h6>1</h6></section>Текст', ' \n<!-- note --><h6>1</h6><p>Текст</p>'):
            with self.subTest(body=body):
                self.assertEqual(check_html(ARTICLE.format(body)), (1, []))

    def test_whitespace_entities_are_allowed_but_text_entities_are_not(self):
        self.assertEqual(check_html(ARTICLE.format('&#32;&#10;&nbsp;<h6>1</h6>')), (1, []))
        _, issues = check_html(ARTICLE.format('&lt;p&gt;&#88;&amp;<h6>1</h6>'))
        self.assertEqual([v.code for v in issues], ['DIRECT_ARTICLE_TEXT'])

    def test_code_comments_raw_text_and_other_articles_are_not_markup(self):
        good = ARTICLE.format(
            '<h6>1</h6><pre><code>&lt;p&gt;&lt;div&gt;x&lt;/div&gt;</code></pre><!-- <p><div> -->'
        )
        good += '<article class="other"><p><div>not in scope</div></p></article>'
        for tag in ('script', 'style', 'textarea', 'title'):
            good += ARTICLE.format(f'<{tag}><p><div>literal</div></p></{tag}>')
        self.assertEqual(check_html(good), (5, []))

    def test_all_raw_elements_ignore_literal_markup(self):
        for tag in 'script style textarea title xmp iframe noembed noframes plaintext'.split():
            with self.subTest(tag=tag):
                body = f'<{tag}><p><div>literal</div></p><h6>fake</h6></{tag}>Текст'
                self.assertEqual(check_html(ARTICLE.format(body)), (1, []))

    def test_raw_text_cannot_change_tokenizer_mode_or_hide_following_blocks(self):
        for tag in ('textarea', 'title', 'xmp', 'iframe', 'noembed', 'noframes'):
            for literal in ('<script>', '<!--', '</article>' + ARTICLE.format('<h6>fake</h6>')):
                with self.subTest(tag=tag, literal=literal):
                    body = f'<{tag}>{literal}</{tag}><p><div>bad</div></p>'
                    count, issues = check_html(ARTICLE.format(body))
                    self.assertEqual(count, 1)
                    self.assertEqual([v.code for v in issues], ['BLOCK_IN_PARAGRAPH'])

    def test_article_classes_match_tokens_regardless_of_order(self):
        for classes in ('md-content__inner md-typeset', 'extra md-typeset\tmd-content__inner'):
            with self.subTest(classes=classes):
                self.assertEqual(
                    check_html(f'<ARTICLE CLASS="{classes}"><P>ok</P></ARTICLE>'), (1, [])
                )
        for attribute in ('', ' class', ' class="md-typeset"', ' class="md-content__inner"',
                          ' class="md-content__inner-x md-typeset"'):
            with self.subTest(attribute=attribute):
                self.assertEqual(check_html(f'<article{attribute}><p><div>x</div></p></article>'), (0, []))

    def test_repeated_articles_keep_grid_state_local(self):
        text = ARTICLE.format('before<h6>1</h6>after')
        text += ARTICLE.format('allowed')
        text += ARTICLE.format('<p>valid</p><h6>2</h6>')
        count, issues = check_html(text)
        self.assertEqual(count, 3)
        self.assertEqual([v.code for v in issues], ['DIRECT_ARTICLE_TEXT'] * 2)

    def test_nested_articles_keep_grid_state_local(self):
        text = ARTICLE.format('allowed' + ARTICLE.format('bad<h6>1</h6>') + 'allowed')
        count, issues = check_html(text)
        self.assertEqual(count, 2)
        self.assertEqual([v.code for v in issues], ['DIRECT_ARTICLE_TEXT'])

    def test_coordinates_are_one_based_in_serialized_source(self):
        text = ARTICLE.format('\n<p>До\n  <span><div>x</div></span></p>\n<h6>1</h6>\nТекст')
        self.assertEqual(check_html(text, 'nested/page.html')[1], [
            Violation('nested/page.html', 3, 9, 'BLOCK_IN_PARAGRAPH', '<div> inside <p>'),
            Violation('nested/page.html', 4, 11, 'DIRECT_ARTICLE_TEXT',
                      'text outside an element in h6/grid article'),
        ])

    def test_unclosed_article_flushes_direct_text_at_eof(self):
        text = '<article class="md-content__inner md-typeset">before<h6>1</h6>after'
        count, issues = check_html(text)
        self.assertEqual(count, 1)
        self.assertEqual([v.code for v in issues], ['DIRECT_ARTICLE_TEXT'] * 2)

    def test_ancestor_end_closes_article_and_ignores_unmatched_end_tags(self):
        text = '<main><article class="md-content__inner md-typeset"><h6>1</h6>bad</main>'
        text += '</unknown><p><div>outside</div></p>'
        self.assertEqual([v.code for v in check_html(text)[1]], ['DIRECT_ARTICLE_TEXT'])

    def test_self_closing_elements_do_not_leak_stack_state(self):
        body = '<p><span/>ok<div/></p><h6/>bad'
        self.assertEqual([v.code for v in check_html(ARTICLE.format(body))[1]], [
            'BLOCK_IN_PARAGRAPH', 'DIRECT_ARTICLE_TEXT',
        ])
        self.assertEqual(check_html('<article class="md-content__inner md-typeset"/>'), (1, []))

    def test_site_is_read_only_and_covers_nested_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'nested').mkdir()
            (site / 'index.html').write_text(ARTICLE.format('<p>ok</p>'), encoding='utf-8')
            bad = site / 'nested/bad.html'
            bad.write_text(ARTICLE.format('<p><ul><li>x</li></ul></p>'), encoding='utf-8')
            before = {p: p.read_bytes() for p in site.rglob('*.html')}
            count, issues = check_site(site)
            self.assertEqual(count, 2)
            self.assertEqual({v.code for v in issues}, {'BLOCK_IN_PARAGRAPH'})
            self.assertEqual({v.path for v in issues}, {'nested/bad.html'})
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_site_traversal_is_sorted_and_html_suffix_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for relative in ('z/z.HTML', 'a/z.html', 'a/a.html', 'z.HTML', 'a.html'):
                page = site / relative
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text(ARTICLE.format('bad<h6>1</h6>'), encoding='utf-8')
            (site / 'ignored.txt').write_bytes(b'\xff')
            count, issues = check_site(site)
            self.assertEqual(count, 5)
            self.assertEqual([v.path for v in issues], ['a.html', 'z.HTML', 'a/a.html', 'a/z.html', 'z/z.HTML'])

    def test_site_counts_articles_not_files(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'index.html').write_text(ARTICLE.format('<p>ok</p>') * 2, encoding='utf-8')
            (site / 'other.html').write_text('<article class="other">ignored</article>', encoding='utf-8')
            self.assertEqual(check_site(site), (2, []))

    def test_missing_site_or_file_is_site_error(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'file'
            file.write_text('file', encoding='utf-8')
            for site in (Path(directory) / 'missing', file):
                with self.subTest(site=site):
                    count, issues = check_site(site)
                    self.assertEqual(count, 0)
                    self.assertEqual([v.code for v in issues], ['SITE_ERROR'])
                    self.assertEqual((issues[0].path, issues[0].line, issues[0].column), (str(site), 1, 1))

    def test_empty_site_or_no_matching_article_is_no_articles(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for body in (None, '<article class="other"><p>x</p></article>'):
                with self.subTest(body=body):
                    if body is not None:
                        (site / 'index.html').write_text(body, encoding='utf-8')
                    count, issues = check_site(site)
                    self.assertEqual(count, 0)
                    self.assertEqual([v.code for v in issues], ['NO_ARTICLES'])

    def test_read_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'index.html').write_text(ARTICLE.format('<p>ok</p>'), encoding='utf-8')
            with patch.object(Path, 'read_text', side_effect=OSError('denied')):
                count, issues = check_site(site)
            self.assertEqual(count, 0)
            self.assertEqual([v.code for v in issues], ['READ_ERROR', 'NO_ARTICLES'])
            self.assertEqual(issues[0], Violation('index.html', 1, 1, 'READ_ERROR', 'denied'))

    def test_decoding_error_does_not_skip_remaining_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'a.html').write_bytes(b'\xff')
            (site / 'z.html').write_text(ARTICLE.format('<p>ok</p>'), encoding='utf-8')
            count, issues = check_site(site)
            self.assertEqual(count, 1)
            self.assertEqual([v.code for v in issues], ['READ_ERROR'])
            self.assertEqual((issues[0].path, issues[0].line, issues[0].column), ('a.html', 1, 1))

    def test_directory_walk_error_fails_closed(self):
        def fail_walk(site, *, onerror):
            onerror(OSError('denied'))

        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            with patch('scripts.check_article_html.os.walk', side_effect=fail_walk):
                count, issues = check_site(site)
            self.assertEqual(count, 0)
            self.assertEqual(issues, [
                Violation(str(site), 1, 1, 'READ_ERROR', 'denied'),
                Violation(str(site), 1, 1, 'NO_ARTICLES', 'no matching articles found'),
            ])

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / 'scripts/check_article_html.py'), *args],
            capture_output=True, text=True, check=False,
        )

    def test_cli_success(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'index.html').write_text(ARTICLE.format('<p>ok</p>'), encoding='utf-8')
            result = self.run_cli('--site', str(site))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'articles=1 violations=0\n')
            self.assertEqual(result.stderr, '')

    def test_cli_bad_site(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'index.html').write_text(ARTICLE.format('<p><div>x</div></p>'), encoding='utf-8')
            result = self.run_cli('--site', str(site))
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stdout,
                             'index.html:1:50: BLOCK_IN_PARAGRAPH: <div> inside <p>\n'
                             'articles=1 violations=1\n')
            self.assertEqual(result.stderr, '')

    def test_cli_missing_empty_no_article_and_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for case, code, violations in (
                ('missing', 'SITE_ERROR', 1), ('empty', 'NO_ARTICLES', 1),
                ('no-article', 'NO_ARTICLES', 1), ('invalid-utf8', 'READ_ERROR', 2),
            ):
                with self.subTest(case=case):
                    target = site / case
                    if case != 'missing':
                        target.mkdir()
                    if case == 'no-article':
                        (target / 'index.html').write_text('<p>not an article</p>', encoding='utf-8')
                    if case == 'invalid-utf8':
                        (target / 'index.html').write_bytes(b'\xff')
                    result = self.run_cli('--site', str(target))
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(f':1:1: {code}: ', result.stdout)
                    self.assertTrue(result.stdout.endswith(f'articles=0 violations={violations}\n'))
                    self.assertEqual(result.stderr, '')

    def test_cli_invalid_arguments_keep_argparse_exit_two(self):
        for args in ((), ('--unknown',), ('--site',)):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertIn('usage:', result.stderr)

    def test_main_accepts_explicit_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'index.html').write_text(ARTICLE.format('<p>ok</p>'), encoding='utf-8')
            with patch('builtins.print') as output:
                self.assertEqual(main(['--site', str(site)]), 0)
            output.assert_called_once_with('articles=1 violations=0')


class BuildGateTests(unittest.TestCase):
    def test_build_gate_exit_order_and_import_path(self):
        fake_python = '''#!/bin/sh
printf '%s\\n' "$*" >> "$V8STD_TEST_CALLS"
printf '%s\\n' "${PYTHONPATH:-}" >> "$V8STD_TEST_PATHS"
if [ "${1:-}" = "-" ]; then
  command cat >/dev/null
  exit 0
fi
case "${1:-}" in
  */check_article_html.py) exit "$V8STD_TEST_CHECK_EXIT" ;;
esac
exit 0
'''
        for check_exit in (0, 1):
            for inherited_path in (None, '/existing/modules'):
                with self.subTest(check_exit=check_exit, pythonpath=inherited_path):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory).resolve()
                        scripts = root / 'runtime/scripts'
                        scripts.mkdir(parents=True)
                        for name in ('zensical_docs.sh', 'zensical-version.sh'):
                            shutil.copy2(ROOT / 'scripts' / name, scripts / name)
                        content = root / 'content'
                        content.mkdir()
                        (content / 'zensical.toml').write_text('[project]\n', encoding='utf-8')
                        python = root / 'venv/bin/python'
                        python.parent.mkdir(parents=True)
                        python.write_text(fake_python, encoding='utf-8')
                        python.chmod(0o755)
                        calls_path = root / 'calls'
                        paths_path = root / 'paths'
                        env = dict(os.environ)
                        env.pop('PYTHONPATH', None)
                        if inherited_path is not None:
                            env['PYTHONPATH'] = inherited_path
                        env.update(
                            VIRTUAL_ENV=str(root / 'venv'), V8STD_REPO_ROOT=str(content),
                            V8STD_TEST_CALLS=str(calls_path), V8STD_TEST_PATHS=str(paths_path),
                            V8STD_TEST_CHECK_EXIT=str(check_exit),
                        )
                        result = subprocess.run(
                            ['bash', str(scripts / 'zensical_docs.sh'), 'build', '--strict'],
                            cwd=content, env=env, capture_output=True, text=True, check=False,
                        )
                        calls = calls_path.read_text().splitlines()
                        checker = f'{scripts}/check_article_html.py --site {content}/site'
                        self.assertEqual(calls.count(checker), 1, calls)
                        self.assertEqual(result.returncode, check_exit, result.stderr)
                        build_index = calls.index('-m zensical build --strict')
                        self.assertEqual(calls[build_index + 1], checker)
                        publishers = [
                            f'{scripts}/publish_diagnostic_sitemap.py --root {content} --sitemap {content}/site/sitemap.xml',
                            f'{scripts}/publish_license_texts.py --site {content}/site',
                            f'{scripts}/generate_ai_artifacts.py --from-site-markdown-cache {content}/.cache/site-markdown-pages.jsonl --write-site-markdown {content}/site',
                        ]
                        self.assertEqual(calls[build_index + 2:], publishers if check_exit == 0 else [])
                        self.assertFalse(any('--write-site-markdown' in c for c in calls[:build_index]))
                        expected_path = f'{content}:{scripts.parent}'
                        if inherited_path is not None:
                            expected_path += ':' + inherited_path
                        self.assertEqual(paths_path.read_text().splitlines(), [expected_path] * len(calls))


if __name__ == '__main__':
    unittest.main()
