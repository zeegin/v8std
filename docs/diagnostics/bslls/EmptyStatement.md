###### bslls:EmptyStatement

# Пустой оператор (EmptyStatement)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/EmptyStatement.md
source_path=docs/diagnostics/EmptyStatement.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=ed4a3ddeb0f80b6c135fd89a7ea1c3f8997a1bc529381159571534d278c088aa
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Пустой оператор - это оператор, состоящий только из точки с запятой (";"). Появляется он в обычно

- при рефакторинге, когда разработчик удалил часть кода, но забыл удалить последнюю ";"
- при "копипасте", когда разработчик вставил скопированный код, содержащий конечный символ ";"
- при невнимательности, когда разработчик дважды (а то и больше) раз напечатал символ ";"

Пустой оператор не приводит к ошибкам работы кода, но захламляет его, снижая восприятие.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/EmptyStatement.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
