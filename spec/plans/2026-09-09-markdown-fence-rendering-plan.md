---
schema_version: 1
kind: plan
id: markdown-fence-rendering
design: design:markdown-fence-rendering
implements:
  - design:markdown-fence-rendering
  - adr:NORMALIZE_FENCES_AT_RENDER_BOUNDARY
  - invariant:MARKDOWN_RENDERING_PRESERVES_SOURCE_AND_CODE
  - contract:ARTICLE_HTML@1.0
---

# Markdown Fence Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking. Read the spec and Global Constraints before each task.

**Goal:** Исправить причину #35 в общем Markdown pipeline и блокировать сборку с нарушениями HTML-контракта, сохранив исходный корпус и содержимое кода.

**Architecture:** SuperFences продолжает распознавать и подсвечивать fences. Узкая защита не позволяет Setext поглотить маркер кода; block processor разделяет маркеры перед обработчиком абзацев; проход рабочего дерева завершает разделение после позднего преобразования списков, до inline parsing и сериализации. Независимый read-only HTML checker проверяет сериализованные статьи всей сборки до публикации.

**Tech Stack:** Python 3.12+, Zensical 0.0.47, Markdown 3.10.2, PyMdown Extensions 11.0.1 в проверенном локальном окружении; stdlib `html.parser`, `unittest`, существующие shell wrapper и Dockerfile. Версии не обновлять.

**Spec:** [Согласованный design](../designs/2026-09-09-markdown-fence-rendering-design.md), [ADR](../adr/2026-09-09-normalize-fences-at-render-boundary.md), [инвариант](../invariants/markdown-rendering-preserves-source-and-code.md), [HTML contract](../contracts/article-html-v1-r0.md), [сохраняемый chip contract](../contracts/diagnostic-chip-markup-v1-r0.md).

## Global Constraints

- «Версии зависимостей, CSS, шаблоны, исходные статьи, публичные адреса и MCP-сервер не меняются.»
- «Расширение не записывает файлы и не меняет содержимое `docs/`, managed source blocks, provenance-маркеры или `data/diagnostic-sources.json`.»
- «Markdown sidecars и AI/MCP-артефакты продолжают строиться из исходного корпуса, а не из нормализованной для HTML копии.»
- «Нормализация не добавляет и не удаляет строки внутри fenced-блока, не меняет его отступы, язык, атрибуты и порядок.»
- «Сохраняются вложенность списков, цитат, admonitions и tabs.»
- «Неполные конструкции не исправляются выдуманным закрывающим fence.»
- «Повторное применение нормализации не меняет результат.»
- «Обход включает весь собранный корпус, а не allowlist страниц исходного инцидента.»
- «Диагностика содержит путь файла, вид нарушения и его местоположение.»
- «Коррекция не зависит от постобработки только режима `build`, таймера watcher, браузерного JavaScript или поискового параметра.»
- Сохранять `DIAGNOSTIC_CHIP_MARKUP@1.0`; новое состояние `IMPLEMENTED` относится только к четырём целям в front matter этого plan.
- Работать в основном checkout и feature-ветке. Исходная точка плана: `main` / `8e89194`; ветка авторинга `codex/issue-35-markdown-rendering-plan`.
- Не переписывать четыре уже принятых structured-документа. Plan остаётся candidate, пока не выполнены все checkboxes; merge незавершённого plan запрещён.
- Изменение границ design, новый способ исправления HTML после сериализации или необходимость изменять исходный корпус возвращают работу в `superpowers:brainstorming`.
- Push, публикация, изменения GitHub issue и MCP deployment не входят в выполнение этого плана. #35 пока остаётся открытым.

## Карта файлов и порядок

| Файл | Ответственность | Задача |
|---|---|---|
| Create `scripts/check_article_html.py` | HTML parser, обход сайта, ошибки и CLI | 1 |
| Create `tests/test_article_html.py` | Conformance parser/CLI и build gate | 1, 3 |
| Create `scripts/v8std_markdown.py` | Разделение только маркеров SuperFences | 2 |
| Create `tests/test_v8std_markdown.py` | Реальный renderer, код, контекст, исходники | 2, 3 |
| Modify `zensical.toml`, секция `project.markdown_extensions` | Одно подключение для build и serve | 3 |
| Modify `scripts/zensical_docs.sh`, настройка Python и ветка build | Путь импорта и обязательный HTML gate | 3 |
| Create `spec/operations/2026-09-09-markdown-rendering-verification.md` | Фактические результаты baseline, corpus, Docker и браузера | 4 |
| Update этот candidate plan | Только фактически выполненные шаги и доказательства | 1–4 |

