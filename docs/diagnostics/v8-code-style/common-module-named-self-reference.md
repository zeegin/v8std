###### v8cs:common-module-named-self-reference

# Избыточное обращение по собственному имени внутри общего модуля (common-module-named-self-reference)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-named-self-reference.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-named-self-reference.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=c905fc1252922ef096d9135dec2cd702754bc656f6fc9215dc318f879a1fa0c4
-->

Избыточное обращение по собственному имени внутри общего модуля (к методу, свойству или реквизиту)

Для модулей с повторным использованием возвращаемых значений обращение по собственному имени разрешено

## Неправильно

Внутри модуля с именем "МойМодуль":
```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

МойМодуль.мояПеременная = МойМодуль.тест();
```

## Правильно

Внутри модуля с именем "МойМодуль":

```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

мояПеременная = тест();
```

Внутри модуля с именем "МойМодульПовтИсп":

```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

мояПеременная = МойМодульПовтИсп.тест();
```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-named-self-reference.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
