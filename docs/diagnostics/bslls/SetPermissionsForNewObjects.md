###### bslls:SetPermissionsForNewObjects

# Флажок «Устанавливать права для новых объектов» должен быть установлен только у роли ПолныеПрава (SetPermissionsForNewObjects)

- Тип: Уязвимость
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`, `design`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SetPermissionsForNewObjects.md
source_path=docs/diagnostics/SetPermissionsForNewObjects.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=bd0816a1f1102f3de282846565941b8df085cb3eddf31086c3fc0f5e1aa0a657
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
При добавлении новой роли может быть ошибочно установлен атрибут "Устанавливать права для новых объектов", что приведет к накоплению в этой роли прав на все добавленные после неё объекты и избыточные права у пользователей с этой ролью.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

## Источники

* Источник: [Стандарт: Установка прав для новых объектов и полей объектов](https://its.1c.ru/db/v8std/content/532/hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std532, п. 2: Установка прав для новых объектов и полей объектов](../../std/532.md#2) — Диагностика «Флажок «Устанавливать права для новых объектов» должен быть установлен только у роли ПолныеПрава (SetPermissionsForNewObjects)» проверяет условие пункта 2 стандарта std532.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SetPermissionsForNewObjects.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
