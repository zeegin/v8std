###### bslls:UseLessForEach

# Бесполезный перебор коллекции (UseLessForEach)

- Тип: Ошибка
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `clumsy`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UseLessForEach.md
source_path=docs/diagnostics/UseLessForEach.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=e838b027a777b39328ba00b7e5bc00230ede11190602487cf14681876b71cb87
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Отстутствие итератора в теле цикла указывает на бесполезный перебор коллекции либо на ошибку в теле цикла.

## Примеры

Неправильно

```Bsl

Для Каждого Итератор Из Коллекция Цикл

    ВыполнитьДействиеНадЭлементом(Коллекция);

КонецЦикла;

```

Правильно

```Bsl

Для Каждого Итератор Из Коллекция Цикл

    ВыполнитьДействиеНадЭлементом(Итератор);

КонецЦикла;

```

```bsl

ВыполнитьДействиеНадКоллекцией(Коллекция);

```

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UseLessForEach.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
