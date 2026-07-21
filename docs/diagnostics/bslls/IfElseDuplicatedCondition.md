###### bslls:IfElseDuplicatedCondition

# Повторяющиеся условия в синтаксической конструкции Если...Тогда...ИначеЕсли... (IfElseDuplicatedCondition)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `suspicious`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/IfElseDuplicatedCondition.md
source_path=docs/diagnostics/IfElseDuplicatedCondition.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=0a2dda29ee7c83281511f071a606807b3f8c3b8835328a76ea1b5466277d3894
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Синтаксическая конструкция **Если...Тогда...ИначеЕсли...** не должна иметь одинаковых условий.

## Примеры

```bsl
Если п = 0 Тогда
    т = 0;
ИначеЕсли п = 1 Тогда
    т = 1;
ИначеЕсли п = 1 Тогда
    т = 2;
Иначе
    т = -1;
КонецЕсли;
```

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/IfElseDuplicatedCondition.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
