###### bslls:CommonModuleNameCached

# Пропущен постфикс "ПовтИсп" (CommonModuleNameCached)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameCached.md
source_path=docs/diagnostics/CommonModuleNameCached.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=4aa7a6760049ea699868d88ab617f818bc4698740baee255020488b2de8ebe94
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Модули, предназначенные для реализации на сервере или на клиенте функций с повторным использованием возвращаемых
значений (на время вызова или на время сеанса), именуются с постфиксом "ПовтИсп" (англ. "Cached")
и "КлиентПовтИсп" (англ. "ClientCached") соответственно.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

РаботаСФайламиКлиентПовтИсп, UsersInternalCached

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->


[Стандарт: Правила создания общих модулей](https://its.1c.ru/db/v8std#content:469:hdoc:3.2.3)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std469, п. 3.2.3: Правила создания общих модулей](../../std/469.md#323) — Диагностика «Пропущен постфикс "ПовтИсп" (CommonModuleNameCached)» проверяет условие пункта 3.2.3 стандарта std469.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameCached.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
