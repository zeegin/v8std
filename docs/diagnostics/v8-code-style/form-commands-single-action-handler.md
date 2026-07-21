###### v8cs:form-commands-single-action-handler

# У каждого действия команды должна быть назначена своя процедура-обработчик (form-commands-single-action-handler)

- Категория: `form`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/form-commands-single-action-handler.md
source_path=bundles/com.e1c.v8codestyle.form/markdown/ru/form-commands-single-action-handler.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=dc6c7f262fa1aadcd6db3832a3434bb8bfcf6a02e40042d0cbdafd9b4e156a15
-->

У каждого действия команды должна быть назначена своя процедура-обработчик.

## Неправильно

Смешение нескольких событий в одной процедуре неоправданно усложняет ее логику и снижает ее стабильность
(вместо одного предусмотренного вызова по событию из платформы код процедуры должен рассчитывать и на другие вызовы).

## Правильно

У каждого события должна быть назначена своя процедура-обработчик.
Если одинаковые действия должны выполняться при возникновении событий в разных командах формы, следует:
- создать отдельную процедуру (функцию), выполняющую необходимые действия
- для каждого элемента формы создать отдельный обработчик с именем, назначаемым по умолчанию
- из каждого обработчика вызвать требуемую процедуру (функцию).

## См.

[Структура модуля](https://its.1c.ru/db/v8std/content/455/hdoc#2.4.3)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/form-commands-single-action-handler.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
