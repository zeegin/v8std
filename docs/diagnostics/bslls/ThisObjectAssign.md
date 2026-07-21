###### bslls:ThisObjectAssign

# Присвоение значения свойству ЭтотОбъект (ThisObjectAssign)

- Тип: Ошибка
- Важность: Блокирующий
- Включена по умолчанию: Да
- Теги: `error`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ThisObjectAssign.md
source_path=docs/diagnostics/ThisObjectAssign.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=a6380e3562f94dd6027f03d0ad4077cf7306f479b73b39a19ef181dbc78e4c48
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
В модулях управляемых форм и общих модулях не должно быть переменной с именем "ЭтотОбъект".

Часто ошибка появляется при поднятии версии режима совместимости конфигурации т.к. в версиях до 8.3.3
свойство "ЭтотОбъект" у управляемых форм и общих модулей отсутствовало. И могло быть
использовано как переменная.

## Примеры

Неправильно:
```bsl

ЭтотОбъект = РеквизитФормыВЗначение("Объект");

```

## Источники

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ThisObjectAssign.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