`scripts/generate_ai_artifacts.py`, `scripts/diagnostic_articles.py`, CSS,
шаблоны и Dockerfile читаются для проверок, но не изменяются. Новая проверка
не должна стать импортом или побочным действием MCP runtime.

## Проверенные детали существующего pipeline

При авторинге plan на `8e89194` свежий `Markdown` из
`zensical.config.parse_config('zensical.toml')` подтвердил:

```text
Before\n```bsl\nx = 1;\n```\nAfter
→ после SuperFences: Before\n\x02wzxhzdk:0\x03\nAfter
→ итог: <p>Before\n<div class="language-bsl highlight">…</div>\nAfter</p>
```

SuperFences хранит исходники распознанных блоков в `extension.stash`, включая
маркер и исходные отступы. Его indented-code processor может восстановить
слишком жадно распознанный fence. Поэтому не разбирать fences повторно и не
вставлять пустые строки во входной Markdown: работать после этих решений.

Штатные block priorities: indented code 80, списки 40/30, цитаты 20,
reference 15, paragraph 10. Выбранный processor с priority 11 работает внутри
уже выбранного родительского контейнера. Тело подсвеченного HTML в
`htmlStash` не редактируется. Отдельный `<p>PLACEHOLDER</p>` штатно снимается
`RawHtmlPostprocessor`; это существующее поведение, не новый post-build repair.

Zensical преобразует список расширений через `set`, поэтому нельзя полагаться
на порядок их регистрации. Определять установленный SuperFences при обработке
блока, когда все extensions уже зарегистрированы. Не менять зависимости и не
патчить `.venv`. При несовместимом устройстве stash получить явную ошибку,
а не незаметно отключать нормализацию.

---

### Task 1: Структурная проверка HTML статьи

**Files:** Create `scripts/check_article_html.py`, `tests/test_article_html.py`.

**Interfaces:**
- Consumes: UTF-8 HTML, выбранный каталог сборки `Path`.
- Produces: `Violation(path: str, line: int, column: int, code: str, message: str)`; `check_html(text: str, path: str = '<memory>') -> tuple[int, list[Violation]]`; `check_site(site: Path) -> tuple[int, list[Violation]]`; `main(argv: list[str] | None = None) -> int`.
- Координаты one-based. Коды: `BLOCK_IN_PARAGRAPH`, `DIRECT_ARTICLE_TEXT`, `SITE_ERROR`, `READ_ERROR`, `NO_ARTICLES`. Успех CLI — 0, любая ошибка — 1; `argparse` сохраняет штатный 2 для неверных аргументов.

- [x] **Step 1: Добавить RED fixtures parser и corpus CLI.**

В `tests/test_article_html.py` использовать stdlib `unittest`, `tempfile`,
`pathlib`, `unittest.mock.patch`, `subprocess`, `sys`; ошибки чтения моделировать
через `patch.object(Path, 'read_text', side_effect=OSError('denied'))`, а не
через `chmod`, который не гарантирует отказ под root.

```python
from scripts.check_article_html import check_html, check_site

ARTICLE = '<article class="md-content__inner md-typeset">{}</article>'

def test_block_inside_paragraph(self):
    count, issues = check_html(ARTICLE.format('<p>До<div><pre>x</pre></div>После</p>'), 'bad.html')
    self.assertEqual(count, 1)
    self.assertIn('BLOCK_IN_PARAGRAPH', {item.code for item in issues})
    self.assertTrue(all(item.path == 'bad.html' and item.line > 0 and item.column > 0 for item in issues))

def test_direct_text_is_rejected_even_before_h6(self):
    for body in ('Текст<h6>1</h6>', '<h6>1</h6>Текст'):
        with self.subTest(body=body):
            self.assertEqual([v.code for v in check_html(ARTICLE.format(body))[1]], ['DIRECT_ARTICLE_TEXT'])

def test_non_grid_text_and_nested_h6_are_allowed(self):
    for body in ('Текст', '<section><h6>1</h6></section>Текст', ' \n<!-- note --><h6>1</h6><p>Текст</p>'):
        self.assertEqual(check_html(ARTICLE.format(body))[1], [])

def test_code_comments_raw_text_and_other_articles_are_not_markup(self):
    good = ARTICLE.format('<h6>1</h6><pre><code>&lt;p&gt;&lt;div&gt;x&lt;/div&gt;</code></pre><!-- <p><div> -->')
    good += '<article class="other"><p><div>not in scope</div></p></article>'
    for tag in ('script', 'style', 'textarea', 'title'):
        good += ARTICLE.format(f'<{tag}><p><div>literal</div></p></{tag}>')
    self.assertEqual(check_html(good)[1], [])

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
        self.assertIn('nested/bad.html', {v.path for v in issues})
        self.assertEqual(before, {p: p.read_bytes() for p in before})
```

