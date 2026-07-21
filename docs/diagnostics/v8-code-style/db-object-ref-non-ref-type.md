###### v8cs:db-object-ref-non-ref-type

# Реквизиты составного типа (db-object-ref-non-ref-type)

- Категория: `md`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-ref-non-ref-type.md
source_path=bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-ref-non-ref-type.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=99c106ddcac39ba868d230d630d809c2c2604cdf9c5837e3c5ad20915b678d69
-->

Реквизиты составного типа, используемые в условиях соединений, отборах, а также для упорядочивания, должны содержать
только ссылочные типы (СправочникСсылка.…, ДокументСсылка.… и пр.).
В состав их типов не рекомендуется включать никаких других нессылочных типов, например: Строка, Число, Дата,
УникальныйИдентификатор, Булево, а также ХранилищеЗначения.


## Неправильно

## Правильно

## См.

[Ограничения на использование реквизитов составного типа](https://its.1c.ru/db/v8std#content:728:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std728, п. 1.1: Ограничения на использование реквизитов составного типа](../../std/728.md#11) — Диагностика v8cs:db-object-ref-non-ref-type проверяет требование пункта 1.1 стандарта std728.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-ref-non-ref-type.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
