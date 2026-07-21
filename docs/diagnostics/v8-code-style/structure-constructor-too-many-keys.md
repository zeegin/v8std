###### v8cs:structure-constructor-too-many-keys

# Конструктор структуры содержит слишком много ключей (structure-constructor-too-many-keys)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/structure-constructor-too-many-keys.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/structure-constructor-too-many-keys.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=71af889d961127b08e92f92114a0c848f17fa0719cb82198a3727cc42523f2d2
-->

При создании структуры через конструктор со строкой имён ключей
количество ключей не должно превышать 3 (настраивается).
Если структуре требуется больше ключей, используйте метод `Вставить` для добавления каждого ключа отдельно.
Это повышает читаемость кода и упрощает изменение набора ключей.

## Неправильно

```bsl
Параметры = Новый Структура("Ключ1, Ключ2, Ключ3, Ключ4");
```

## Правильно

```bsl
Параметры = Новый Структура;
Параметры.Вставить("Ключ1");
Параметры.Вставить("Ключ2");
Параметры.Вставить("Ключ3");
Параметры.Вставить("Ключ4");
```

## См.

- [Параметры процедур и функций: конструкторы структур](https://its.1c.ru/db/v8std#content:640:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std640: Параметры процедур и функций](../../std/640.md)
- [#std693: Использование объектов типа Структура](../../std/693.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/structure-constructor-too-many-keys.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
