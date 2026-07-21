###### bslls:UsingModalWindows

# Использование модальных окон (UsingModalWindows)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingModalWindows.md
source_path=docs/diagnostics/UsingModalWindows.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=8a52c730aa483284df669d107620598d8e817da6bb9a09fa5d5ca0c798bfac89
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Модальные и всплывающие окна считаются плохим тоном, пользователи привыкли к работе "в одном окне". При разработке конфигураций, предназначенных для работы в веб-клиенте, запрещено использовать модальные формы и диалоги. В противном случае, конфигурация окажется неработоспособной в ряде веб-браузеров, так как модальные окна не входят в стандарт веб-разработки.

### Ограничения диагностики

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
|ПОМЕСТИТЬФАЙЛ|PUTFILE|

## Примеры

```bsl
// Пример "Плохо"
Предупреждение(НСтр("ru = 'Выберите документ!'; en = 'Select a document!'"), 10);

// Пример "Хорошо"
ПоказатьПредупреждение(, НСтр("ru = 'Выберите документ!'; en = 'Select a document!'"), 10);
```

## Источники

* [Ограничение на использование модальных окон и синхронных вызовов](https://its.1c.ru/db/v8std/content/703/hdoc/)
* Полезная информация: [Отказ от использования модальных окон](https://its.1c.ru/db/metod8dev#content:5272:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingModalWindows.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
