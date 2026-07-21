###### v8cs:input-field-list-choice-mode

# В полях форм со списками выбора следует всегда устанавливать свойство **РежимВыбораИзСписка** в значение Истина (input-field-list-choice-mode)

- Категория: `form`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/input-field-list-choice-mode.md
source_path=bundles/com.e1c.v8codestyle.form/markdown/ru/input-field-list-choice-mode.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=6ac09de34c45c70d6b075b8a97931ef8521354b6c0c476a8f9218b7dfd4ad7f4
-->

В полях форм со списками выбора следует всегда устанавливать свойство **РежимВыбораИзСписка** в значение Истина. В этом случае, в поле будет корректно выводиться локализуемое представление, а не значение из списка выбора.

## Неправильно

## Правильно

## См.

https://its.1c.ru/db/v8std#content:765:hdoc

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std765, п. 5: Элементы форм: требования по локализации](../../std/765.md#5) — Диагностика v8cs:input-field-list-choice-mode проверяет требование пункта 5 стандарта std765.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/input-field-list-choice-mode.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
