###### bslls:UnusedLocalMethod

# Неиспользуемый локальный метод (UnusedLocalMethod)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `suspicious`, `unused`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnusedLocalMethod.md
source_path=docs/diagnostics/UnusedLocalMethod.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=0db96fe0b6394aeca9080222865243c06cf09dddadca1f967e2514cc26112f37
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Программные модули не должны иметь неиспользуемых процедур и функций. Диагностика умеет пропускать `подключаемые методы`, имеющие префиксы, указанные в параметре диагностики.

## Источники

* [Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:456:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std456: Тексты модулей](../../std/456.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnusedLocalMethod.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