Поместить методы в `ArticleHTMLTests(unittest.TestCase)`. Добавить table-driven
случаи каждого тега из `NON_PHRASING`, вложенного `<span><div>`, обычных inline
ссылок, void-тегов `br/img/hr`, повторных статей и HTML entities. Для CLI
запускать `[sys.executable, str(ROOT / 'scripts/check_article_html.py'), '--site', str(site)]`
с `capture_output=True, text=True, check=False`; проверить 0 на валидном сайте,
1 на bad/missing/empty/no-article сайте и UTF-8 decoding error. Для пустого
каталога ожидается именно `NO_ARTICLES`, для отсутствующего — `SITE_ERROR`.

- [x] **Step 2: Запустить RED и зафиксировать исходный отказ.**

```bash
.venv/bin/python -m unittest tests.test_article_html -v
```

До создания checker ожидается import error. После появления parser ошибки
fixtures должны объясняться HTML-нарушениями, а не отсутствием окружения.

- [x] **Step 3: Реализовать parser без восстановления DOM браузером.**

Использовать `HTMLParser(convert_charrefs=True)`, `dataclass`, `Path`, `os`,
`argparse`. Стек должен хранить сериализованную структуру, без автоматического
закрытия `p` при открытии `div`. Основа данных и обработчиков:

```python
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
RAW = set('script style textarea title xmp iframe noembed noframes plaintext'.split())
NON_PHRASING = set(('address article aside blockquote body caption center col colgroup dd details '
                   'dialog dir div dl dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 '
                   'head header hgroup hr html legend li main menu nav ol p pre search section style summary '
                   'table tbody td tfoot th thead title tr ul').split())

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
    def __init__(self, path: str):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack: list[str] = []
        self.articles: list[Article] = []
        self.count = 0
        self.issues: list[Violation] = []

    def emit(self, code: str, message: str, position=None):
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
            self.articles[-1].text_positions.append(self.getpos())

def check_html(text: str, path: str = '<memory>') -> tuple[int, list[Violation]]:
    parser = ArticleParser(path)
    parser.feed(text)
    parser.close()
    parser.stack.clear()
    parser.finish_articles()
    return parser.count, parser.issues
```

Импортировать `field` вместе с `dataclass`. Не считать этот checker полным
HTML5 validator: он проверяет выбранную статью и две заданные структурные
границы. При появлении нового ложноположительного случая воспроизвести его
структурным fixture, не добавлять исключение по пути статьи.

- [x] **Step 4: Реализовать полный обход и CLI, затем получить GREEN.**

```python
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
```

```bash
.venv/bin/python -m unittest tests.test_article_html -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
.venv/bin/python scripts/check_article_html.py --site site
```

Unit tests должны пройти; старый strict build может пройти, но новый checker
на старом renderer должен обнаружить дефект #35. Сохранить число проверенных
статей и список нарушений как baseline; исторические 42 страницы не являются
assertion. На этом шаге build wrapper ещё не включает новый gate.

### Task 2: Разделение распознанных fenced-блоков перед абзацем

**Files:** Create `scripts/v8std_markdown.py`, `tests/test_v8std_markdown.py`.

**Interfaces:**
- Consumes: штатный `Markdown` с зарегистрированным `SuperFencesCodeExtension`; checker из Task 1 только в тестах.
- Produces: `split_fence_blocks(md: Markdown, block: str) -> list[str]`, `FenceBoundaryExtension(Extension)`, `makeExtension(**kwargs)`.
- Helper возвращает исходный блок единственным элементом, если разделение не нужно. Повторное разбиение каждого результата не меняет список; уже корректный документ рендерится без изменений.

- [x] **Step 1: Добавить RED для реального renderer.**

Не собирать облегчённый список расширений вручную. В тестовом helper каждый
раз получать новый renderer из действующей конфигурации; временно исключать
новое расширение только для baseline/reference:

```python
ROOT = Path(__file__).resolve().parents[1]
EXTENSION = 'scripts.v8std_markdown'

def renderer(enabled: bool = True) -> Markdown:
    config = parse_config(str(ROOT / 'zensical.toml'))
    extensions = [e for e in config['markdown_extensions'] if e != EXTENSION]
    if enabled:
        extensions.append(EXTENSION)
    return Markdown(extensions=extensions, extension_configs=config['mdx_configs'])

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
```

