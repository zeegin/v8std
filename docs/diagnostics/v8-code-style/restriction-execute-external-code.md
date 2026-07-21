###### v8cs:restriction-execute-external-code

# Ограничение на выполнение «внешнего» кода (restriction-execute-external-code)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/restriction-execute-external-code.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/restriction-execute-external-code.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=6f960f1730a26691070cae5096244d16a5f1b4e15902450770f77b0a7fd892ed
-->

При использовании в конфигурации Библиотеки стандартных
подсистем, следует использовать методы подключения компонент
библиотеки и полностью исключить непосредственное использование
платформенных механизмов подключения внешних компонент, таких как:

ПодключитьВнешнююКомпоненту
НачатьУстановкуВнешнейКомпоненты
УстановитьВнешнююКомпоненту
НачатьПодключениеВнешнейКомпоненты
ЗагрузитьВнешнююКомпоненту

Новый ЗащищенноеСоединениеOpenSSL;


## Неправильно

Новый ЗащищенноеСоединениеOpenSSL;

## Правильно

ОбщегоНазначенияКлиентСервер.НовоеЗащищенноеСоединение();

## См.

- [Ограничение на выполнение «внешнего» кода](https://its.1c.ru/db/v8std#content:669:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std669, п. 7: Ограничение на выполнение внешнего кода](../../std/669.md#7) — Диагностика v8cs:restriction-execute-external-code проверяет требование пункта 7 стандарта std669.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/restriction-execute-external-code.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
