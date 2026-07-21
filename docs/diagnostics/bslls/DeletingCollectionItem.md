###### bslls:DeletingCollectionItem

# Удаление элемента при обходе коллекции посредством оператора "Для каждого ... Из ... Цикл" (DeletingCollectionItem)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `error`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DeletingCollectionItem.md
source_path=docs/diagnostics/DeletingCollectionItem.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=296eaaff7d82f6a66960eee29b69684ef543d8da583edd6e93c451ff921a0fef
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Не следует непосредственно удалять элементы коллекции при ее обходе через синтаксическую конструкцию
**Для каждого ... Из ... Цикл**. Т.к. при удалении элемента сдвигается индекс следующего элемента.

Например:

```bsl
Для Каждого Элемент Из Коллекция Цикл
   Коллекция.Удалить(Элемент)
КонецЦикла;
```

Как вариант удаляйте элементы с конца:

```bsl
ТекущийИндекс = Числа.ВГраница();
Пока ТекущийИндекс >= 0 Цикл
    Если Числа[ТекущийИндекс] < 10 Тогда
        Числа.Удалить(ТекущийИндекс);
    КонецЕсли;
    ТекущийИндекс = ТекущийИндекс – 1;
КонецЦикла;
```

## Источники

* [1С:Программирование для начинающих. Разработка в системе "1С:Предприятие 8.3"](https://its.1c.ru/db/pubprogforbeginners#content:88:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DeletingCollectionItem.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
