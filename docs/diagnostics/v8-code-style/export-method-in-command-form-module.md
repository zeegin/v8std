###### v8cs:export-method-in-command-form-module

# Ограничения на использование экспортных процедур и функций в модуле команд и форм (export-method-in-command-form-module)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/export-method-in-command-form-module.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/export-method-in-command-form-module.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=5369e6b43a81c0914e26180710bd2cdbf91abc1a69565213cb8faed943515957
-->

Не следует размещать экспортные процедуры и функции в модулях команд и форм.
Для реализации экспортных процедур и функций рекомендуется использовать модули объектов, модули менеджеров объектов или
общие модули.

Так же, рекомендуется избегать обращения к методам и свойствам формы после ее открытия.

Исключения из этого правила составляют экспортные процедуры-обработчики оповещений (ОписаниеОповещения.ИмяПроцедуры).

## Неправильно

```bsl
&НаКлиенте
Процедура ОбработкаКоманды(ПараметрКоманды, ПараметрыВыполненияКоманды) Экспорт
КонецПроцедуры
```

## Правильно

```bsl
Процедура ОбработкаКоманды(ПараметрКоманды, ПараметрыВыполненияКоманды)
КонецПроцедуры
```

## См.

- [Ограничения на использование экспортных процедур и функций](https://its.1c.ru/db/v8std#content:544:hdoc)
- [Правила создания модулей форм](https://its.1c.ru/db/v8std#content:630:hdoc)
- [Открытие форм](https://its.1c.ru/db/v8std#content:404:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std544: Ограничения на использование экспортных процедур и функций](../../std/544.md)
- [#std630: Правила создания модулей форм](../../std/630.md)
- [#std404: Открытие форм](../../std/404.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/export-method-in-command-form-module.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
