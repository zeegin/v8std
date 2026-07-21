###### bslls:NestedStatements

# Управляющие конструкции не должны быть вложены слишком глубоко (NestedStatements)

- Тип: Дефект кода
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `badpractice`, `brainoverload`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/NestedStatements.md
source_path=docs/diagnostics/NestedStatements.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=716bf8abb7cb6c54fa6121d45a9c55bc1d053a117b6ad92c55c4b807603a8750
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Вложенные операторы "Если, "Для", "Для Каждого", "Пока" и "Попытка" являются ключевыми ингредиентами для создания так называемого "спагетти-кода".

Такой код трудно читать, рефакторить и поддерживать.

## Примеры

Неправильно

```bsl

Если Чтото Тогда                  // Допустимо - уровень = 1
  /* ... */
  Если ЧтоТоЕще Тогда             // Допустимо - уровень = 2
    /* ... */
    Для Ном = 0 По 10 Цикл          // Допустимо - уровень = 3
      /* ... */
      Если ОпятьУсловие Тогда       // Допустимо - уровень = 4, лимит достигнут, но не превышен
        Если ЕщеЧтото Тогда        // Уровень = 5, Превышен лимит
          /* ... */
        КонецЕсли;
        Возврат;
      КонецЕсли;
    КонецЦикла;
  КонецЕсли;
КонецЕсли;

```

## Источники

* [RSPEC-134](https://rules.sonarsource.com/java/RSPEC-134)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/NestedStatements.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
