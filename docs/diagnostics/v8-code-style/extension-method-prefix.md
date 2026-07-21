###### v8cs:extension-method-prefix

# У метода отсутствует префикс расширения (extension-method-prefix)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-method-prefix.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-method-prefix.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=7d23310e015e82a170fe71f1304502a8a62612288195c5cba4d3b4468eca8873
-->

Все добавленные объекты (методы и объекты, отчеты, обработки и подсистемы, а также обработчики событий) расширения,
а также имена собственных методов и переменных расширяющих модулей, должны иметь префикс,
соответствующий префиксу самого расширения.

## Неправильно

```bsl
&Before("NonComplient")
Процедура Ext_НеправильныйМетод()
    //
КонецПроцедуры
```

## Правильно

```bsl
&After("Complient")
Процедура Ext1_ПравильныйМетод()
    //
КонецПроцедуры
```

## См.


- [Требования к программным продуктам](https://1c.ru/rus/products/1c/predpr/compat/soft/requirements.htm)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/extension-method-prefix.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
