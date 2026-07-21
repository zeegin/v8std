###### v8cs:module-accessibility-at-client

# Метод или переменная доступны НаКлиенте (module-accessibility-at-client)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-accessibility-at-client.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-accessibility-at-client.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=ad842308b31790be01c1f013c27a9fbb7f02da83b0ab147098fef74f1e1d32fd
-->

Метод или переменная доступны НаКлиенте в модулях менеджера или объекта

## Неправильно

```bsl

Перем ПеременнаяМодуля;

Процедура ПередУдалением(Отказ)
	// Неправильно
КонецПроцедуры

Процедура Неправильно() Экспорт
	// пусто
КонецПроцедуры

ПеременнаяМодуля = Неопределено;

```

## Правильно

```bsl
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда

Перем ПеременнаяМодуля;

Процедура ПередУдалением(Отказ)
	// Неправильно
КонецПроцедуры

Процедура Правильно() Экспорт
	// пусто
КонецПроцедуры

ПеременнаяМодуля = Неопределено;

#Иначе
  ВызватьИсключение НСтр("ru = 'Недопустимый вызов объекта на клиенте.'");
#КонецЕсли
```

## См.

- [Поддержка толстого клиента, управляемое приложение, клиент-сервер](https://its.1c.ru/db/v8std#content:680:hdoc:2)
- [Обработчики событий ОбработкаПолученияПредставления и ОбработкаПолученияПолейПредставления](https://its.1c.ru/db/v8std#content:746:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std680, п. 2: Поддержка толстого клиента, управляемое приложение, клиент-сервер](../../std/680.md#2) — Диагностика v8cs:module-accessibility-at-client проверяет требование пункта 2 стандарта std680.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/module-accessibility-at-client.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
