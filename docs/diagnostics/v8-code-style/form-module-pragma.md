###### v8cs:form-module-pragma

# Использование директив компиляции модуля формы (form-module-pragma)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-module-pragma.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-module-pragma.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=6c668fa1ff7c5d2dce047655f67fab7f03ae60a44f39b5e28b6972bf17a31fde
-->

Директивы компиляции

```bsl
&НаКлиенте
&НаСервере
&НаСервереБезКонтекста
```

следует применять только в коде модулей управляемых форм и в коде модулей команд.
В остальных модулях рекомендуется применять инструкции препроцессора.

В серверных или клиентских общих модулях контекст исполнения очевиден, поэтому смысла в директивах компиляции нет.
В общих модулях с признаками клиент и сервер применение директив компиляции затрудняет понимание - какие же процедуры (функции) доступны в конечном итоге.

## Неправильно

## Правильно

## См.

- [Использование директив компиляции и инструкций препроцессора](https://its.1c.ru/db/v8std#content:439:hdoc:1)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std439: Использование директив компиляции и инструкций препроцессора](../../std/439.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/form-module-pragma.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
