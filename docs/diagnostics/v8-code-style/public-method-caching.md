###### v8cs:public-method-caching

# Проверка кэширования программного интерфейса (public-method-caching)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/public-method-caching.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/public-method-caching.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=783b3713abfb59cbf95ba1d794a28bf459e5cc89ccb75242e9295a5cab224988
-->

Не следует создавать программный интерфейс в модулях с повторным использованием возвращаемых значений.

## Неправильно

```bsl

#Область ПрограммныйИнтерфейс

Процедура ПолучитьДанные() Экспорт
КонецПроцедуры

#КонецОбласти

```

## Правильно

```bsl

#Область СлужебныйПрограммныйИнтерфейс

Процедура ПолучитьДанные() Экспорт
КонецПроцедуры

#КонецОбласти

```

## См.


- [Обеспечение совместимости библиотек](https://its.1c.ru/db/v8std/content/644/hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std644, п. 3.6: Обеспечение совместимости библиотек](../../std/644.md#36) — Диагностика v8cs:public-method-caching проверяет требование пункта 3.6 стандарта std644.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/public-method-caching.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
