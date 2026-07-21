###### bslls:OneStatementPerLine

# Одно выражение в одной строке (OneStatementPerLine)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`, `design`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/OneStatementPerLine.md
source_path=docs/diagnostics/OneStatementPerLine.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=e832ebdd0cd151fdb477f8af39b66eedc1660de83900d994ccd5c1e345561b5f
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Тексты модулей оформляются по принципу "один оператор в одной строке". Наличие нескольких операторов допускается только для "однотипных" операторов присваивания, например:

`НачальныйИндекс = 0; Индекс = 0; Результат = 0;`

## Источники

* [Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:456:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std456, п. 4: Тексты модулей](../../std/456.md#4) — Диагностика «Одно выражение в одной строке (OneStatementPerLine)» проверяет условие пункта 4 стандарта std456.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/OneStatementPerLine.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
