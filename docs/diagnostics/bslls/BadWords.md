###### bslls:BadWords

# Запрещенные слова (BadWords)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Нет
- Теги: `design`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/BadWords.md
source_path=docs/diagnostics/BadWords.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=fea0a412121f8259c7d3ab3c83d8600917c5c682dd372d054fc08a86a3c94971
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
В тексте модулей не должны встречаться запрещенные слова.
Список запрещенных слов задается регулярным выражением.
Поиск производится без учета регистра символов.

**Примеры настройки:**

"редиска|лопух|экзистенциальность"

"ло(х|шара|шпед)"

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/BadWords.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
