###### v8cs:module-structure-init-code-in-region

# Раздел инициализации содержит код инициализации (module-structure-init-code-in-region)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-init-code-in-region.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-init-code-in-region.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=a05bc12b757ec82483ed37897e28bf0569287b8f35d98725b9264d8b62541f38
-->

Раздел инициализации содержит операторы, инициализирующие переменные модуля или объект (форму).

## Неправильно

```bsl

АдресПоддержки = "v8@1c.ru";
ВыполнитьИнициализацию();
...

```

## Правильно

```bsl

#Область Инициализация

АдресПоддержки = "v8@1c.ru";
ВыполнитьИнициализацию();
...

#КонецОбласти

```

## См.


- [Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std455: Структура модуля](../../std/455.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-init-code-in-region.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
