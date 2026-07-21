###### v8cs:data-exchange-load

# Проверка ОбменДанными.Загрузка в обработчике события (data-exchange-load)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/data-exchange-load.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/data-exchange-load.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=3001aa0b4afc7492d2fd1cfbab1ae08415f4db5f48b2d60441d45ae1ae86ac62
-->

Все действия в процедурах-обработчиков событий ПередЗаписью, ПриЗаписи, ПередУдалением должны выполняться после проверки на ОбменДанными.Загрузка.

Это необходимо для того, чтобы никакая бизнес-логика объекта не выполнялась при записи объекта через механизм обмена данными, поскольку она уже была выполнена для объекта в том узле, где он был создан. В этом случае все данные загружаются в ИБ «как есть», без искажений (изменений), проверок или каких-либо других дополнительных действий, препятствующих загрузке данных.

## Неправильно

```bsl
Процедура ПередЗаписью(Отказ)
// код обработчика
// ...
КонецПроцедуры
```

## Правильно

```bsl
Процедура ПередЗаписью(Отказ)
Если ОбменДанными.Загрузка Тогда
     Возврат;
КонецЕсли;

// код обработчика
// ...
КонецПроцедуры
```

## См.

- https://its.1c.ru/db/v8std#content:773:hdoc
- https://its.1c.ru/db/v8std#content:752:hdoc
- https://its.1c.ru/db/v8std#content:464:hdoc
- https://its.1c.ru/db/v8std#content:465:hdoc

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std464, п. 2: Обработчик события ПередЗаписью](../../std/464.md#2) — Диагностика v8cs:data-exchange-load проверяет требование пункта 2 стандарта std464.
- [#std465, п. 2: Обработчик события ПриЗаписи](../../std/465.md#2) — Диагностика v8cs:data-exchange-load проверяет требование пункта 2 стандарта std465.
- [#std752, п. 2: Обработчик события ПередУдалением](../../std/752.md#2) — Диагностика v8cs:data-exchange-load проверяет требование пункта 2 стандарта std752.
- [#std773, п. 1: Использование признака ОбменДанными.Загрузка в обработчиках событий объекта](../../std/773.md#1) — Диагностика v8cs:data-exchange-load проверяет требование пункта 1 стандарта std773.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/data-exchange-load.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
