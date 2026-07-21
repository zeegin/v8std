###### bslls:NestedTernaryOperator

# Вложенный тернарный оператор (NestedTernaryOperator)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `brainoverload`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/NestedTernaryOperator.md
source_path=docs/diagnostics/NestedTernaryOperator.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=be68a6edf2210a41e82379e5dc25d33f9dc85e2e24914ac74d50b73a0d06a907
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Использование вложенных тернарных операторов затрудняет читаемость кода.

## Примеры

### Некорректное использование тернарных операторов

```bsl
Результат  =  ?(x % 15 <> 0, ?( x % 5 <> 0, ?( x % 3 <> 0, x, "Fizz"), "Buzz"), "FizzBuzz");
```

```bsl
Если ?(Стр.Emp_emptype = Null, 0, Стр.Emp_emptype) = 0 Тогда

      Статус = "Готово";

КонецЕсли;
```

### Возможные вариант реализации

```bsl
Если x % 15 = 0 Тогда
	Результат = "FizzBuzz";
ИначеЕсли x % 3 = 0 Тогда
	Результат = "Fizz";
ИначеЕсли x % 5 = 0 Тогда
	Результат = "Buzz";
Иначе
	Результат = x;
КонецЕсли;
```

```bsl
Если Стр.Emp_emptype = Null ИЛИ Стр.Emp_emptype = 0 Тогда

      Статус = "Готово";

КонецЕсли;
```

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/NestedTernaryOperator.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
