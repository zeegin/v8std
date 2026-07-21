###### v8cs:functional-option-privileged-get-mode

# В функциональной опции не установлен флаг "Привилегированный режим при получении" (functional-option-privileged-get-mode)

- Категория: `md`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/functional-option-privileged-get-mode.md
source_path=bundles/com.e1c.v8codestyle.md/markdown/ru/functional-option-privileged-get-mode.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=e4db0914e6b7bc35c04232324c3e89b87bcdbd3ed62abfa8f0e9432d1ee19b92
-->

Во всех функциональных опциях должны быть выставлены флаги
«Привилегированный режим при получении».

Исключение: в конфигурации могут быть предусмотрены параметризированные
ФО, для которых разработчик специально предусматривает различия в
получаемых значениях пользователями с разными правами.
Пример: Есть параметризованная ФО
ИспользватьВалютуПриРасчетеСПерсоналом, которая параметризуется
организацией. Если пользователь будет получать ее значение в контексте
своих прав, то он не увидит поле «валюта» в документе, если у него нет
ни одной организации, где применяется валютный учет.

## Неправильно

## Правильно

## См.

[Настройка ролей и прав доступа](https://its.1c.ru/db/v8std#content:689:hdoc:1.8)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std689: Настройка ролей и прав доступа](../../std/689.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/functional-option-privileged-get-mode.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
