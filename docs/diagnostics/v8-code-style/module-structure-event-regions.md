###### v8cs:module-structure-event-regions

# Раздел «Обработчики событий» содержит только методы являющиеся обработчиками событий (module-structure-event-regions)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-event-regions.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-event-regions.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=a8134fa610b5009571e969752fdcd7647f31584206487c65a3fc7696e2bed071
-->

Проверяет регион обработчиков событий на методов относящихся только к обработчикам

## Неправильно

```bsl

#Область ОбработчикиСобытий

Процедура Тест()
КонецПроцедуры

#КонецОбласти

```

## Правильно

```bsl

#Область ОбработчикиСобытий

Процедура ОбработкаПолученияФормы(ВидФормы, Параметры, ВыбраннаяФорма, ДополнительнаяИнформация, СтандартнаяОбработка)
КонецПроцедуры

#КонецОбласти

```

## См.


- [Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std455: Структура модуля](../../std/455.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-event-regions.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
