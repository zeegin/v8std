###### v8cs:bsl-canonical-pragma

# Аннотация написана канонически (bsl-canonical-pragma)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/bsl-canonical-pragma.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/bsl-canonical-pragma.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=cf2b0e484191a518d409b643c26a1ac9079d9b9ce32c82db16e5b0b979139d76
-->

Аннотации пишутся канонически (как в документации или Синтакс-помощнике).

## Неправильно

```bsl
&ИЗМЕНЕНИЕиконтроль("МояФункция")
Функция Расш1_МояФункция()

	#Удаление
	Возврат 1;
	#КонецУдаления

КонецФункции
```

## Правильно

```bsl
&ИзменениеИКонтроль("МояФункция")
Функция Расш1_МояФункция()

	#Удаление
	Возврат 1;
	#КонецУдаления

КонецФункции
```

## См.

- https://its.1c.ru/db/v8std#content:441:hdoc

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std441, п. 1: Общие требования к построению конструкций встроенного языка](../../std/441.md#1) — Диагностика v8cs:bsl-canonical-pragma проверяет требование пункта 1 стандарта std441.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/bsl-canonical-pragma.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
