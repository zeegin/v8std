###### bslls:ConsecutiveEmptyLines

# Подряд идущие пустые строки (ConsecutiveEmptyLines)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ConsecutiveEmptyLines.md
source_path=docs/diagnostics/ConsecutiveEmptyLines.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=67f1111924b43d07f27eff661ad802e5f326fbac241db49c3012a012c32d3101
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Для разделения блоков кода между собой используется вставка пустой строки.

Вставка 2-х и более пустых строк не несет данной ценности и приводит к бессмысленному увеличению длины метода или модуля.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ConsecutiveEmptyLines.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
