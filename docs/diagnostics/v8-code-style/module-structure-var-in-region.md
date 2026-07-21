###### v8cs:module-structure-var-in-region

# Раздел описания переменных (module-structure-var-in-region)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-var-in-region.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-var-in-region.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=645c4e630528224d790b72176eb7279e6ff123bfa67c8ef26e3a2d401572554c
-->

Раздел описания переменных. Имена переменных назначаются согласно общим правилам образования имен переменных,
а их использование описывается в статье Использование глобальных переменных в программных модулях.

Все переменные модуля должны быть снабжены комментарием, достаточным для понимания их назначения.
Комментарий рекомендуется размещать в той же строке, где объявляется переменная.

## Неправильно

```bsl


Перем ВалютаУчета;
Перем АдресПоддержки;
...

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


- [Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std455, п. 1.1: Структура модуля](../../std/455.md#11) — Диагностика v8cs:module-structure-var-in-region проверяет требование пункта 1.1 стандарта std455.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-var-in-region.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
