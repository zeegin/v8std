###### v8cs:use-non-recommended-method

# Использование не рекомендуемых методов (use-non-recommended-method)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/use-non-recommended-method.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/use-non-recommended-method.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=66459d0fd3a7484e4ab18f34fd79f4c862ada1a5ed2c044aa547beb3b0352548
-->

Существуют не рекомендуемые методы, вместо которых следует использовать либо методы БСП, либо другие методы.

## Неправильно

```bsl
Сообщить("Текст сообщения");

Дата = ТекущаяДата();

ОбщаяФорма1 = ПолучитьФорму("ОбщаяФорма.ОбщаяФорма1");
```

```bsl
Найти(Сотрудник.Имя, "Иван");
```

## Правильно

```bsl
Сообщение = Новый СообщениеПользователю();
Сообщение.Текст = ("Текст Сообщения");
Сообщение.Сообщить();

Дата = ТекущаяДатаСеанса();

ОткрытьФорму("ОбщаяФорма.ОбщаяФорма1);
```

```bsl
СтрНайти(Сотрудник.Имя, "Иван");
```

## См.

- [Ограничение на использование метода Сообщить](https://its.1c.ru/db/v8std#content:418:hdoc)
- [Работа в разных часовых поясах](https://its.1c.ru/db/v8std#content:643:hdoc:2.1)
- [Открытие форм](https://its.1c.ru/db/v8std#content:404:hdoc:1)
- [Переход на платформу 1С:Предприятие 8.3](https://its.1c.ru/db/metod8dev#content:5293:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std418: Ограничение на использование метода Сообщить](../../std/418.md)
- [#std643: Работа в разных часовых поясах](../../std/643.md)
- [#std404: Открытие форм](../../std/404.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/use-non-recommended-method.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
