###### bslls:TryNumber

# Приведение к числу в попытке (TryNumber)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/TryNumber.md
source_path=docs/diagnostics/TryNumber.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=ec1c4490676400636afaac7ebc7e19c7fe951e402cc8595e12fba282d1d023cd
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Неправильно использовать исключения для приведения значения к типу. Для таких операций необходимо использовать возможности объекта ОписаниеТипов.

## Примеры

Неправильно:

```bsl
Попытка
 КоличествоДнейРазрешения = Число(Значение);
Исключение
 КоличествоДнейРазрешения = 0; // значение по умолчанию
КонецПопытки;
```

Правильно:

```bsl
ОписаниеТипа = Новый ОписаниеТипов("Число");
КоличествоДнейРазрешения = ОписаниеТипа.ПривестиЗначение(Значение);
```

## Источники

* [Стандарт: Перехват исключений в коде](https://its.1c.ru/db/v8std#content:499:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std499, п. 1: Перехват исключений в коде](../../std/499.md#1) — Диагностика «Приведение к числу в попытке (TryNumber)» проверяет условие пункта 1 стандарта std499.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/TryNumber.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
