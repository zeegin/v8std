###### v8cs:module-consecutive-blank-lines

# Проверка максимального количства пустых строк (module-consecutive-blank-lines)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-consecutive-blank-lines.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-consecutive-blank-lines.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=86c2cca6bb27f46a3a9ae373dcd0f9df359c2e2ac5782af96483f08a1bedd69b
-->

## Неправильно

```bsl
Процедура Тест()

    А1 = 1;


    A2 = 2;

КонецПроцедуры
```

## Правильно

```bsl
Процедура Тест()

    А1 = 1;

    A2 = 2;

КонецПроцедуры
```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-consecutive-blank-lines.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
