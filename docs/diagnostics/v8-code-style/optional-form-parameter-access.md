###### v8cs:optional-form-parameter-access

# Обращение к опциональному параметру формы (optional-form-parameter-access)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/optional-form-parameter-access.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/optional-form-parameter-access.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=17caadcd15ab1c99f6663f9a7a32792639599b608ba61724df996b0e136e3150
-->

Параметры формы следует объявлять явно на закладке Параметры редактора формы.
В таком случае в коде обработчика ПриСозданииНаСервере не требуется проверять наличие свойств
у структуры Параметры, а сам состав параметров формы явно задекларирован (поэтому их не требуется
восстанавливать, изучая весь код обработчика ПриСозданииНаСервере).

## Неправильно

```bsl
&НаСервере
Процедура ПриСозданииНаСервере(Отказ, СтандартнаяОбработка)
    ФамилияИмяОтчество = Неопределено;
    Если Параметры.Свойство("ФамилияИмяОтчество", ФамилияИмяОтчество) Тогда
        Объект.Наименование = ФамилияИмяОтчество;
    КонецЕсли;
КонецПроцедуры
```

## Правильно

```bsl
&НаСервере
Процедура ПриСозданииНаСервере(Отказ, СтандартнаяОбработка)
    Объект.Наименование = Параметры.ФамилияИмяОтчество;
КонецПроцедуры
```

## См.

- [Открытие параметризированных форм](https://its.1c.ru/db/v8std#content:741:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std741, п. 3: Открытие параметризированных форм](../../std/741.md#3) — Диагностика v8cs:optional-form-parameter-access проверяет требование пункта 3 стандарта std741.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/optional-form-parameter-access.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
