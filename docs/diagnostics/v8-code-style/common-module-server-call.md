###### v8cs:common-module-server-call

# Ограничение на установку признака «Вызов сервера» у общих модулей (common-module-server-call)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-server-call.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-server-call.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=814b9b34ebddc7f66f998bb55690a1c6f7a6af1d1f9bb7019b00abe9adef72d5
-->

Не следует всем общим модулям с признаком Сервер принудительно устанавливать флажок Вызов сервера.
 В таких общих модулях следует размещать только те процедуры и функции, которые действительно предназначены для
 вызова из клиентского кода и гарантируют выполнение только тех действий
 (и передачи только тех данных на сторону клиента), которые разрешены пользователю при его работе в программе.
 Например, серверная функция, реализующая некоторый алгоритм расчета, должна передавать на сторону клиента
 окончательный результат этого расчета, но не исходные (или промежуточные) данные для расчета, которые сами по
 себе могут быть недоступны текущему пользователю.


## Неправильно

## Правильно

## See
[Ограничение на установку признака «Вызов сервера» у общих модулей]https://its.1c.ru/db/v8std#content:679:hdoc

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std679: Ограничение на установку признака «Вызов сервера» у общих модулей](../../std/679.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/common-module-server-call.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
