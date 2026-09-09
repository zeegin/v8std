#!/usr/bin/env python3
"""Check the serialized ARTICLE_HTML@1.0 boundaries without repairing the DOM.

This is a read-only structural checker, not a full HTML5 validator.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
RAW = set('script style textarea title xmp iframe noembed noframes plaintext'.split())
NON_PHRASING = set((
    'address article aside blockquote body caption center col colgroup dd details '
    'dialog dir div dl dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 '
    'head header hgroup hr html legend li main menu nav ol p pre search section style summary '
    'table tbody td tfoot th thead title tr ul'
).split())


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    column: int
    code: str
    message: str


@dataclass
class Article:
    depth: int
    has_h6: bool = False
    text_positions: list[tuple[int, int]] = field(default_factory=list)


class ArticleParser(HTMLParser):
    # Suppressing callbacks alone does not stop HTMLParser from entering script
    # or comment mode on literal text inside textarea/title and the other RAWs.
    CDATA_CONTENT_ELEMENTS = tuple(sorted(RAW))

    def __init__(self, path: str):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack: list[str] = []
        self.articles: list[Article] = []
        self.count = 0
        self.issues: list[Violation] = []

    def emit(self, code: str, message: str, position: tuple[int, int] | None = None):
        line, column = self.getpos() if position is None else position
        self.issues.append(Violation(self.path, line, column + 1, code, message))

    def finish_articles(self):
        while self.articles and self.articles[-1].depth > len(self.stack):
            article = self.articles.pop()
            if article.has_h6:
                for position in article.text_positions:
                    self.emit('DIRECT_ARTICLE_TEXT', 'text outside an element in h6/grid article', position)

    def handle_starttag(self, tag, attrs):
        if self.stack and self.stack[-1] in RAW:
            return
        if self.articles:
            article = self.articles[-1]
            # Keep the serialized nesting: opening a block never auto-closes p.
            if tag in NON_PHRASING and 'p' in self.stack[article.depth:]:
                self.emit('BLOCK_IN_PARAGRAPH', f'<{tag}> inside <p>')
            if tag == 'h6' and len(self.stack) == article.depth:
                article.has_h6 = True
        if tag not in VOID:
            self.stack.append(tag)
        classes = set((dict(attrs).get('class') or '').split())
        if tag == 'article' and {'md-content__inner', 'md-typeset'} <= classes:
            self.articles.append(Article(len(self.stack)))
            self.count += 1

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] in RAW and tag != self.stack[-1]:
            return
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[index:]
            self.finish_articles()

    def handle_startendtag(self, tag, attrs):
        if self.stack and self.stack[-1] in RAW:
            return
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.articles and len(self.stack) == self.articles[-1].depth and data.strip():
            # A direct h6 may occur later, so decide when the article closes.
            self.articles[-1].text_positions.append(self.getpos())


def check_html(text: str, path: str = '<memory>') -> tuple[int, list[Violation]]:
    parser = ArticleParser(path)
    parser.feed(text)
    parser.close()
    parser.stack.clear()
    parser.finish_articles()
    return parser.count, parser.issues


def check_site(site: Path) -> tuple[int, list[Violation]]:
    if not site.is_dir():
        return 0, [Violation(str(site), 1, 1, 'SITE_ERROR', 'site directory is missing or not a directory')]
    count = 0
    issues: list[Violation] = []

    def fail_walk(error):
        raise error

    try:
        for directory, dirs, files in os.walk(site, onerror=fail_walk):
            dirs.sort()
            for name in sorted(files):
                if not name.lower().endswith('.html'):
                    continue
                path = Path(directory) / name
                relative = path.relative_to(site).as_posix()
                try:
                    found, errors = check_html(path.read_text(encoding='utf-8'), relative)
                except (OSError, UnicodeError) as error:
                    issues.append(Violation(relative, 1, 1, 'READ_ERROR', str(error)))
                    continue
                count += found
                issues.extend(errors)
    except OSError as error:
        issues.append(Violation(str(site), 1, 1, 'READ_ERROR', str(error)))
    if count == 0:
        issues.append(Violation(str(site), 1, 1, 'NO_ARTICLES', 'no matching articles found'))
    return count, issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Check serialized article HTML')
    parser.add_argument('--site', type=Path, required=True)
    args = parser.parse_args(argv)
    count, issues = check_site(args.site)
    for issue in issues:
        print(f'{issue.path}:{issue.line}:{issue.column}: {issue.code}: {issue.message}')
    print(f'articles={count} violations={len(issues)}')
    return int(bool(issues))


if __name__ == '__main__':
    raise SystemExit(main())
