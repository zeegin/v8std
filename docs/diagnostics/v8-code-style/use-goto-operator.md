###### v8cs:use-goto-operator

# Используется оператор Перейти (use-goto-operator)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/use-goto-operator.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/use-goto-operator.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=de0dfcd99067ec60e4d375cb4be65fead0425698ceebf86b19a8179bb732d28f
-->

В коде на встроенном языке не рекомендуется использовать оператор Перейти,
так как необдуманное использование данного оператора приводит к получению запутанных,
плохо структурированных модулей, по тексту которых затруднительно понять порядок
исполнения и взаимозависимость фрагментов. Вместо оператора Перейти рекомендуется использовать
другие конструкции встроенного языка.

## Неправильно

```bsl
Если ПланВидовРасчета = Объект.ПланВидовРасчета Тогда

  Перейти ~ПланВидовРасчета;

КонецЕсли;
```

## Правильно

```bsl
Если ПланВидовРасчета = Объект.ПланВидовРасчета Тогда

  ОбработатьПланВидовРасчета();

КонецЕсли;
```

## См.

- [Ограничение на использование оператора Перейти](https://its.1c.ru/db/v8std#content:547:hdoc:1)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std547: Ограничение на использование оператора Перейти](../../std/547.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/use-goto-operator.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
