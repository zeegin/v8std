###### v8cs:doc-comment-redundant-parameter-section

# Секция параметров документирующего комментария избыточная (doc-comment-redundant-parameter-section)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-redundant-parameter-section.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-redundant-parameter-section.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=c34b8c2c5a8496318709ded69f4b3cec433f4cb1602388293702a031e83189d8
-->

Документирующий комментарий для метода без параметров не должен иметь секции параметров, и она должна быть удалена.

## Неправильно

```bsl
// Параметры:
//  Параметры - Метод не должен иметь секцию параметров
Процедура Неправильно()
	// пусто
КонецПрцоедуры

```

## Правильно

```bsl
// Метод без параметров не должен иметь такую секцию
Процедура Правильно()
	// пусто
КонецПрцоедуры

```


## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-redundant-parameter-section.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
