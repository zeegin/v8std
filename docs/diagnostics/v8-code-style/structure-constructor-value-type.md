###### v8cs:structure-constructor-value-type

# Типизация значений в конструкторе структуры (structure-constructor-value-type)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/structure-constructor-value-type.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/structure-constructor-value-type.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=e7af10588d03e76714aa7dd4be896b38f3966536d7cc8850232f41c129643b93
-->

Проверяет строковый литерал в конструкторе структуры что каждый ключ имеет типзированное значение.

## Неправильно

Ключи структуры инициализируются без какого-либо значения по умолчанию что устанавливает пустой тип значения для ключа структуры на всё время жизни.

```bsl
// @strict-types

Процедура Тест() Экспорт

	Параметры = новый Структура("Ключ1, Ключ2, Ключ3");
	// некоторый код...

	Параметры.Ключ1 = 1345;
	Параметры.Ключ2 = "New vlaue";
	Параметры.Ключ3 = Справочники.Товары.Service;

КонецПроцедуры
```

## Правильно

Инициализируйте ключи структуры с типизированным значением по умолчанию в конструкторе или вставляйте новый ключ с типизированным значением по умолчанию.

```bsl
// @strict-types

Процедура Тест() Экспорт

	Параметры = новый Структура("Ключ1, Ключ2", 0, "");
	Параметры.Вставить("Ключ3", Справочники.Товары.ПустаяСсылка());
	// некоторый код...

	Параметры.Ключ1 = 1345;
	Параметры.Ключ2 = "New vlaue";
	Параметры.Ключ3 = Справочники.Товары.Услуга;

КонецПроцедуры
```

## См.

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/structure-constructor-value-type.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
