###### bslls:DeprecatedMessage

# Ограничение на использование устаревшего метода "Сообщить" (DeprecatedMessage)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `standard`, `deprecated`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DeprecatedMessage.md
source_path=docs/diagnostics/DeprecatedMessage.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=d66d3edba3dffb7f2b3bea89c3a8387dbfa50c5f4f9001329ef174273015e1d4
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Для вывода сообщений пользователю во всех случаях следует использовать объект СообщениеПользователю, даже когда сообщение не «привязывается» к некоторому элементу управления формы. Метод Сообщить применять не следует.

*При использовании в конфигурации Библиотеки стандартных подсистем рекомендуется использовать процедуру СообщитьПользователю общего модуля ОбщегоНазначенияКлиентСервер, которая работает с объектом СообщениеПользователю.*

## Источники

* [Стандарт: Ограничение на использование метода Сообщить](https://its.1c.ru/db/v8std#content:418:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std418: Ограничение на использование метода Сообщить](../../std/418.md)

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DeprecatedMessage.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
