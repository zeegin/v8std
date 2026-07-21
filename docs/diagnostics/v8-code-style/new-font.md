###### v8cs:new-font

# Использование конструкции "Новый Шрифт" (new-font)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/new-font.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/new-font.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=7dab3738a84ed69a9169bff0db3242b61f70a2e0c8476c53402fdc622c9ab725
-->

Для изменения оформления следует использовать элементы стиля, а не
задавать конкретные значения непосредственно в элементах управления.

## Неправильно

```bsl
Шрифт = Новый Шрифт(, 1, Истина, Истина, Истина, Истина, 100); ...
```

## Правильно

```bsl
Шрифт = ШрифтСтиля.<Имя элемента стиля>; ...
```

Это требуется для того, чтобы аналогичные элементы управления выглядели
одинаково во всех формах, где они встречаются.

## См.

- [Элементы стиля](https://its.1c.ru/db/v8std#content:667:hdoc:1)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std667: Элементы стиля](../../std/667.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/new-font.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
