###### bslls:EmptyRegion

# Область не должна быть пустой (EmptyRegion)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/EmptyRegion.md
source_path=docs/diagnostics/EmptyRegion.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=5fb3b6d8c3918b44fcec9a0a476e9a9f05ff546691917b3793491758f8d8d74b
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
Модуль не должен содержать пустых областей.
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->
```bsl
#Область ПустаяОбласть
#КонецОбласти
```

## Источники

* Источник: [Стандарт: Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std455: Структура модуля](../../std/455.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/EmptyRegion.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
