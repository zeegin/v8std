###### v8cs:using-isinrole

# Использован метод "РольДоступна" (using-isinrole)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/using-isinrole.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/using-isinrole.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=e6d65c6165de3fc72da9f812b37f1e873ea150eab17d508f25d71f12347a3652
-->

Для проверки прав доступа в коде следует использовать метод ПравоДоступа.

## Неправильно

```bsl
Если РольДоступна("ДобавлениеИзменениеСтранМира") Тогда ...
```

## Правильно

```bsl
Если ПравоДоступа("Редактирование", Метаданные.Справочники.СтраныМира) Тогда ...
```

Такой подход позволяет повысить устойчивость кода к пересмотру состава
ролей в конфигурации, а также обеспечить работоспособность конфигурации
в особых режимах работы, когда реальный состав ролей отличается от
спроектированного

## См.

- [Настройка ролей и прав доступа](https://its.1c.ru/db/v8std#content:689:hdoc)
- [Проверка прав доступа](https://its.1c.ru/db/v8std#content:737:hdoc:3)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std689: Настройка ролей и прав доступа](../../std/689.md)
- [#std737: Проверка прав доступа](../../std/737.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/using-isinrole.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
