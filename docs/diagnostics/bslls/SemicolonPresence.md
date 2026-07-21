###### bslls:SemicolonPresence

# Выражение должно заканчиваться символом ";" (SemicolonPresence)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SemicolonPresence.md
source_path=docs/diagnostics/SemicolonPresence.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=f3713e8a01233868d25f7f08861602388dc060624625700db17669026ca3540e
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

В текстах программных процедур и функций операторы между собой обязательно стоит разделять точкой с запятой (";"). Конец строки не является признаком конца оператора.
Не смотря на то, что в некоторых случаях платформа позволяет опускать точку с запятой, необходимо указывать этот символ всегда, явно указывая завершение оператора.

**ПРИМЕЧАНИЕ**: Ключевые слова `Процедура`, `КонецПроцедуры`, `Функция`, `КонецФункции` являются не операторами, а операторными скобками, поэтому **НЕ** должны заканчиваться точкой с запятой (это может приводить к ошибкам выполнения модуля).

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SemicolonPresence.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
