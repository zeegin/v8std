###### v8cs:db-object-anyref-type

# Реквизиты составного типа, такие как ЛюбаяСсылка и аналогичные (db-object-anyref-type)

- Категория: `md`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-anyref-type.md
source_path=bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-anyref-type.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=3bd6962ebfa9873996dc1193a2bb3d51f18176bd53b83035fdad2e29637deacc
-->

Для типизированных объектов метаданных, хранящихся в информационной базе, не следует использовать составные типы
ЛюбаяСсылка, СправочникСсылка, ДокументСсылка и аналогичные. Состав типов того или иного типизированного объекта
должен определяться явным образом.


## Неправильно

## Правильно

## См.

[Ограничения на использование реквизитов составного типа](https://its.1c.ru/db/v8std#content:728:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std728, п. 2.1: Ограничения на использование реквизитов составного типа](../../std/728.md#21) — Диагностика v8cs:db-object-anyref-type проверяет требование пункта 2.1 стандарта std728.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-anyref-type.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
