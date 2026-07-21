###### v8cs:method-optional-parameter-before-required

# Необязательные параметры процедуры/функции расположены перед обязательными (method-optional-parameter-before-required)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/method-optional-parameter-before-required.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/method-optional-parameter-before-required.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=0f06537fb70b00f024bce544fc112ec270bb77cc3f7b94d4af96e51f0268b8b8
-->

Необязательные параметры (параметры со значениями по умолчанию)
должны располагаться после параметров без значений по умолчанию.

## Неправильно

```bsl
Функция КурсВалютыНаДату(Дата = Неопределено, Валюта) Экспорт
```

## Правильно

```bsl
Функция КурсВалютыНаДату(Валюта, Дата = Неопределено) Экспорт
```

## См.

- [Параметры процедур и функций](https://its.1c.ru/db/v8std#content:640:hdoc:4)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std640: Параметры процедур и функций](../../std/640.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/method-optional-parameter-before-required.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
