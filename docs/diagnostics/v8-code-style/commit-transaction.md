###### v8cs:commit-transaction

# Проверка нарушения схемы работы с транзакциями (commit-transaction)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/commit-transaction.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/commit-transaction.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=43883d0dec6ce8511052722a8f3ceb9ac3319fb2846d7414d739fb45f4d748a2
-->

Вызов "ЗафиксироватьТранзакцию()" находится вне конструкции "Попытка... Исключение"
Отсутствует вызов "НачатьТранзакцию()", хотя вызываются "ЗафиксироватьТранзакцию()"
Для вызова "НачатьТранзакцию()" отсутствует парный вызов "ОтменитьТранзакцию()"
Mежду "ЗафиксироватьТранзакцию()" и "Исключение" есть исполняемый код, который может вызвать исключение

## Неправильно

```bsl
    НачатьТранзакцию();
    ЗафиксироватьТранзакцию();
    Попытка
    // ...
    Исключение
    // ...
    ОтменитьТранзакцию();
    // ...
    ВызватьИсключение;
    КонецПопытки;
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

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/commit-transaction.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
