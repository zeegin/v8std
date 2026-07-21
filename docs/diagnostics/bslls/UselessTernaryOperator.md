###### bslls:UselessTernaryOperator

# Бесполезный тернарный оператор (UselessTernaryOperator)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `badpractice`, `suspicious`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UselessTernaryOperator.md
source_path=docs/diagnostics/UselessTernaryOperator.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=7a0c7c9fabe350792e009827a6c78a6328952cbc20a5776dd64e46b95e9570c6
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
Размещение в тернарном операторе булевых констант "Истина" или "Ложь" указывает на плохую продуманность кода.

## Примеры
Бессмысленные операторы

```Bsl
А = ?(Б = 1, Истина, Ложь);
```
```Bsl
А = ?(Б = 0, False, True);
```

Подозрительные операторы (обе ветки - одна и та же булева константа, результат не зависит от условия)

```Bsl
А = ?(Б = 1, True, Истина);
```
```Bsl
А = ?(Б = 0, Ложь, False);
```

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UselessTernaryOperator.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
