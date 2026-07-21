###### v8cs:db-object-max-number-length

# Превышена максимальная длина числовых данных (31 знак) (db-object-max-number-length)

- Категория: `md`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-max-number-length.md
source_path=bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-max-number-length.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=6880c2368ce192bab7414d5fe8f69de271b7904fa2090dcbad7cf277532e1c7a
-->

Конфигурация должна быть одинаково рассчитана на работу со всеми
СУБД, операционными системами, веб-браузерами и различными режимами
работы, которые поддерживает платформа 1С:Предприятие.


## Неправильно

Максимальная длина числовых данных – 38 знак


## Правильно


Соблюдение стандартов "Приложение 8. Особенности работы с различными
СУБД"

[8.3. IBM Db2](https://its.1c.ru/db/v83doc#bookmark:dev:TI000001288)


> 8.3. Сервер IBM DB2
> ●  Максимальная длина числовых данных – 31 знак (а не 38).



## См.

- [Общие требования к конфигурации](https://its.1c.ru/db/v8std#content:467:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std467: Общие требования к конфигурации](../../std/467.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/db-object-max-number-length.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
