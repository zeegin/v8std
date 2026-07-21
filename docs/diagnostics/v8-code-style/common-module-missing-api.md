###### v8cs:common-module-missing-api

# Общий модуль должен иметь хотя бы один экспортный метод (common-module-missing-api)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-missing-api.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-missing-api.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=7cf6f2286949fca0ee627229e4312f34426313369e9a8d5bab523f5ef6ebec56
-->

Общий модуль должен иметь программный интерфейс.

## Неправильно

```bsl

Процедура Тест()
    //TODO
КонецПроцедуры

```

## Правильно

```bsl

#Область СлужебныйПрограммныйИнтерфейс

Процедура Тест() Экспорт
    //TODO
КонецПроцедуры

#КонецОбласти

```

## См.

- [Структура модуля](https://its.1c.ru/db/v8std/content/455/hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-missing-api.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
