###### bslls:CommonModuleNameClientServer

# Пропущен постфикс "КлиентСервер" (CommonModuleNameClientServer)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameClientServer.md
source_path=docs/diagnostics/CommonModuleNameClientServer.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=fb1e3d55d52a699e80ac90b7d19fcd079bbdf9814907867d401a406fe3e5b20d
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Для того чтобы избежать дублирования кода, рекомендуется создавать клиент-серверные общие модули с теми процедурами и функциями, содержание которых одинаково на сервере и на клиенте. Такие процедуры и функции размещаются в общих модулях с признаками:

* Клиент (управляемое приложение)
* Сервер (флажок Вызов сервера сброшен)
* Клиент (обычное приложение)
* Внешнее соединение

Общие модули этого вида именуются с постфиксом "КлиентСервер" (англ. "ClientServer").

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

РаботаСФайламиКлиентСервер, ОбщегоНазначенияКлиентСервер, UsersClientServer

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->


[Стандарт: Правила создания общих модулей](https://its.1c.ru/db/v8std#content:469:hdoc:2.4)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std469, п. 2.4: Правила создания общих модулей](../../std/469.md#24) — Диагностика «Пропущен постфикс "КлиентСервер" (CommonModuleNameClientServer)» проверяет условие пункта 2.4 стандарта std469.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameClientServer.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
