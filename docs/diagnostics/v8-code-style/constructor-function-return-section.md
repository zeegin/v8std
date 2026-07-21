###### v8cs:constructor-function-return-section

# Секция возвращаемого значения функции-конструктора данных (constructor-function-return-section)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/constructor-function-return-section.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/constructor-function-return-section.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=c88437aefd2f2c70f7b9a40f5f4e0e52700761253a30cd893b62407578037808
-->

Система строгой типизации кода проверяет что поле документирующего комментария имеет описание типа

## Неправильно

## Правильно

```bsl
// Описание обработки для регистрации как внешней
//
// Возвращаемое значение:
//   Структура:
//   	* Вид			- Строка
//   	* Назначение		- Массив Из Строка
//   	* Наименование		- Строка
//   	* БезопасныйРежим	- Булево
//   	* Версия		- Строка
//   	* Информация		- Строка
//   	* Команды		- ТаблицаЗначений
//
Функция СведенияОВнешнейОбработке() Экспорт
```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/constructor-function-return-section.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
