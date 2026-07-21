###### v8cs:notify-description-to-server-procedure

# Описание оповещения на серверную процедуру (notify-description-to-server-procedure)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/notify-description-to-server-procedure.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/notify-description-to-server-procedure.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=0d48d59b2b5e27678c8c5c343989cb4a54e04edc197cba645af62a4b4cc6359e
-->

В качестве параметра обработчика оповещения указана серверная процедура.

Такой вызов оповещения не поддерживается в веб-клиенте.

## Неправильно

```bsl
&НаКлиенте
Процедура Неправильно()

	Оповещение = Новый ОписаниеОповещения("НеправильноеОповещение", ЭтотОбъект);

КонецПроцедуры

&НаСервере
Процедура НеправильноеОповещение() Экспорт
	// Процедура не доступна на клиенте

КонецПроцедуры
```

## Правильно

```bsl
&НаКлиенте
Процедура Правильно()

	Оповещение = Новый ОписаниеОповещения("ПравильноОповещение", ЭтотОбъект);

КонецПроцедуры

&НаКлиенте
Процедура ПравильноОповещение() Экспорт
	// Процедура доступна на клиенте!

КонецПроцедуры
```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/notify-description-to-server-procedure.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
