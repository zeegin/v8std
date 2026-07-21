###### v8cs:doc-comment-return-section-type

# Секция возвращаемого значения документирующего комментария содержит корректные типы (doc-comment-return-section-type)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-return-section-type.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-return-section-type.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=2a574190d6d22b54e49ec05dbea4b7c0cfc4ae1e37656552a955deab56e9e017
-->

## Неправильно

```bsl

// Возвращаемое значение:
//  пустое значение
Функция Неправильно(Параметры) Экспорт
	// пустая
КонецФункции

// Ссылка на функцию без указания типа возвращаемого значения
//
// Возвращаемое значение:
//  См. Неправильно()
Функция Неправильно2(Параметры) Экспорт
	// пустая
КонецФункции

// Возвращаемое значение:
//  НеизвестныйТип - неизвестный возвращаемый тип
Функция Неправильно3(Параметры) Экспорт
	// пустая
КонецФункции

```

## Правильно

```bsl

// Параметры:
//  См. Правильно2()
Функция Правильно(Параметры) Экспорт
	// пустая
КонецФункции

// Параметры:
//  Структура - указан возвращаемый тип
Функция Правильно2(Параметры) Экспорт
	// пустая
КонецФункции

```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-return-section-type.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
