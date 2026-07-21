###### v8cs:extension-variable-prefix

# У имени переменной отсутствует префикс расширения (extension-variable-prefix)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-variable-prefix.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-variable-prefix.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=13facd6193df3f65b26e0e41630791171eb8e6ba2c51cef813f75ed84928a7f4
-->

Все добавленные объекты (методы и объекты, отчеты, обработки и подсистемы, а также обработчики событий) расширения,
а также имена собственных методов и переменных расширяющих модулей, должны иметь префикс,
соответствующий префиксу самого расширения.

## Неправильно

```bsl
Перем КонвертацияФайлов Экспорт;

```

## Правильно

```bsl
Перем Ext1_КонвертацияФайлов Экспорт;

```

## См.


- [Требования к программным продуктам](https://1c.ru/rus/products/1c/predpr/compat/soft/requirements.htm)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-variable-prefix.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
