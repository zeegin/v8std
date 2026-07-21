###### bslls:DoubleNegatives

# Двойные отрицания (DoubleNegatives)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `brainoverload`, `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DoubleNegatives.md
source_path=docs/diagnostics/DoubleNegatives.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=396ef876632db07ad011a004de75f1f97c7ca3b3837e4c98103ba753555a9d65
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Использование двойных отрицаний усложняет понимание кода и может приводить к ошибкам, когда вместо истины разработчик "в уме" вычислил Ложь, или наоборот.
Двойные отрицания рекомендуется заменять на выражения условий, которые прямо выражают намерения автора.

## Примеры

### Неправильно

```bsl
Если Не ТаблицаЗначений.Найти(ИскомоеЗначение, "Колонка") <> Неопределено Тогда
    // Сделать действие
КонецЕсли;
```

### Правильно

```bsl
Если ТаблицаЗначений.Найти(ИскомоеЗначение, "Колонка") = Неопределено Тогда
    // Сделать действие
КонецЕсли;
```

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->

* Источник: [Remove double negative](https://www.refactoring.com/catalog/removeDoubleNegative.html)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DoubleNegatives.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
