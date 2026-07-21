###### bslls:CanonicalSpellingKeywords

# Каноническое написание ключевых слов (CanonicalSpellingKeywords)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CanonicalSpellingKeywords.md
source_path=docs/diagnostics/CanonicalSpellingKeywords.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=da74fc4d67b2e9a05f23c091be786ca4b49e8f3234c579c46c757be30f7e839e
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

В конструкциях встроенного языка ключевые слова пишутся канонически.

### Ключевые слова

| RU                 | EN            |
|--------------------|---------------|
| ВызватьИсключение  | Raise         |
| Выполнить          | Execute       |
| ДобавитьОбработчик | AddHandler    |
| Для                | For           |
| Если               | If            |
| Знач               | Val           |
| И                  | AND, and      |
| Из                 | In            |
| ИЛИ, Или           | OR, Or        |
| Иначе              | Else          |
| ИначеЕсли          | ElsIf         |
| Исключение         | Except        |
| Истина             | True          |
| Каждого, каждого   | Each, each    |
| КонецЕсли          | EndIf         |
| КонецПопытки       | EndTry        |
| КонецПроцедуры     | EndProcedure  |
| КонецФункции       | EndFunction   |
| КонецЦикла         | EndDo         |
| НЕ, Не             | NOT, Not      |
| Неопределено       | Undefined     |
| Перейти            | Goto          |
| Перем              | Var           |
| По                 | To            |
| Пока               | WHile         |
| Попытка            | Try           |
| Процедура          | Procedure     |
| Прервать           | Break         |
| Продолжить         | Continue      |
| Тогда              | Then          |
| Цикл               | Do            |
| УдалитьОбработчик  | RemoveHandler |
| Функция            | Function      |
| Экспорт            | Export        |

### Инструкции препроцессора

| RU                                 | EN                             |
|------------------------------------|--------------------------------|
| ВебКлиент                          | WebClient                      |
| ВнешнееСоединение                  | ExternalConnection             |
| Если                               | If                             |
| И                                  | AND, And                       |
| ИЛИ, Или                           | OR, Or                         |
| Иначе                              | Else                           |
| ИначеЕсли                          | ElsIf                          |
| КонецЕсли                          | EndIf                          |
| КонецОбласти                       | EndRegion                      |
| Клиент                             | Client                         |
| МобильноеПриложениеКлиент          | MobileAppClient                |
| МобильноеПриложениеСервер          | MobileAppServer                |
| МобильныйКлиент                    | MobileClient                   |
| НаКлиенте                          | AtClient                       |
| НаСервере                          | AtServer                       |
| НЕ, Не                             | NOT, Not                       |
| Область                            | Region                         |
| Сервер                             | Server                         |
| Тогда                              | Then                           |
| ТолстыйКлиентОбычноеПриложение     | ThickClientOrdinaryApplication |
| ТолстыйКлиентУправляемоеПриложение | ThickClientManagedApplication  |
| ТонкийКлиент                       | ThinClient                     |

### Директивы компиляции

| RU                             | EN                        |
|--------------------------------|---------------------------|
| НаКлиенте                      | AtClient                  |
| НаСервере                      | AtServer                  |
| НаСервереБезКонтекста          | AtServerNoContext         |
| НаКлиентеНаСервереБезКонтекста | AtClientAtServerNoContext |
| НаКлиентеНаСервере             | AtClientAtServer          |

## Источники

+ [Стандарт: Общие требования к построению конструкций встроенного языка](https://its.1c.ru/db/v8std#content:441:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std441, п. 1: Общие требования к построению конструкций встроенного языка](../../std/441.md#1) — Диагностика «Каноническое написание ключевых слов (CanonicalSpellingKeywords)» проверяет условие пункта 1 стандарта std441.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CanonicalSpellingKeywords.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
