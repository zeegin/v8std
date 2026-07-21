###### v8cs:module-region-empty

# Область пустая (module-region-empty)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-region-empty.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-region-empty.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=4b8d5a258b3ad724febb6ba901b982a91d29d4f989a3f06e01e173f3777317ea
-->

Проверяет что область модуля пустая

## Неправильно

```bsl
#Область ОписаниеПеременных

// объявление переменных

#КонецОбласти

```

## Правильно

```bsl
#Область ОписаниеПеременных

Перем ВалютаУчета;
Перем АдресПоддержки;
...

#КонецОбласти
```

## См.


- [Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc:1.8)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std455, п. 1.8: Структура модуля](../../std/455.md#18) — Диагностика v8cs:module-region-empty проверяет требование пункта 1.8 стандарта std455.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-region-empty.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
