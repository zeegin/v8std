###### bslls:BeginTransactionBeforeTryCatch

# Нарушение правил работы с транзакциями для метода 'НачатьТранзакцию' (BeginTransactionBeforeTryCatch)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/BeginTransactionBeforeTryCatch.md
source_path=docs/diagnostics/BeginTransactionBeforeTryCatch.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=553de1f47a9804ff02f6831ee11931d3b1e6d0f8ce7cf4f9e126880d5b74bea9
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Метод НачатьТранзакцию должен быть за пределами блока Попытка-Исключение непосредственно перед оператором Попытка;

## Источники

+ [Транзакции: правила использования](https://its.1c.ru/db/v8std/content/783/hdoc/_top/)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) — Диагностика «Нарушение правил работы с транзакциями для метода 'НачатьТранзакцию' (BeginTransactionBeforeTryCatch)» проверяет условие пункта 1.3 стандарта std783.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/BeginTransactionBeforeTryCatch.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
