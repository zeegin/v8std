###### bslls:WrongUseOfRollbackTransactionMethod

# Некорректное использование метода ОтменитьТранзакцию() (WrongUseOfRollbackTransactionMethod)

- Тип: Ошибка
- Важность: Критичный

Вызов метода `#!bsl ОтменитьТранзакцию()` должен производиться в блоке `#!bsl Попытка - Исключение`. В блоке Исключение нужно сначала вызвать метод `#!bsl ОтменитьТранзакцию()`, а затем выполнять другие действия, если они требуются.

###### Стандарт

[Транзакции: правила использования: п. 1.3](../../std/783.md#13)

###### Источник

https://1c-syntax.github.io/bsl-language-server/diagnostics/WrongUseOfRollbackTransactionMethod/