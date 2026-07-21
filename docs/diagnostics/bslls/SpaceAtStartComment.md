###### bslls:SpaceAtStartComment

# Пробел в начале комментария (SpaceAtStartComment)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SpaceAtStartComment.md
source_path=docs/diagnostics/SpaceAtStartComment.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=25cfe1533c1b85d068d289beb85933a52c08aff45a5272fd7c070c3588445267
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Между символами комментария "//" и текстом комментария должен быть пробел.

Исключением из правила являются _**комментарии-аннотации**_, т.е. комментарии начинающиеся с определенной последовательности символов.

## Источники

* [Стандарт: Тексты модулей, пункт 7.3](https://its.1c.ru/db/v8std#content:456:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std456, п. 7.3: Тексты модулей](../../std/456.md#73) — Диагностика «Пробел в начале комментария (SpaceAtStartComment)» проверяет условие пункта 7.3 стандарта std456.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SpaceAtStartComment.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
