###### bslls:LineLength

# Ограничение на длину строки (LineLength)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/LineLength.md
source_path=docs/diagnostics/LineLength.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=8e118458212887ef7f592c8c03a2e54d6aef3c587d3460cf6c292ed3a495a0ce
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

При длине строки более 120 символов следует использовать переносы. Строки длиннее 120 символов делать не рекомендуется, за исключением тех случаев, когда перенос невозможен (например, в коде определена длинная строковая константа, которая выводится без переносов в окно сообщений с помощью объекта СообщениеПользователю).

## Источники

* [Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:456:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std456: Тексты модулей](../../std/456.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/LineLength.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
