###### v8cs:module-attachable-event-handler-name

# Имя подключаемого обработчка события (module-attachable-event-handler-name)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-attachable-event-handler-name.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-attachable-event-handler-name.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=348b4b732f03ad75af8e6563519f3286150005879339f316143ae626a1e43067
-->

Имя программно добавленного обработчика события должно соответствать шаблону: префикс **Подключаемый_**

## Неправильно

```bsl
// Параметры:
//  Элемент - FormField
Процедура Неправильно(Элемент)

	Элемент.SetAction("ПриИзменении", "НеправильноПриИзменении");

КонецПроцедуры
```

## Правильно

```bsl
// Параметры:
//  Элемент - FormField
Процедура Правильно(Элемент)

	Элемент.SetAction("ПриИзменении", "Подключаемый_ПравильноПриИзменении");

КонецПроцедуры
```

## См.

- [Обработчики событий модуля формы, подключаемые из кода](https://its.1c.ru/db/v8std#content:492:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std492: Обработчики событий модуля формы, подключаемые из кода](../../std/492.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-attachable-event-handler-name.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
