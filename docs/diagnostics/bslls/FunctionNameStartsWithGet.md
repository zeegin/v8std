###### bslls:FunctionNameStartsWithGet

# Имя функции не должно начинаться с "Получить" (FunctionNameStartsWithGet)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Нет
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/FunctionNameStartsWithGet.md
source_path=docs/diagnostics/FunctionNameStartsWithGet.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=d02b67fa9ee54bcdc55afad6fc7d4c37e910d23148cb5c5c2125a06e8b3f1732
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

В имени функции слово получить лишнее т.к. функция по определению возвращает значение.

## Примеры
```bsl
// Не правильно:
Функция ПолучитьИмяПоКоду()

// Правильно:
Функция ИмяПоКоду()
```


## Источники
* Источник: [Стандарт: Имена процедур и функций п 6.1](https://its.1c.ru/db/v8std#content:647:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std647, п. 6.1: Имена процедур и функций](../../std/647.md#61) — Диагностика «Имя функции не должно начинаться с "Получить" (FunctionNameStartsWithGet)» проверяет условие пункта 6.1 стандарта std647.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/FunctionNameStartsWithGet.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