Поместить методы в `MarkdownRenderingTests(unittest.TestCase)`, импортировать
`Markdown`, `parse_config`, `Path`, `unittest`, `check_html`; `ARTICLE` определить
в этом модуле той же строкой, что в Task 1, без импорта теста из теста.

```bash
.venv/bin/python -m unittest tests.test_v8std_markdown -v
```

Ожидается RED: ещё нет расширения, затем — воспроизводимый failing assertion
на структуре без исправления. Не делать исходный дефект обязательным после
будущего обновления renderer: baseline assertion зафиксировать как evidence
текущей реализации, а долговременный regression оставить на корректный результат.

- [x] **Step 2: Реализовать минимальный block processor.**

```python
import re
from markdown import Markdown, util
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from pymdownx.superfences import SuperFencesCodeExtension

PLACEHOLDER = re.compile(util.HTML_PLACEHOLDER % r'[0-9]+')

def split_fence_blocks(md: Markdown, block: str) -> list[str]:
    extension = next((e for e in md.registeredExtensions if isinstance(e, SuperFencesCodeExtension)), None)
    if extension is None:
        raise RuntimeError('v8std Markdown extension requires pymdownx.superfences')
    stash = extension.stash
    parts: list[str] = []
    pending: list[str] = []
    for line in block.split('\n'):
        token = line.strip()
        indent = len(line) - len(line.lstrip(' '))
        recognized = (
            indent < md.tab_length
            and PLACEHOLDER.fullmatch(token) is not None
            and stash.get(token[1:-1]) is not None
        )
        if recognized:
            if pending:
                parts.append('\n'.join(pending))
                pending = []
            parts.append(line)
        else:
            pending.append(line)
    if pending:
        parts.append('\n'.join(pending))
    return parts if len(parts) > 1 else [block]

class FenceBoundaryProcessor(BlockProcessor):
    def test(self, parent, block):
        return len(split_fence_blocks(self.parser.md, block)) > 1

    def run(self, parent, blocks):
        block = blocks.pop(0)
        self.parser.parseBlocks(parent, split_fence_blocks(self.parser.md, block))

class FenceBoundaryExtension(Extension):
    def extendMarkdown(self, md):
        md.registerExtension(self)
        md.parser.blockprocessors.register(FenceBoundaryProcessor(md.parser), 'v8std_fence_boundary', 11)

def makeExtension(**kwargs):
    return FenceBoundaryExtension(**kwargs)
```

Не добавлять broad fallback для любого HTML placeholder, не трогать raw HTML
и не выполнять regex replacement внутри `rawHtmlBlocks`. Проверить отсутствие
рекурсии на одиночном placeholder, отсутствие утечки состояния после `md.reset()`
и независимость результата от позиции расширения в списке регистрации.

Уточнение после полной сборки: block-only пример выше недостаточен для
`TransferringParametersBetweenClientAndServer`. При присоединении следующего
loose item штатный `OListProcessor` оборачивает ранее накопленный текст tight
item в `p` после block pass. Попытка вставить узлы раньше меняет уже корректный
tight-list HTML и отвергнута регрессией byte equality.

Добавить `ListFenceBoundaryProcessor(Treeprocessor)` с priority 25, до inline
processor 20: только непосредственные text-only `p` внутри `li`, только
standalone-маркеры из SuperFences stash. Разделить их на соседние `p`, сохранить
tail на последнем, не разбирать fences заново. В уже сформированном абзаце
indented-code recovery завершён; его прежний guard сохранить в публичном
`split_fence_blocks`, но не применять к маркерам внутри такого `p`.
Это коррекция алгоритма в рамках принятого render boundary, не постобработка HTML.

```python
md.treeprocessors.register(
    ListFenceBoundaryProcessor(md), 'v8std_list_fence_boundary', 25,
)
```

Обязательные регрессии дополнения: переход tight→loose через следующий пункт,
маркер в child tail, ordered/unordered списки, нулевой и четырёхпробельный отступ,
соседние/конечные fences, реальная статья, сохранение byte-identical tight list,
reset/порядок регистрации и повторное применение tree pass.

Уточнение итогового review 10 сентября: Setext с priority 60 может раньше
поглотить одиночный маркер fence перед `---`/`===` и создать ложный заголовок.
Добавить `SetextFenceBoundaryProcessor` с priority 61: сначала использовать
штатный Setext `test`, затем проверить только первые две строки существующим
stash-aware splitter. При совпадении отделить первую строку от неизменённого
остатка и вернуть их обычному parser. General processor остаётся priority 11;
indented-code обработка по-прежнему раньше guard. Контейнерные префиксы и
обычные заголовки не являются standalone-маркерами и не затрагиваются.
Регрессии: compact/reference с `---`, `===`, контейнерами, обычными Setext,
indented code, raw HTML, сохранностью stash и повторным применением. Полное
сравнение с pre-fix renderer подтвердило byte equality всех 1428 текущих статей.

