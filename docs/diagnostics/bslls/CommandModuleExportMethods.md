###### bslls:CommandModuleExportMethods

# Экспортные методы в модулях команд и общих команд (CommandModuleExportMethods)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `standard`, `clumsy`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommandModuleExportMethods.md
source_path=docs/diagnostics/CommandModuleExportMethods.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=c84a64a3c1767ae76e934aea18fcd2f8fb9bb374658188773d9ccb5b7260ce48
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Не следует размещать экспортные методы в модулях команд и общих команд. К этим модулям нет возможности
обращаться из внешнего по отношению к ним кода, поэтому экспортные методы в этих модулях не имеют смысла.

## Источники

* [Источник](https://its.1c.ru/db/v8std/content/544/hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std544: Ограничения на использование экспортных процедур и функций](../../std/544.md#std544) — Диагностика «Экспортные методы в модулях команд и общих команд (CommandModuleExportMethods)» проверяет требование всего std544; стандарт не имеет нумерованных пунктов.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommandModuleExportMethods.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
