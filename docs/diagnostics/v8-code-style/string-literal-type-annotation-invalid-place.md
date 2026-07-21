###### v8cs:string-literal-type-annotation-invalid-place

# Теги размещены неправильно, внутри конструкции языка (string-literal-type-annotation-invalid-place)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/string-literal-type-annotation-invalid-place.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/string-literal-type-annotation-invalid-place.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=552e061a3545d0079af18a2155ef54a783f010b8ee759af0d0cd7b880231302b
-->

## Неправильно

```bsl

Процедура НоваяПроцедура(ОбъектXDTO)

    Если Истина // @fqn
    Тогда // @fqn

        Значение = "";
    ИначеЕсли Ложь

    Тогда // @noN-nls-1

        Значение = "";

    Если
        Значение = "";

    КонецЕсли;

КонецПроцедуры

```

## Правильно

```bsl

Процедура НоваяПроцедура(ОбъектXDTO)

    Если Истина Тогда

        Значение = ""; // @fqn
    ИначеЕсли Ложь

    Тогда

        Значение = ""; // @noN-nls-1

    Если
        Значение = "";

    КонецЕсли;

КонецПроцедуры

```

## См.

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/string-literal-type-annotation-invalid-place.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
