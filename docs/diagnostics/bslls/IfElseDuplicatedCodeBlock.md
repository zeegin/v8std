###### bslls:IfElseDuplicatedCodeBlock

# Повторяющиеся блоки кода в синтаксической конструкции Если...Тогда...ИначеЕсли... (IfElseDuplicatedCodeBlock)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `suspicious`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/IfElseDuplicatedCodeBlock.md
source_path=docs/diagnostics/IfElseDuplicatedCodeBlock.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=c039d73344a49a6fe8e09ebd626151d1e4012bb4f03ca1ee581b2a292ef6e185
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Синтаксическая конструкция **Если...Тогда...ИначеЕсли...** не должна иметь одинаковых блоков кода.

## Примеры

```bsl
Если п = 0 Тогда
    т = 0;
ИначеЕсли п = 1 Тогда
    т = 1;
ИначеЕсли п = 2 Тогда
    т = 1;
Иначе
    т = -1;
КонецЕсли;
```

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/IfElseDuplicatedCodeBlock.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
