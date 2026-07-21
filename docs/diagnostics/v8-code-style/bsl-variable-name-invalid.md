###### v8cs:bsl-variable-name-invalid

# Правила образования имен переменных (bsl-variable-name-invalid)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/bsl-variable-name-invalid.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/bsl-variable-name-invalid.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=2230c613fbbf0b5eb2351b2cb9fec2905ad571d1556393d5eb690ced337f1965
-->

1. Имена переменных следует образовывать от терминов предметной области таким образом, чтобы из имени
   переменной было понятно ее назначение.
2. Имена следует образовывать путем удаления пробелов между словами. При этом, каждое слово в имени
   пишется с прописной буквы. Предлоги и местоимения из одной буквы также пишутся прописными буквами.
3. Имена переменных запрещается начинать с подчеркивания.
4. Имена переменных не должны состоять из одного символа. Использование односимвольных имен переменных
   допускается только для счетчиков циклов..
5. Переменные, отражающие состояние некоторого флага, следует называть так, как пишется истинное значение этого флага.

## Примеры некорректных имен переменных

```bsl
массРеквизитов, _СоотвВидИмя, нС
```

## Примеры корректных имен переменных

```bsl
Перем ДиалогРаботыСКаталогом;
Перем КоличествоПачекВКоробке;
НовыйДокументСсылка;
```

## См.

- [Правила образования имен переменных](https://its.1c.ru/db/v8std#content:454:hdoc:3)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std454, п. 3: Правила образования имен переменных](../../std/454.md#3) — Диагностика v8cs:bsl-variable-name-invalid проверяет требование пункта 3 стандарта std454.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/bsl-variable-name-invalid.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
