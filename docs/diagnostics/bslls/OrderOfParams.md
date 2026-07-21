###### bslls:OrderOfParams

# Порядок параметров метода (OrderOfParams)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `design`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/OrderOfParams.md
source_path=docs/diagnostics/OrderOfParams.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=14e75417c99cc9e2b7aa921f361cbd61b64b9cfcd019ce208d80d55b23c50237
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Необязательные параметры (параметры со значениями по умолчанию) должны располагаться после обязательных параметров (без значений по умолчанию).

## Примеры

```bsl
Функция КурсВалютыНаДату(Валюта, Дата = Неопределено) Экспорт
```

## Источники

* [Стандарт: Параметры процедур и функций](https://its.1c.ru/db/v8std#content:640:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std640: Параметры процедур и функций](../../std/640.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/OrderOfParams.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
