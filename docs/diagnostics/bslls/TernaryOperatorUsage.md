###### bslls:TernaryOperatorUsage

# Использование тернарного оператора (TernaryOperatorUsage)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Нет
- Теги: `brainoverload`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/TernaryOperatorUsage.md
source_path=docs/diagnostics/TernaryOperatorUsage.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=33e542db3cac1650ae0e80009d2aec28d5a0024f32888a1c7432b3ce90a9a845
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Вместо тернарного оператора стоит использовать конструкцию "Если-Иначе".

## Примеры

Плохо:

```bsl
Результат  =  ?(x % 15 <> 0, ?( x % 5 <> 0, ?( x % 3 <> 0, x, "Fizz"), "Buzz"), "FizzBuzz");
```

Хорошо:

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

Плохо:

```bsl
Если ?(Стр.Emp_emptype = Null, 0, Стр.Emp_emptype) = 0 Тогда
      Статус = "Готово";
КонецЕсли;
```
Хорошо:

```bsl
Если Стр.Emp_emptype = Null ИЛИ Стр.Emp_emptype = 0 Тогда
      Статус = "Готово";
КонецЕсли;
```

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/TernaryOperatorUsage.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
