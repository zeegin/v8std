###### bslls:MetadataObjectNameLength

# Имена объектов метаданных не должны превышать допустимой длины наименования (MetadataObjectNameLength)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MetadataObjectNameLength.md
source_path=docs/diagnostics/MetadataObjectNameLength.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=bbbec01476eba6c93b1032b8393316dfa1eeb312513cc386fe62e599c3fd7149
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Имена объектов метаданных не должны превышать 80 символов.

Кроме проблем с использованием этих объектов возникают проблемы с выгрузкой конфигурации в файлы.

## Примеры

ОченьДлинноеИмяСправочникиКотороеВызываетПроблемыВРаботеАТакжеОшибкиВыгрузкиКонфигурации, LooooooooooooooooooooooooooooooooooooooooooooooooooooooooongVeryLongDocumentName

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->

[Стандарт: Имя, синоним, комментарий](https://its.1c.ru/db/v8std#content:474:hdoc:2.3)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std474, п. 2.3: Имя, синоним, комментарий](../../std/474.md#23) — Диагностика «Имена объектов метаданных не должны превышать допустимой длины наименования (MetadataObjectNameLength)» проверяет условие пункта 2.3 стандарта std474.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MetadataObjectNameLength.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