- [x] **Step 3: Зафиксировать матрицу сохранения кода и контейнеров.**

Использовать реальные пары compact/reference; не получать reference тем же
helper, который тестируется. Для корневых примеров сравнивать весь HTML;
для tight/loose lists дополнительно сравнивать текст кода и родителей, чтобы
не принять исчезновение пункта или перемещение блока как исправление.

```python
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

def test_context_matrix(self):
    for name, compact, separated in CASES:
        with self.subTest(name=name):
            actual = renderer().convert(compact)
            expected = renderer(False).convert(separated)
            self.assertEqual(actual, expected)
            self.assertEqual(check_html(ARTICLE.format(actual))[1], [])
            self.assertEqual(renderer().convert(separated), expected)
```

Отдельные неизменяемые fixtures: inline code с fence-подобным текстом, indented code,
незакрытый fence, обычный raw HTML без fences; сравнить `renderer(True)` и
`renderer(False)` byte-for-byte. Добавить код с пустыми строками, табом,
четырьмя пробелами, вложенным fence-подобным текстом, коротким закрывающим
fence и backtick/tilde длины 3/4/5: распознавание остаётся за SuperFences.
Для tight list `- До\n    ```bsl\n    x = 1;\n    ```\n    После\n- Следующий`
проверить два `li` и расположение кода в первом `li`; допустимость оболочек
проверять по корректному эквиваленту, не ослаблять сохранение смысла.

Идемпотентность helper проверять на настоящем stash после preprocessors:

```python
def test_partition_is_idempotent_and_does_not_edit_stash(self):
    md = renderer()
    lines = CASES[0][1].split('\n')
    for processor in md.preprocessors:
        lines = processor.run(lines)
    block = '\n'.join(lines).strip('\n')
    before = list(md.htmlStash.rawHtmlBlocks)
    first = split_fence_blocks(md, block)
    second = [part for value in first for part in split_fence_blocks(md, value)]
    self.assertEqual(first, second)
    self.assertEqual(md.htmlStash.rawHtmlBlocks, before)
```

- [x] **Step 4: Получить GREEN и проверить исходный корпус.**

```bash
.venv/bin/python -m unittest tests.test_v8std_markdown tests.test_article_html -v
.venv/bin/python scripts/check_diagnostic_articles.py
.venv/bin/python scripts/acc_diagnostics.py generate --check
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check
git diff --exit-code -- docs data/diagnostic-sources.json
```

Отсутствие source diff обязательно. Если вложенный fixture опровергает выбор
точки обработки, сначала исследовать причину в пределах согласованного renderer
boundary; необходимость нового подхода за границами design останавливает реализацию.

### Task 3: Общее подключение и обязательный build gate

**Files:** Modify `zensical.toml`, `scripts/zensical_docs.sh`, оба новых test-модуля.

**Interfaces:**
- Consumes: `scripts.v8std_markdown` и CLI `check_article_html.py --site PATH`.
- Produces: одинаковое расширение для `build`/`serve`; build с ненулевым статусом при нарушении; импорт и в checkout, и при запуске wrapper из `/opt/v8std/scripts` с content root `/docs`.

- [x] **Step 1: Добавить RED тест подключения и наблюдаемого shell gate.**

```python
def test_project_config_loads_extension(self):
    config = parse_config(str(ROOT / 'zensical.toml'))
    self.assertIn('scripts.v8std_markdown', config['markdown_extensions'])
    md = Markdown(extensions=config['markdown_extensions'], extension_configs=config['mdx_configs'])
    self.assertEqual(check_html(ARTICLE.format(md.convert(CASES[0][1])))[1], [])
```

В `test_article_html.py` построить временный fake runtime и копию wrapper;
не подменять executable или конфигурацию пользователя. Это только тестовый
`tempfile.TemporaryDirectory`. Копировать wrapper и `zensical-version.sh`
через `shutil.copy2`, создать `content/zensical.toml` с `[project]` и `venv/bin/python`.
Fake Python логирует вызовы и управляемо отказывает только новому checker:

```python
FAKE_PYTHON = '''#!/bin/sh
printf '%s\\n' "$*" >> "$V8STD_TEST_CALLS"
if [ "${1:-}" = "-" ]; then
  command cat >/dev/null
  exit 0
fi
case "${1:-}" in
  */check_article_html.py) exit "$V8STD_TEST_CHECK_EXIT" ;;
esac
exit 0
'''
```

