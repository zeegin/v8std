###### v8cs:module-structure-form-event-regions

# Проверяет регион обработчиков событий формы (module-structure-form-event-regions)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-form-event-regions.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-form-event-regions.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=7ae87835ab42a94138673a1156b796dc050b03a023c56054a633b3a9a2bea651
-->

Раздел «Обработчики событий формы» содержит процедуры-обработчики событий формы: ПриСозданииНаСервере, ПриОткрытии и т.п.
Раздел «Обработчики событий элементов шапки формы» содержит процедуры-обработчики элементов,
расположенных в основной части формы (все, что не связано с таблицами на форме).
В разделах «Обработчики событий элементов таблицы формы <имя таблицы формы>» размещаются процедуры-обработчики
таблиц формы и элементов таблиц. Для процедур-обработчиков каждой таблицы должен быть создан свой раздел.
Раздел «Обработчики команд формы» содержит процедуры-обработчики команд формы (имена которых задаются
в свойстве Действие команд формы).

## Неправильно

```bsl

#Область ОбработчикиСобытийФормы

Процедура ОшибочноРасположенныйМетод()
КонецПроцедуры

#КонецОбласти

```

## Правильно

```bsl

#Область ОбработчикиСобытийФормы

Процедура ПриОткрытии(Отмена)
КонецПроцедуры

#КонецОбласти

```

## См.


- [Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std455, п. 1.6: Структура модуля](../../std/455.md#16) — Диагностика v8cs:module-structure-form-event-regions проверяет требование пункта 1.6 стандарта std455.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-structure-form-event-regions.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
