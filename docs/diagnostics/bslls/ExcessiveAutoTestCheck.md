###### bslls:ExcessiveAutoTestCheck

# Избыточная проверка параметра АвтоТест (ExcessiveAutoTestCheck)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`, `deprecated`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ExcessiveAutoTestCheck.md
source_path=docs/diagnostics/ExcessiveAutoTestCheck.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=4d8cbc1f8eada331fa970dd5ae7b0acd72a46106aae735aaf8c757a78726a3c1
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
Стандарт 772 "Взаимодействие со средствами автоматизированного тестирования" был отменен.
В связи с этим, больше не нужна проверка параметра "АвтоТест" в коде форм.

## Примеры
```bsl
Если Параметры.Свойство("АвтоТест") Тогда
    Возврат;
КонецЕсли;
```

и обработчике ОбработкаЗаполнения модуля объекта (набора записей):

```bsl
// Пропускаем обработку, чтобы гарантировать получение формы при передаче параметра "АвтоТест".
Если ДанныеЗаполнения = "АвтоТест" Тогда
    Возврат;
КонецЕсли;
```

## Источники
* Источник: [Стандарт: Тексты модулей пункт 3](https://its.1c.ru/db/v8std#content:456:hdoc:3)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std456, п. 3: Тексты модулей](../../std/456.md#3) — Диагностика «Избыточная проверка параметра АвтоТест (ExcessiveAutoTestCheck)» проверяет условие пункта 3 стандарта std456.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ExcessiveAutoTestCheck.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
