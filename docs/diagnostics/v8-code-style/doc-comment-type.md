###### v8cs:doc-comment-type

# Определение типа документирующего комментария (doc-comment-type)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-type.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-type.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=145587ec7194e59c27084f109767f302911c1c828601925ff18d5bdb7946b4e7
-->

## Неправильно

```bsl
// Параметры:
//  Параметры - Структура1 - некорректый тип
Процедура Неправильно(Параметры) Export
	// пустая
КонецПроцедуры

```

## Правильно

```bsl
// Параметры:
//  Параметры - Структура - корректный тип
Процедура Правильно(Параметры) Экспорт
	// пустая
КонецПроцедуры

```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-type.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
