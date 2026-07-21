###### bslls:ExtraCommas

# Запятые без указания параметра в конце вызова метода (ExtraCommas)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ExtraCommas.md
source_path=docs/diagnostics/ExtraCommas.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=e41486dfd53e61f43c13d5a498f61de391009236473fd9e3e9b16ae617bf58d1
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Не следует указывать запятую в конце вызова метода без указания параметра. Это затрудняет восприятие и не несет важной информации.
Необязательные параметры попадают под принцип Бритва Оккама "Не следует множить сущности без необходимости", так как "висящая" запятая малоинформативна.

Плохо:

```bsl
Результат = Действие(П1, П2,,);
```

Хорошо:

```bsl
Результат = Действие(П1, П2);
```

## Источники

* [Соглащения о написании кода. Параметры процедур и функций. Пункт 7](https://its.1c.ru/db/v8std#content:640:hdoc).

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std640, п. 7: Параметры процедур и функций](../../std/640.md#7) — Диагностика «Запятые без указания параметра в конце вызова метода (ExtraCommas)» проверяет условие пункта 7 стандарта std640.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ExtraCommas.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
