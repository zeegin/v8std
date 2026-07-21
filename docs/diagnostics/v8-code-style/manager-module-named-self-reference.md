###### v8cs:manager-module-named-self-reference

# Избыточное обращение по собственному имени внутри модуля менеджера (manager-module-named-self-reference)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/manager-module-named-self-reference.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/manager-module-named-self-reference.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=bd35172ad495a49f133ee6fb260c995a9beb9e89ff8d8a8b33ab142e60cd3e78
-->

Избыточное обращение по собственному имени внутри модуля менеджера (к методу, свойству или реквизиту)

## Неправильно

Внутри модуля модуля менеджера типа Справочники с именем "МойСправочник":
```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

Справочники.МойСправочник.мояПеременная = Справочники.МойСправочник.тест();
```

## Правильно

Внутри модуля модуля менеджера типа Справочники с именем "МойСправочник":

```bsl
Парам мояПеременная;

Функция тест() Экспорт
    // код
КонецФункции

мояПеременная = тест();
```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/manager-module-named-self-reference.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
