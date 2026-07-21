###### v8cs:not-support-goto-operator-webclient

# Ограничение на использование оператора Перейти (not-support-goto-operator-webclient)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/not-support-goto-operator-webclient.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/not-support-goto-operator-webclient.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=27fc7288656201a5f88e7469c80906c33ef205c72661124210f46efae10d5f8a
-->

В коде на встроенном языке не рекомендуется использовать оператор Перейти, так как необдуманное использование
данного оператора приводит к получению запутанных, плохо структурированных модулей, по тексту которых затруднительно
понять порядок исполнения и взаимозависимость фрагментов. Вместо оператора Перейти рекомендуется использовать
другие конструкции встроенного языка.
Запрещается использовать оператор Перейти в общих модулях с признаком
"Клиент (управляемое приложение)", модулях команд и в клиентском коде модулей управляемых форм, так как данный метод
не поддерживается платформой 1С:Предприятие в режиме веб-клиента.

## Неправильно

Например, неправильно:

 Если ПланВидовРасчета = Объект.ПланВидовРасчета Тогда

  Перейти ~ПланВидовРасчета;

 КонецЕсли;

## Правильно

Например, правельно:

 Если ПланВидовРасчета = Объект.ПланВидовРасчета Тогда

  ОбработатьПланВидовРасчета();

 КонецЕсли;

 ## См.

- [Ограничение на использование оператора Перейти](https://its.1c.ru/db/v8std#content:547:hdoc:2)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std547, п. 2: Ограничение на использование оператора Перейти](../../std/547.md#2) — Диагностика v8cs:not-support-goto-operator-webclient проверяет требование пункта 2 стандарта std547.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/not-support-goto-operator-webclient.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