Для каждого `check_exit` из `(0, 1)` запускать `bash wrapper build --strict`
с `cwd=content`, изолированным `VIRTUAL_ENV`, `V8STD_REPO_ROOT`,
`V8STD_TEST_CALLS`, `V8STD_TEST_CHECK_EXIT`. Проверить наблюдаемый exit code,
один вызов checker с точным `--site content/site`, порядок
`-m zensical build --strict` → checker → sitemap/licenses/sidecars.
При `check_exit=1` публикационные helper-вызовы после checker отсутствуют.
В тесте вызовы pre-build generators отличать от публикационного
`--write-site-markdown`. Фикстуры писать обычными Python test API; это код
будущего теста, не shell-правка файлов проекта.

```bash
.venv/bin/python -m unittest tests.test_article_html tests.test_v8std_markdown -v
```

До интеграции ожидается RED: отсутствует extension config/вызов checker.

- [x] **Step 2: Подключить расширение и путь импорта без смены Dockerfile.**

В `zensical.toml` добавить ровно одну quoted dotted table:

```toml
[project.markdown_extensions."scripts.v8std_markdown"]
```

Нельзя использовать unquoted `scripts.v8std_markdown`: преобразователь
Zensical разворачивает вложенные таблицы лишь для известных `pymdownx` и
`zensical`, а не произвольного `scripts` namespace.

В `scripts/zensical_docs.sh` после вычисления `REPO_ROOT`, до Python/Zensical:

```bash
export PYTHONPATH="${REPO_ROOT}:$(dirname -- "${SCRIPT_DIR}")${PYTHONPATH:+:${PYTHONPATH}}"
```

Checkout имеет приоритет; container fallback уже содержит `scripts` благодаря
существующему `COPY scripts /opt/v8std/scripts`. Передача прежнего `PYTHONPATH`
сохраняется. Не устанавливать пакет, не менять `site-packages`/Dockerfile и
не рассчитывать на рабочий каталог процесса как единственное условие импорта.

- [x] **Step 3: Добавить fail-closed build gate и получить GREEN.**

В ветке `build`, непосредственно после успешного `-m zensical "$@"`:

```bash
"${PYTHON_BIN}" "${SCRIPT_DIR}/check_article_html.py" --site "${REPO_ROOT}/site"
```

`set -euo pipefail` уже останавливает wrapper. Не ставить `|| true`, не менять
watcher и не называть `serve` успешной release-проверкой.

```bash
bash -n scripts/zensical_docs.sh
.venv/bin/python -m unittest tests.test_article_html tests.test_v8std_markdown -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
.venv/bin/python scripts/check_article_html.py --site site
```

Ожидается GREEN unit/integration и ноль нарушений во всей свежей сборке.
Число страниц не фиксировать прежним 1429; проверять реальное покрытие и
положительное число статей. Не фильтровать найденные нарушения ради зелёной сборки.

### Task 4: Доказательства сохранности, build/serve, Docker и браузера

**Files:** Create `spec/operations/2026-09-09-markdown-rendering-verification.md`; update candidate plan по факту. Рабочие материалы и screenshots держать вне исходного корпуса.

**Interfaces:**
- Consumes: свежий сайт из Task 3, исходный корпус, доступные локальные browser/Docker runtime.
- Produces: проверяемые baseline/after результаты и завершённый plan перед integration gate. Отсутствующий Docker/browser не считать успешной проверкой: оставить соответствующий checkbox открытым и сообщить ограничение.

- [x] **Step 1: Проверить сохранность содержимого и публичных идентификаторов.**

```bash
.venv/bin/python scripts/check_diagnostic_articles.py
.venv/bin/python scripts/acc_diagnostics.py generate --check
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check
.venv/bin/python -m unittest tests.test_diagnostic_standard_links tests.test_diagnostics_registry_js tests.test_generate_ai_artifacts tests.test_diagnostic_articles -v
git diff --exit-code main -- docs data/diagnostic-sources.json
```

Для всего исходного `docs/**/*.md` выполнить два чистых in-memory рендера с
конфигурацией проекта, с расширением и без него. Собирать HTMLParser-проекцию:
порядок `(tag, attrs)` для `h1..h6`, `a`, `pre`, `code`, code-wrapper с `highlight`
или `mermaid`; отдельно текст каждого `code` внутри `pre` и нормализованный
видимый текст. Сравнить порядок/ID/href/classes/атрибуты, не общий HTML целиком:
абзацы вокруг fences должны измениться. Whitespace внутри кода НЕ нормализовать.
Для исходно валидных страниц дополнительно требовать полное равенство HTML.

Пример нормализации только обычного текста:

