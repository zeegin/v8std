###### v8cs:rollback-transaction

# Проверка нарушения схемы работы с транзакциями (rollback-transaction)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/rollback-transaction.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/rollback-transaction.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=497ae1c31229cc26c196994479ec4949346a052dbea06158951c93265a57c00d
-->

Вызов "ОтменитьТранзакцию()" находится вне конструкции "Попытка... Исключение"
Отсутствует вызов "НачатьТранзакцию()", хотя вызываются "ОтменитьТранзакцию()"
Для вызова "НачатьТранзакцию()" отсутствует парный вызов "ЗафиксироватьТранзакцию()"
Mежду "Исключение" и "ОтменитьТранзакцию()" есть исполняемый код, который может вызвать исключение

## Неправильно

```bsl
    НачатьТранзакцию();
    Попытка
    // ...
    ЗафиксироватьТранзакцию();
    Исключение
    // ...
    ВызватьИсключение;
    КонецПопытки;
    ОтменитьТранзакцию();
```

## Правильно

```bsl
    НачатьТранзакцию();
    Попытка
    // ...
    ЗафиксироватьТранзакцию();
    Исключение
    // ...
    ОтменитьТранзакцию();
    // ...
    ВызватьИсключение;
    КонецПопытки;
```

## См.

- [Перехват исключений в коде](https://its.1c.ru/db/v8std#content:499:hdoc:3.6)
- [Транзакции: правила использования](https://its.1c.ru/db/v8std#content:783:hdoc:1.3)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std499: Перехват исключений в коде](../../std/499.md)
- [#std783: Транзакции: правила использования](../../std/783.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/rollback-transaction.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
