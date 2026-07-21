###### v8cs:semicolon-missing

# Отсутствие точки с запятой в конце оператора (semicolon-missing)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/semicolon-missing.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/semicolon-missing.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=86f5d7d3f79f46be593ec444c05f2eae1885a3de3687dcee0b8641581c5f03b1
-->

Точка с запятой в конце последнего оператора блока не являеться обязательной, предпочтительно наличие.

## Неправильно

Процедура Ааааa()

    А = 1

КонецПроцедуры

## Правильно

Процедура Ааааa()

    А = 1;

КонецПроцедуры

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/semicolon-missing.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
