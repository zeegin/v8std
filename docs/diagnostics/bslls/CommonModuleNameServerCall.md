###### bslls:CommonModuleNameServerCall

# Пропущен постфикс "ВызовСервера" (CommonModuleNameServerCall)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameServerCall.md
source_path=docs/diagnostics/CommonModuleNameServerCall.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=5e4aec516e12aac5b68d6065f877b31c71626fbb130ed16c14d5fb84fe1f7e8d
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Серверные общие модули для вызова с клиента содержат серверные процедуры и функции, доступные для использования
из клиентского кода. Они составляют клиентский программный интерфейс сервера приложения.
Такие процедуры и функции размещаются в общих модулях с признаком:

* Сервер (флажок Вызов сервера установлен)

Серверные общие модули для вызова с клиента называются по общим правилам именования объектов метаданных
и должны именоваться с постфиксом "ВызовСервера" (англ. "ServerCall").

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

РаботаСФайламиВызовСервера, CommonServerCall

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->


[Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:469:hdoc:2.2)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std469, п. 2.2: Правила создания общих модулей](../../std/469.md#22) — Диагностика «Пропущен постфикс "ВызовСервера" (CommonModuleNameServerCall)» проверяет условие пункта 2.2 стандарта std469.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameServerCall.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
