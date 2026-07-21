###### bslls:IdenticalExpressions

# Одинаковые выражения слева и справа от "foo" оператора (IdenticalExpressions)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `suspicious`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/IdenticalExpressions.md
source_path=docs/diagnostics/IdenticalExpressions.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=3398f803a48fcbf08813273dd26937b2ef5d9c678d38335db10a3ab3f208a033
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Если в тексте программы имеется оператор (<, >, <=, >=, =, <>, И, ИЛИ, -, /), слева и справа от которого расположены одинаковые подвыражения фрагмент кода, который, скорее всего, содержит логическую ошибку.

## Примеры

```bsl
Если Сумма <> 0 И Сумма <> 0 Тогда

    // Тут код

КонецЕсли;
```

Здесь оператор `И` окружен одинаковыми выражениями `Сумма <> 0`,
что наталкивает на мысли об ошибке по невнимательности при копировании. Правильное выражение будет выглядеть так:

```bsl
Если Сумма <> 0 И СуммаНДС <> 0 Тогда

    // Тут код

КонецЕсли;
```

ИЛИ

```bsl
Если Сумма <> 0 Тогда

    // Тут код

КонецЕсли;
```

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/IdenticalExpressions.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
