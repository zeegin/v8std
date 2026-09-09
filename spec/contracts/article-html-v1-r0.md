---
schema_version: 1
kind: contract
id: ARTICLE_HTML
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:markdown-fence-rendering
producer: Zensical Markdown renderer
consumers:
  - site stylesheets
  - browser HTML parser
  - accessibility tools
  - search highlighting and code-copy controls
requirements:
  - MARKDOWN_FENCES_ARE_RENDERED_AS_BLOCKS
  - ARTICLE_HTML_REJECTS_LAYOUT_BREAKING_STRUCTURE
  - MARKDOWN_BUILD_AND_SERVE_SHARE_RENDERING
governs:
  - scripts/v8std_markdown.py
  - scripts/check_article_html.py
  - scripts/zensical_docs.sh
  - zensical.toml
  - overrides/
  - docs/assets/stylesheets/extra.css
conformance:
  module: tests.test_article_html
  command: .venv/bin/python -m unittest tests.test_article_html -v
required_when: implemented
supersedes: []
deprecates: []
---

# HTML статьи, версия 1.0

## Область

Контракт относится к HTML внутри `article.md-content__inner.md-typeset`,
который renderer передаёт браузеру. Проверяется исходный сериализованный
HTML: автоматическое исправление браузером не считается соответствием.
Это не полный валидатор всех HTML-стандартов и не новый Markdown API.

## Структура и совместимость

Fenced-блоки кода расположены вне `p`. В абзацах нет элементов, запрещённых
paragraph/phrasing-содержимым, включая `div`, `pre`, списки, таблицы,
блочные цитаты, заголовки и секционные контейнеры. Проверка должна учитывать
структуру HTML и raw-text/комментарии, а не искать эти слова внутри кода.

Для статьи с непосредственным `h6`, к которой применяется существующая
двухколоночная CSS-раскладка, непосредственные непустые текстовые узлы
запрещены. Такой текст должен находиться в корректном элементе-контейнере.
Пробелы и комментарии допустимы. Содержимое не скрывается и не переносится
в другую смысловую секцию для прохождения проверки.

Порядок текста, заголовков и блоков кода, их ID и anchors, href, атрибуты
кодовых блоков, классы и семантика diagnostic chips сохраняются. Новые
обёртки абзацев исправляют структуру без изменения публичных URL и ссылок.
CSS и шаблоны входят в `governs` как потребители контракта; их изменение не
входит в scope этого исправления.

## Проверка и ошибки

Планируемый CLI `scripts/check_article_html.py --site site` обходит все
HTML-страницы сборки и сообщает относительный путь, строку/позицию и тип
нарушения; возвращает ненулевой код при нарушении или ошибке чтения.
Отсутствующий каталог или отсутствие проверяемых статей не дают ложный успех.
Проверка read-only и не «ремонтирует» выходные файлы.

Сначала используются fixtures ошибочной и корректной структуры, затем
свежий полный HTML-корпус. Успех `build --strict` включает этот gate.
Один и тот же renderer используется в `serve`, включая повторную генерацию;
gate публикации не заменяется проверкой предпросмотра или статусом HTTP 200.

Настоящая ревизия не отменяет `DIAGNOSTIC_CHIP_MARKUP@1.0` и не меняет MCP.
Conformance module появится при реализации; до этого контракт фиксирует
намерение и не должен представляться как уже выполняемое свойство сайта.
