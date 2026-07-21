###### v8cs:dont-use-modality-mode

# Checks dont use modality call in dont use modality mode. (dont-use-modality-mode)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/dont-use-modality-mode.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/dont-use-modality-mode.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=8f73458893d291563474f5671baa875f67557003779e6f44401646d463e181fc
-->

## Неправильно

Процедура ПроцедураПример(Параметры)
	Предупреждение("Сообщение");
КонецПроцедуры


## Правильно

Процедура ПроцедураПример(Параметры)
	ПоказатьПредупреждение(,"Сообщение");
КонецПроцедуры


 ## См.
[Ограничение на использование модальных окон и синхронных вызовов](https://its.1c.ru/db/v8std#content:703:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std703, п. 1: Ограничение на использование модальных окон и синхронных вызовов](../../std/703.md#1) — Диагностика v8cs:dont-use-modality-mode проверяет требование пункта 1 стандарта std703.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/dont-use-modality-mode.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
