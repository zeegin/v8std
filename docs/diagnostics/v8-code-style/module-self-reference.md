###### v8cs:module-self-reference

# Избыточное использование псевдонима "ЭтотОбъект" (module-self-reference)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-self-reference.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-self-reference.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=4e83ed5f8c060f12b1202da649d01c22ae2a48ba6153f46359ccab9fffa398c8
-->

Избыточное обращение внутри модуля через псевдоним "ЭтотОбъект" (к методу, свойству или реквизиту).

Проверяются общие модули, модули объектов, наборов записей, модули менеджеров значений и модули форм.
Проверку модулей объектов, наборов записей и менеджеров значений можно отключить
через параметр `Проверять модули объектов (наборов записей, менеджеров значений)`.

Для модулей форм проверяется только обращение к методам и существующим свойствам
(в случае если установлен параметр `Проверять только существовующие свойства в форме`, иначе проверяются все случаи).

## Неправильно

```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

ЭтотОбъект.мояПеременная = ЭтотОбъект.тест();
```

## Правильно

```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

мояПеременная = тест();
```

## См.

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-self-reference.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
