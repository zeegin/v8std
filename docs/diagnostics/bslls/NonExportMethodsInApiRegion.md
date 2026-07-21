###### bslls:NonExportMethodsInApiRegion

# Неэкспортные методы в областях ПрограммныйИнтерфейс и СлужебныйПрограммныйИнтерфейс (NonExportMethodsInApiRegion)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/NonExportMethodsInApiRegion.md
source_path=docs/diagnostics/NonExportMethodsInApiRegion.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=a55f0c3ba38f27aadcc1d970941eef8aa348fae19e34e548aee9c01cdfc33072
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

* Раздел «Программный интерфейс» содержит экспортные процедуры и функции, предназначенные для использования другими объектами конфигурации или другими программами (например, через внешнее соединение).

* Раздел «Служебный программный интерфейс» предназначен для модулей, которые являются частью некоторой функциональной подсистемы. В нем должны быть размещены экспортные процедуры и функции, которые допустимо вызывать только из других функциональных подсистем этой же библиотеки.

## Источники

* [Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std455: Структура модуля](../../std/455.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/NonExportMethodsInApiRegion.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
