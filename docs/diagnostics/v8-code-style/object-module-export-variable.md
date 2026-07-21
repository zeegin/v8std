###### v8cs:object-module-export-variable

# Использование переменных в программных модулях (object-module-export-variable)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/object-module-export-variable.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/object-module-export-variable.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=685fbb52bdf17e7cc1b1176f9b668acf8047b53886ace9f049e0fb439e6c0c7a
-->

В большинстве случаев, вместо переменных программных модулей следует использовать более подходящие средства разработки платформы 1С:Предприятие.
Поскольку область видимости (использования) таких переменных сложно контролировать,
то они зачастую становятся источником трудновоспроизводимых ошибок.

## Неправильно

```bsl

Перем КонвертацияФайлов Экспорт;

Процедура ПередЗаписью(Отказ)

  Если КонвертацияФайлов Тогда
  ...

КонецПроцедуры

// вызывающий код
ФайлОбъект.КонвертацияФайлов = Истина;
ФайлОбъект.Записать();

```

## Правильно

```bsl

Процедура ПередЗаписью(Отказ)

  Если ДополнительныеСвойства.Свойство("КонвертацияФайлов") Тогда
  ...

КонецПроцедуры

// вызывающий код
ФайлОбъект.ДополнительныеСвойства.Вставить("КонвертацияФайлов", Истина);
ФайлОбъект.Записать();

```

## См.

- [Использование переменных в программных модулях](https://its.1c.ru/db/v8std/content/639/hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std639, п. 2.1: Использование переменных в программных модулях](../../std/639.md#21) — Диагностика v8cs:object-module-export-variable проверяет требование пункта 2.1 стандарта std639.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/object-module-export-variable.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