```python
def ordinary_text_key(text: str) -> str:
    return ' '.join(text.split())

def attributes_key(attrs):
    return tuple(sorted((name, value) for name, value in attrs))
```

Code-copy oracle для compact fixtures — корректно отделённый reference из
Task 2, поскольку сломанная HTML-структура сама по себе не задаёт правильное
браузерное копирование. Проверить совпадение sidecars/AI files с pre-change
baseline или отсутствие tracked diff после генераторов; не менять их источник
на нормализованную копию.

- [x] **Step 2: Проверить локальный serve и повторный рендеринг без правки статьи.**

```bash
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh serve --dev-addr=127.0.0.1:8769
```

Перед запуском убедиться, что порт свободен; завершать только запущенный нами
процесс. Проверить response body страницы #35 новым `check_html`, а не HTTP 200.
Для повторного рендеринга изменить только mtime файла через `touch`
`docs/diagnostics/bslls/SetPrivilegedMode.md`, дождаться сообщения watcher о
пересборке, проверить заново и подтвердить неизменность SHA-256 содержимого.
Вторая сборка должна работать без перезапуска serve и ручного запуска checker
как «исправителя». Завершить preview и восстановить полную strict build для
последующих проверок; `touch` не меняет content/hash и не создаёт Git diff.

- [x] **Step 3: Проверить реальный Docker import и render, без MCP запуска.**

```bash
docker build -f docker-compose/docker/Dockerfile -t v8std-markdown-check:issue35 .
docker run --rm --entrypoint python -v "$PWD:/docs:ro" -w /docs v8std-markdown-check:issue35 -c 'from zensical.config import parse_config; from markdown import Markdown; from scripts.check_article_html import check_html; c=parse_config("zensical.toml"); m=Markdown(extensions=c["markdown_extensions"], extension_configs=c["mdx_configs"]); s="До\n```bsl\nx = 1;\n```\nПосле"; h=m.convert(s); n,e=check_html("<article class=\"md-content__inner md-typeset\">"+h+"</article>"); assert n == 1 and not e, e'
docker run --rm --entrypoint python -e PYTHONPATH=/opt/v8std -w /tmp v8std-markdown-check:issue35 -c 'import scripts.v8std_markdown as m; print(m.__file__)'
```

Сохранить версии Markdown/PyMdown внутри собранного образа и результаты.
Docker build использует существующий install script; не закреплять новые
версии в рамках исправления. Несовместимость установленного runtime нельзя
считать зелёным import-тестом только на host. Не запускать `docker compose up`,
не менять production и не публиковать образ. Локальный проверочный образ можно
оставить с сообщением о его имени; не удалять другие Docker ресурсы.

- [x] **Step 4: Пройти браузерную матрицу с измерениями и визуальной проверкой.**

Отдавать локальную свежую сборку, например
`.venv/bin/python -m http.server 8769 --bind 127.0.0.1 --directory site`.
Проверить следующие адреса: `/diagnostics/bslls/SetPrivilegedMode/`, тот же адрес
с `?h=привилеги#setprivilegedmode`, `/std/640/`, `/std/643/`, `/std/686/`,
`/std/726/`, `/lang/`; для EDT взять страницу из фактического baseline Task 1
и записать точный URL в evidence. Не угадывать slug диагностики.

Матрица каждой страницы: ширины **390, 768, 1024, 1920 px**; светлая и
тёмная темы при включённом JavaScript, а без JavaScript — читаемость и ссылки
в существующем светлом представлении сайта. Это 108 обязательных сочетаний
для девяти проверенных адресов. Сохранять screenshot и ширины; измерять:

Уточнение 10 сентября согласовано пользователем после разбора ошибки плана:
«обе темы и работа без JavaScript» не требует добавлять отсутствующую тёмную
тему без JS. Прежние дополнительные 36 измерений с dark OS preference без JS
сохраняются как свидетельство фактической светлой загрузки, а не как проверка
тёмной темы. CSS, шаблоны и принятый design не меняются.

```javascript
const article = document.querySelector('article.md-content__inner.md-typeset');
const style = getComputedStyle(article);
({
  viewport: innerWidth,
  pageWidth: document.documentElement.scrollWidth,
  articleWidth: article.getBoundingClientRect().width,
  display: style.display,
  columns: style.gridTemplateColumns,
  directText: [...article.childNodes].filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim()).length,
  code: [...article.querySelectorAll('pre code')].map(n => n.textContent)
});
```

