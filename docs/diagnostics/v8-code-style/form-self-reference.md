###### v8cs:form-self-reference

# Использование устаревшего псевдонима (form-self-reference)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-self-reference.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-self-reference.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=61a4b7afdf18ad48f9253f30d7aa41365076fdb19e88d888e3b70fecf0f7fe85
-->

Следует использовать псевдоним "ЭтотОбъект" вместо устаревшего "ЭтаФорма" в модуле формы

## Неправильно

```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

ЭтаФорма.мояПеременная = ЭтаФорма.тест();
```

## Неправильно

```bsl
	Оповещение = Новый ОписаниеОповещения("ВопросЗавершение", ЭтаФорма);
	ПоказатьВопрос(Оповещение, ТекстВопроса, РежимДиалогаВопрос.ДаНет, , КодВозвратаДиалога.Да);
```


## Правильно

```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

ЭтотОбъект.мояПеременная = ЭтотОбъект.тест();
```

## Правильно

```bsl
	Оповещение = Новый ОписаниеОповещения("ВопросЗавершение", ЭтотОбъект);
	ПоказатьВопрос(Оповещение, ТекстВопроса, РежимДиалогаВопрос.ДаНет, , КодВозвратаДиалога.Да);
```

## См.

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-self-reference.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
