###### bslls:AssignToReadOnlyProperty

# Присвоение значения свойству, доступному только для чтения (AssignToReadOnlyProperty)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `suspicious`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/AssignToReadOnlyProperty.md
source_path=docs/diagnostics/AssignToReadOnlyProperty.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=ebb466bf8f600d45be5a0d7579668acbaddde879ec2201ede4515dcd2c86627b
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Подсвечивает попытку присвоить значение свойству платформенного типа, объявленному в синтакс-помощнике как «Только чтение».
Такое присваивание приведёт к ошибке во время исполнения. Информация о режиме доступа берётся из синтакс-помощника установленной платформы 1С (через `bsl-context`) или из встроенного JSON-fallback.

Диагностика покрывает только цепочки `Что-то.Свойство = …` с доступом через точку. Индексаторы (`coll[0] = …`) и параметры процедур с режимом «Передан как параметр» здесь не диагностируются.

## Примеры

```bsl
// плохо: свойство Метаданные у ссылочного типа доступно только для чтения
Документ.Метаданные = "что-то";

// хорошо
СвободныйОбъект.Дата = ТекущаяДата();
```

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/AssignToReadOnlyProperty.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
