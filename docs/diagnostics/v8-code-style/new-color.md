###### v8cs:new-color

# Использование конструкции "Новый Цвет" (new-color)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/new-color.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/new-color.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=a3b53c528c63e88428848f626321a139ec32a939fe510638e0673bb0a914477b
-->

Для изменения оформления следует использовать элементы стиля, а не
задавать конкретные значения непосредственно в элементах управления.

## Неправильно

```bsl
Цвет = Новый Цвет(0,0,0); ...
```

## Правильно

```bsl
Цвет = ЦветаСтиля.<Имя элемента стиля>; ...
```

Это требуется для того, чтобы аналогичные элементы управления выглядели
одинаково во всех формах, где они встречаются.

## См.

- [Элементы стиля](https://its.1c.ru/db/v8std#content:667:hdoc:1)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std667, п. 1: Элементы стиля](../../std/667.md#1) — Диагностика v8cs:new-color проверяет требование пункта 1 стандарта std667.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/new-color.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
