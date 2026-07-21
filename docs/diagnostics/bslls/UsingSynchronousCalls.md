###### bslls:UsingSynchronousCalls

# Использование синхронных вызовов (UsingSynchronousCalls)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingSynchronousCalls.md
source_path=docs/diagnostics/UsingSynchronousCalls.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=b71b127ebe1a508c13ffe40dfac899c98c20bf9a358a7134cf6f44f8f19722a5
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

При разработке конфигураций, предназначенных для работы в веб-клиенте, запрещено использовать модальные формы и диалоги и синхронные вызовы. В противном случае, конфигурация окажется неработоспособной в ряде веб-браузеров, так как модальные окна не входят в стандарт веб-разработки, а для обеспечения взаимодействия с пользователем требуются асинхронные средства.

### Ограничение диагностики

На данный момент диагностируется **только использование методов глобального контекста**.

Список методов:

|Метод|Английский вариант|
| :-- | :-- |
|ВОПРОС|DOQUERYBOX|
|ОТКРЫТЬФОРМУМОДАЛЬНО|OPENFORMMODAL|
|ОТКРЫТЬЗНАЧЕНИЕ|OPENVALUE|
|ПРЕДУПРЕЖДЕНИЕ|DOMESSAGEBOX|
|ВВЕСТИДАТУ|INPUTDATE|
|ВВЕСТИЗНАЧЕНИЕ|INPUTVALUE|
|ВВЕСТИСТРОКУ|INPUTSTRING|
|ВВЕСТИЧИСЛО|INPUTNUMBER|
|УСТАНОВИТЬВНЕШНЮЮКОМПОНЕНТУ|INSTALLADDIN|
|УСТАНОВИТЬРАСШИРЕНИЕРАБОТЫСФАЙЛАМИ|INSTALLFILESYSTEMEXTENSION|
|УСТАНОВИТЬРАСШИРЕНИЕРАБОТЫСКРИПТОГРАФИЕЙ|INSTALLCRYPTOEXTENSION|
|ПОДКЛЮЧИТЬРАСШИРЕНИЕРАБОТЫСКРИПТОГРАФИЕЙ|ATTACHCRYPTOEXTENSION|
|ПОДКЛЮЧИТЬРАСШИРЕНИЕРАБОТЫСФАЙЛАМИ|ATTACHFILESYSTEMEXTENSION|
|ПОМЕСТИТЬФАЙЛ|PUTFILE|
|КОПИРОВАТЬФАЙЛ|FILECOPY|
|ПЕРЕМЕСТИТЬФАЙЛ|MOVEFILE|
|НАЙТИФАЙЛЫ|FINDFILES|
|УДАЛИТЬФАЙЛЫ|DELETEFILES|
|СОЗДАТЬКАТАЛОГ|CREATEDIRECTORY|
|КАТАЛОГВРЕМЕННЫХФАЙЛОВ|TEMPFILESDIR|
|КАТАЛОГДОКУМЕНТОВ|DOCUMENTSDIR|
|РАБОЧИЙКАТАЛОГДАННЫХПОЛЬЗОВАТЕЛЯ|USERDATAWORKDIR|
|ПОЛУЧИТЬФАЙЛЫ|GETFILES|ПОМЕСТИТЬФАЙЛЫ|PUTFILES|
|ЗАПРОСИТЬРАЗРЕШЕНИЕПОЛЬЗОВАТЕЛЯ|REQUESTUSERPERMISSION|
|ЗАПУСТИТЬПРИЛОЖЕНИЕ|RUNAPP|

## Источники

* [Ограничение на использование модальных окон и синхронных вызовов](https://its.1c.ru/db/v8std/content/703/hdoc/)
* [Отказ от использования модальных окон](https://its.1c.ru/db/metod8dev#content:5272:hdoc)
* [Соответствие синхронных методов асинхронным аналогам](https://its.1c.ru/db/v838doc#bookmark:dev:TI000000438)
* [Асинхронные вызовы расширений и внешних компонентов](http://v8.1c.ru/o7/201412async/index.htm)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std703, п. 5: Ограничение на использование модальных окон и синхронных вызовов](../../std/703.md#5) — Диагностика «Использование синхронных вызовов (UsingSynchronousCalls)» проверяет условие пункта 5 стандарта std703.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingSynchronousCalls.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
