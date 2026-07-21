###### v8cs:form-dynamic-list-item-title

# Пустой заголовок для колонок динамического списка (form-dynamic-list-item-title)

- Категория: `form`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/form-dynamic-list-item-title.md
source_path=bundles/com.e1c.v8codestyle.form/markdown/ru/form-dynamic-list-item-title.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=622d9e73793db9490a075e1555c7bdbe58601105407f403d58a6720efac49cc1
-->

Следует задавать заголовок для колонок динамического списка, получающихся в запросе комбинацией других колонок или для которых задан свой псевдоним.
Нельзя опираться на автоматически сгенерированный заголовок по имени/псевдониму.


Примеры, когда заголовок колонок следует задавать в явном виде:

```bsl
ВЫБРАТЬ
    Таблица.Поле1 КАК Поле2
    ВЫРАЗИТЬ(Таблица.Поле1 КАК СТРОКА(100)) КАК Поле3
```

В таком случае, когда поле создается в запросе и ему присваивается имя, то синоним не "подтягивается" автоматически из метаданных,
т.к. не существует реквизита, связанного с этим полем.
Инструментом редактирования текстов интерфейсов не находится заголовок для колонок в динамическом списке, которым задан псевдоним в запросе.
Имя колонки динамического списка должно быть задано, даже если заголовок поля не выводится на форму,
так как имена колонок выводятся пользователю при настройке полей формы (команда Еще - Изменить форму...).


## См.

- [Элементы форм: требования по локализации](https://its.1c.ru/db/v8std#content:765:hdoc:4)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std765, п. 4: Элементы форм: требования по локализации](../../std/765.md#4) — Диагностика v8cs:form-dynamic-list-item-title проверяет требование пункта 4 стандарта std765.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.form/markdown/ru/form-dynamic-list-item-title.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
