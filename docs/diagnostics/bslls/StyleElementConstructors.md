###### bslls:StyleElementConstructors

# Конструктор элемента стиля (StyleElementConstructors)

- Тип: Ошибка
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/StyleElementConstructors.md
source_path=docs/diagnostics/StyleElementConstructors.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=8dd21d7c011ec53980b3a27f573c8785bd2db9b4603561775cc526afd80aac74
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
Для изменения оформления следует использовать элементы стиля, а не задавать конкретные значения непосредственно в элементах управления. Это требуется для того, чтобы аналогичные элементы управления выглядели одинаково во всех формах, где они встречаются.

Виды элементов стиля:

* `Цвет` - задается значение RGB
* `Шрифт` - задаются вид, размер и начертание
* `Рамка` - задаются тип и ширина границ

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

## Источники
Система стандартов
* Источник: [Стандарт: Элементы стиля](https://its.1c.ru/db/v8std#content:667:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std667, п. 1: Элементы стиля](../../std/667.md#1) — Диагностика «Конструктор элемента стиля (StyleElementConstructors)» проверяет условие пункта 1 стандарта std667.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/StyleElementConstructors.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
