###### bslls:MissingVariablesDescription

# Все объявления переменных должны иметь описание (MissingVariablesDescription)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MissingVariablesDescription.md
source_path=docs/diagnostics/MissingVariablesDescription.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=c44d721a1be1f1d259c600a05bb985e490f6657a98ed6c243857946058616df2
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->
Все переменные модулей, а также все экспортируемые переменные должны иметь комментарии.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

Неправильно:

```bsl
Перем Контекст;
```

Правильно:

```bsl
Перем Контекст; // Некое подробное описание, которое объясняет назначение переменной

// Некое подробное описание, которое объясняет назначение переменной
Перем Контекст;
```

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->

* Источник: [Соглашения при написания кода. Структура модуля](https://its.1c.ru/db/v8std#content:455:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std455, п. 2.2: Структура модуля](../../std/455.md#22) — Диагностика «Все объявления переменных должны иметь описание (MissingVariablesDescription)» проверяет условие пункта 2.2 стандарта std455.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MissingVariablesDescription.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
