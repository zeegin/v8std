###### v8cs:restriction-execute-external-component-code

# Ограничение на выполнение «внешнего» кода (restriction-execute-external-component-code)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/restriction-execute-external-component-code.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/restriction-execute-external-component-code.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=db8fa3004c6fbe263cdfcc8d4e5b0a0e9e4313091e2180786e9e0ff02774e117
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


## Неправильно

ПодключитьВнешнююКомпоненту();

## Правильно

ОбщегоНазначенияКлиент.ПодключитьКомпонентуИзМакета();

## См.

- [Ограничение на выполнение «внешнего» кода](https://its.1c.ru/db/v8std#content:669:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std669: Ограничение на выполнение внешнего кода](../../std/669.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/restriction-execute-external-component-code.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