Ожидается отсутствие нулевой основной колонки при `display=grid`, отсутствие
горизонтального переполнения всей страницы из-за исправляемой структуры и
сохранность текста/кода. Для длинного кода прокрутка внутри code block.
Проверить переход по существующему якорю, подсветку `h`, ссылку diagnostic chip
клавиатурой и реальное копирование кнопкой кода в браузерный clipboard;
сравнить с reference, не только с наличием кнопки. Без JS проверить чтение и
ссылки; не требовать работающей JS-кнопки copy при отключённом JS.

Проверяется отсутствие регрессии от нормализации, а не исправление всех
существующих особенностей темы. Прежнее переполнение шапки фиксировать с
before/after доказательством, не скрывая измерения. Для Mermaid сохранить
HTML и исходный текст диаграммы; отсутствие code-copy control не подменять
проверкой обычного блока кода. Исправление существующего JS-renderer Mermaid
не входит в #35, одинаковый результат compact/reference не доказывает SVG.

- [x] **Step 5: Выполнить полные gates и записать только подтверждённые результаты.**

```bash
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main
.venv/bin/python -m unittest tests.test_v8std_markdown tests.test_article_html -v
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
.venv/bin/python scripts/check_article_html.py --site site
git diff --check
git status --short
```

Если тестовые Git fixtures упираются в GPG prompt, допустим только
process-scoped повтор suite с `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign
GIT_CONFIG_VALUE_0=false`; не менять постоянный Git config и не отключать
подпись продуктовых коммитов.

В evidence записать base SHA и хеш проверяемого diff до финального commit,
а проверенный integration SHA сообщить в итоговом handoff. Не пытаться вписать
SHA самого финального commit внутрь включённого в него файла. Также записать версии окружений,
baseline/after counts, команды и exit codes, source/semantic сравнение,
serve initial/rebuild, Docker и browser matrix. Не отмечать шаги по наличию
текста плана. Завершить checkboxes лишь после всех доказательств; процессные
гейты не заменяют исправление HTML и не доказывают состояние публичного сайта.

## Integration after plan completion

Текущий результат исполнения: [верификация 9 сентября](../operations/2026-09-09-markdown-rendering-verification.md).
Steps 1–5 Task 4 подтверждены фактическими результатами; ошибочная трактовка
матрицы исправлена по согласованию 10 сентября. Прежнее переполнение шапки и
неподтверждённый Mermaid SVG записаны как наблюдения вне исправления #35,
а не объявлены исправленными. Свежие fitness, полный suite и strict build
пройдены 10 сентября. Итоговое общее review завершено: единственное замечание
Setext исправлено и проверено отдельным scoped review. После исправления
пройдены 342 теста полного suite, 63 fitness-проверки, strict build и реальный
Docker import/render. Остался integration gate и локальный merge.

Commit/merge/push/deploy не являются checkbox-задачами. Следовать repo policy,
которая имеет приоритет над generic рекомендацией skill делать commit в каждом
шаге. Незавершённый candidate plan можно сохранять в feature-ветке, но нельзя
сливать в `main` и замораживать как завершённую реализацию.

После завершения всех шагов вручную повторить semantic impact по полному diff:
затронуты `ARTICLE_HTML@1.0`, инвариант сохранности и build/serve; прежний chip
contract сохранён, CSS/source/MCP не менялись. Проверить все изменённые пути,
включая не перечисленные CLI `impact`. При новом влиянии остановиться.

```bash
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready
git diff --check
```

Только после всех gates — подписанный commit файлов задачи и локальный merge
feature-ветки в `main` (fast-forward, если база не изменилась). Проверить чистое
состояние и вычисленные `IMPLEMENTED` для четырёх целей plan. При изменившейся
базе повторно проверить интегрированный результат, не объединять вслепую.

Push требует нового явного запроса и автоматически публикует сайт. После
разрешённой публикации нужен отдельный публичный post-check #35, до этого issue
не закрывать. MCP deployment не входит в данное исправление ни при каких
результатах site build.

## Самопроверка плана при авторинге

Покрытие: рендеринг/код/контекст/идемпотентность — Task 2; структура и ошибки
всего корпуса — Task 1; общий build/serve и импорт — Task 3 и Task 4 Steps 2–3;
source/AI/chips/ID/copy/browser — Task 4. Новые требования или отмена старых
документов не вводятся. Интерфейсы parser/CLI/extension согласованы между задачами.
Все checkboxes на момент авторинга открыты: это план, а не свидетельство исправления.
При авторинге пройдены обычная архитектурная валидация, 13 тестов repository/process,
синтаксический разбор Python/Bash/TOML примеров и проверка относительных ссылок.
Это не запуск будущей реализации. `validate --merge-ready` ожидаемо возвращает
только `INCOMPLETE_PLAN`; обходить этот gate или ставить checkboxes заранее нельзя.
