###### v8cs:redundant-export-method

# Тексты модулей конфигурации не должны содержать неиспользуемые экспортные процедуры и функции. (redundant-export-method)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/redundant-export-method.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/redundant-export-method.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=5786080e0ddb846a5966b55733d5991e35a8e15ec32058a54f68a7b1aa9dd6a2
-->

Исключением являются экспортные методы, расположенные в области "ПрограммныйИнтерфейс",
т.к. эти методы часто могут использоваться другими конфигурациями (библиотеками).

Проверка выполняет поиск всех ссылок на метод, поэтому может выполняться длительное время.

## Неправильно

```bsl
Процедура ТекстЗапросаТаблицаСебестоимостьТоваров() Экспорт

КонецПроцедуры
```

## Правильно

```bsl
#Область ПрограммныйИнтерфейс
Процедура ТекстЗапросаТаблицаСебестоимостьТоваров() Экспорт

КонецПроцедуры
#КонецОбласти
```

## См.

- [Общие требования к конфигурации](https://its.1c.ru/db/v8std#content:467:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std467: Общие требования к конфигурации](../../std/467.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/redundant-export-method.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
