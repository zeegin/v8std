###### bslls:CommonModuleNameFullAccess

# Пропущен постфикс "ПолныеПрава" (CommonModuleNameFullAccess)

- Тип: Потенциальная уязвимость
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameFullAccess.md
source_path=docs/diagnostics/CommonModuleNameFullAccess.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=472424689238f07e7acac54c3f14f0198a07cb1fd3d472da1d9fb33de384b533
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Модули, выполняющиеся в привилегированном режиме, имеющие признак Привилегированный,
именуются с постфиксом "ПолныеПрава" (англ. "FullAccess").

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

Например: РаботаСФайламиПолныеПрава, FilesFullAccess

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->


[Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:469:hdoc:3.2.2)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std469: Правила создания общих модулей](../../std/469.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CommonModuleNameFullAccess.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
