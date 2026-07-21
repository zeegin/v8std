###### v8cs:begin-transaction

# После начала транзакции отсуствует блок Попытка-Исключение (begin-transaction)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/begin-transaction.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/begin-transaction.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=94acfe9422b71a20356964ecb1aed892e3786e89aeeeb17765cbc378fe6ee424
-->

Mежду "НачатьТранзакцию()" и "Попытка" есть исполняемый код, который может вызвать исключение,
после "НачатьТранзакцию()" не найден оператор "Попытка"

## Неправильно

```bsl
    НачатьТранзакцию();
    ЗафиксироватьТранзакцию();
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

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) — Диагностика v8cs:begin-transaction проверяет требование пункта 1.3 стандарта std783.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/begin-transaction.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
