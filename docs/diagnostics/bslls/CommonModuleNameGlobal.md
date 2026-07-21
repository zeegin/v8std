###### bslls:CommonModuleNameGlobal

# Пропущен постфикс "Глобальный" (CommonModuleNameGlobal)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`, `brainoverload`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameGlobal.md
source_path=docs/diagnostics/CommonModuleNameGlobal.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=999a72c20f3c9f709940520ff823c9a509f2757033999361cf5fcfd7819eaf46
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Для глобальных модулей добавляется постфикс "Глобальный" (англ. "Global"),
 в этом случае постфикс "Клиент" добавлять не следует.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

РаботаСФайламиГлобальный, InfobaseUpdateGlobal

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->


[Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:469:hdoc:3.2.1)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std469: Правила создания общих модулей](../../std/469.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameGlobal.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
