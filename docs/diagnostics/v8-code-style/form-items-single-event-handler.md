###### v8cs:form-items-single-event-handler

# У каждого события должна быть назначена своя процедура-обработчик (form-items-single-event-handler)

- Категория: `form`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/form-items-single-event-handler.md
source_path=bundles/com.e1c.v8codestyle.form/markdown/ru/form-items-single-event-handler.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=aff02a3bbb106f1619fe5009a81775b3fd9db64017dceaffb074a3d0793b342c
-->

У каждого события должна быть назначена своя процедура-обработчик

## Неправильно

Смешение нескольких событий в одной процедуре неоправданно усложняет ее логику и снижает ее устойчивость (вместо одного предусмотренного вызова - по событию из платформы - код процедуры должен рассчитывать и на другие вызовы)

## Правильно

У каждого события должна быть назначена своя процедура-обработчик.
Если одинаковые действия должны выполняться при возникновении событий в разных элементах формы, следует:
- создать отдельную процедуру (функцию), выполняющую необходимые действия
- для каждого элемента формы создать отдельный обработчик с именем, назначаемым по умолчанию
- из каждого обработчика вызвать требуемую процедуру (функцию).

## См.

[Структура модуля](https://its.1c.ru/db/v8std/content/455/hdoc#2.4.3)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std455, п. 2.4.3: Структура модуля](../../std/455.md#243) — Диагностика v8cs:form-items-single-event-handler проверяет требование пункта 2.4.3 стандарта std455.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/form-items-single-event-handler.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
