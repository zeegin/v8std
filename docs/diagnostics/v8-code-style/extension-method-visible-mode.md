###### v8cs:extension-method-visible-mode

# У метода в расширении модуля та же видимость, что и оригинального метода (extension-method-visible-mode)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-method-visible-mode.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-method-visible-mode.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=4bc812f7c9d56bd0a90b92f1b262cd528a188e61afa8c81665f4ca20a9e13095
-->

Считается ошибкой то, что расширение метода делает его компилируемым в тех контекстах, в которых исходный метод не компилируется.

## Неправильно

Модуль конфигурации

#Если Сервер Или ТолстыйКлиентОбычноеПриложение Тогда

Процедура Сервер1()
Везде1();
КонецПроцедуры

Процедура Везде1() Экспорт
КонецПроцедуры

#КонецЕсли

Функция Тест() Экспорт
КонецФункции

Модуль расширения

&После("Сервер1")
Процедура Расш1_Сервер1()
Везде1();
КонецПроцедуры


## Правильно

#Если Сервер Или ТолстыйКлиентОбычноеПриложение Тогда

Процедура Сервер1()
Везде1();
КонецПроцедуры

Процедура Везде1() Экспорт
КонецПроцедуры

#КонецЕсли

Функция Тест() Экспорт
КонецФункции

Модуль расширения

#Если Сервер Или ТолстыйКлиентОбычноеПриложение Тогда

&После("Сервер1")
Процедура Расш1_Сервер1()
Везде1();
КонецПроцедуры

#КонецЕсли

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-method-visible-mode.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
