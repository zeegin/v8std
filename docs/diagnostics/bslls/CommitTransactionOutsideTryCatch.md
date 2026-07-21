###### bslls:CommitTransactionOutsideTryCatch

# Нарушение правил работы с транзакциями для метода 'ЗафиксироватьТранзакцию' (CommitTransactionOutsideTryCatch)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommitTransactionOutsideTryCatch.md
source_path=docs/diagnostics/CommitTransactionOutsideTryCatch.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=fab3a32cb0e6b4f30b1e512d3bf6aae3b03e6852a40d84e6fb3450c4be5e4de6
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Метод ЗафиксироватьТранзакцию должен идти последним в блоке Попытка перед оператором Исключение, чтобы  гарантировать, что после ЗафиксироватьТранзакцию не возникнет исключение.

## Источники

* [Транзакции: правила использования](https://its.1c.ru/db/v8std/content/783/hdoc/_top/)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommitTransactionOutsideTryCatch.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
