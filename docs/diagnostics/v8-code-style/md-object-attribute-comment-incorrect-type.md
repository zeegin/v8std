###### v8cs:md-object-attribute-comment-incorrect-type

# Реквизит «Комментарий» у документов (md-object-attribute-comment-incorrect-type)

- Категория: `md`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/md-object-attribute-comment-incorrect-type.md
source_path=bundles/com.e1c.v8codestyle.md/markdown/ru/md-object-attribute-comment-incorrect-type.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=c6d6720b98861b6b16c88d07e56e34020a9bc5595aedf05504b8755e7513db4a
-->

Для всех документов рекомендуется создавать реквизит Комментарий
(строка неограниченной длины). В этом реквизите пользователи могут
записывать по документу различные заметки служебного характера, которые
не относятся к прикладной специфике документа (например, причина пометки
на удаления и т.п.). Доступ к реквизиту для пользователей должен быть
настроен также как и к самому документу (если документ доступен только
для чтения, то и комментарий – только для чтения; если же есть право
записи документа, то и значение реквизита также можно изменять).

Свойство "Многострочный режим" у реквизита должно быть включено.
быть включено.

## Неправильно

## Правильно

## См.

[Реквизит «Комментарий» у документов](https://its.1c.ru/db/v8std#content:531:hdoc:1)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std531, п. 1: Реквизит «Комментарий» у документов](../../std/531.md#1) — Диагностика v8cs:md-object-attribute-comment-incorrect-type проверяет требование пункта 1 стандарта std531.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/md-object-attribute-comment-incorrect-type.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
