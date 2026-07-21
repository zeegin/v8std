###### v8cs:form-module-missing-pragma

# Всегда использовать директивы компиляции в модуле формы (form-module-missing-pragma)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-module-missing-pragma.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-module-missing-pragma.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=e5d599693cbe85645723c47726f41089c0af3718b29ca8ce58e42e9e54a307a7
-->

1.1. Конфигурация должна использовать только штатные и документированные
возможности платформы 1С:Предприятие.

...

Платформа позволяет в модулях форм реализовывать процедуры без директив
компиляции (&НаСервере и т.п.). Такие процедуры не работают в
веб-клиенте и приводят к лишнему серверному вызову.

## Неправильно

```bsl
Процедура Серверная()


КонецПроцедуры
```

## Правильно

```bsl
&НаСервере
Процедура Серверная()


КонецПроцедуры
```

## См.

- [Исполнение модуля формы на клиенте и на сервере](https://its.1c.ru/db/pubv8devui/content/189/hdoc/)
- [Использование директив компиляции и инструкций препроцессора](https://its.1c.ru/db/v8std/content/439/hdoc/)
- [Общие требования к конфигурации](https://its.1c.ru/db/v8std#content:467:hdoc)
- [Модуль формы](https://its.1c.ru/db/v8320doc#bookmark:dev:TI000000403)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std439, п. 1: Использование директив компиляции и инструкций препроцессора](../../std/439.md#1) — Диагностика v8cs:form-module-missing-pragma проверяет требование пункта 1 стандарта std439.
- [#std467, п. 1.1: Общие требования к конфигурации](../../std/467.md#11) — Диагностика v8cs:form-module-missing-pragma проверяет требование пункта 1.1 стандарта std467. Примечание: Пункт задаёт общее требование использовать только документированные возможности; непосредственное правило директив находится в std439/1.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-module-missing-pragma.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
