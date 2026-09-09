---
schema_version: 1
kind: adr
id: NORMALIZE_FENCES_AT_RENDER_BOUNDARY
scope: product
design: design:markdown-fence-rendering
requirements:
  - MARKDOWN_FENCES_ARE_RENDERED_AS_BLOCKS
  - MARKDOWN_RENDERING_PRESERVES_SOURCE_CORPUS
  - MARKDOWN_RENDERING_PRESERVES_CODE_AND_CONTEXT
  - ARTICLE_HTML_REJECTS_LAYOUT_BREAKING_STRUCTURE
  - MARKDOWN_BUILD_AND_SERVE_SHARE_RENDERING
aliases: []
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MARKDOWN_RENDERING_PRESERVES_SOURCE_AND_CODE
  preserves: []
  replaces: {}
  cancels: []
contracts:
  introduces:
    - contract:ARTICLE_HTML@1.0
  preserves:
    - contract:DIAGNOSTIC_CHIP_MARKUP@1.0
  replaces: {}
  cancels: []
---

# Нормализовать границы fenced-блоков при рендеринге

## Входные требования

Требования рендеринга блоков, сохранности исходников и кода, HTML-проверки
и единого поведения `build`/`serve` введены в
`design:markdown-fence-rendering` и перечислены в front matter.

## Решение

Использовать общее Markdown-расширение в pipeline Zensical, которое отделяет
распознанные fenced-блоки от соседнего текста в рабочем представлении
документа. Сохранить исходный корпус, код, CSS и публичные идентификаторы.
Проверять структурную пригодность полученного HTML до публикации.

Issue #35 возникает при сочетании отсутствующих разделителей SuperFences и
grid-раскладки статьи. Нормализация на границе рендеринга устраняет создание
блочного HTML внутри абзаца, работает до исполнения JavaScript и применяется
как при `build`, так и при `serve`.

Заимствованные статьи имеют проверяемые хеши. Их ручное редактирование ради
синтаксических требований конкретного renderer смешало бы исходный корпус с
его HTML-представлением и потребовало бы сопровождения при синхронизациях.

## Влияние на инварианты

Вводится `MARKDOWN_RENDERING_PRESERVES_SOURCE_AND_CODE`: рендеринг не меняет
файлы исходного корпуса, provenance и содержимое кода. Существующие
инварианты не отменяются и не заменяются.

## Влияние на контракты

Вводится `ARTICLE_HTML@1.0` для границы renderer/CSS/browser.
`DIAGNOSTIC_CHIP_MARKUP@1.0` сохраняется без изменения ссылок, обязательных
классов и доступности. MCP-контракты не затронуты.

Появляется небольшой адаптер между исходным Markdown и существующим renderer.
Он не является универсальным исправителем Markdown/HTML. Если вход нельзя
корректно обработать без изменения смысла, нельзя скрывать нарушение,
удалять текст или ослаблять HTML gate: требуется воспроизведение и пересмотр
решения. Принятие ADR не означает, что расширение и проверки уже реализованы.

## Отклонённые альтернативы

- Добавлять пустые строки непосредственно в статьи: затрагивает проверяемые
  source blocks и возвращает задачу при следующем импорте.
- Ограничить ширину колонки или отказаться от CSS Grid: оставляет некорректный
  HTML и меняет визуальный контракт всех стандартов.
- Переписывать DOM в браузере либо HTML после сборки: создаёт отдельный путь
  исправления и риск различий между первой загрузкой, `build` и `serve`.
- Обновить renderer и сопутствующие библиотеки: расширяет область регрессий;
  подтверждённого исправления в иной версии нет в основании этого решения.
