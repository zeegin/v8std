###### v8cs:typed-value-adding-to-untyped-collection

# Добавление типизированного значения в не типизированную коллекцию (typed-value-adding-to-untyped-collection)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/typed-value-adding-to-untyped-collection.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/typed-value-adding-to-untyped-collection.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=6ea7f43fe629e90b8c60829a306a9811bea2d52bf8b6a658354aa1a439a38092
-->

Проверяет, что вызов метода ```Добавить()``` происходит для типизированной коллекции.

## Неправильно

Тип элементов коллекции не указан.

```bsl
// @strict-types

Результат = Новый Массив();

Результат.Добавить(42);
```

## Правильно

Необходимо указать тип элементов коллекции.

```bsl
// @strict-types

Результат = Новый Массив(); // Массив из Число

Результат.Добавить(42);
```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/typed-value-adding-to-untyped-collection.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
