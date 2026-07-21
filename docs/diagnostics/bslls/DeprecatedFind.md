###### bslls:DeprecatedFind

# Использование устаревшего метода "Найти" (DeprecatedFind)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `deprecated`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DeprecatedFind.md
source_path=docs/diagnostics/DeprecatedFind.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=452a8b31fc58ef9640b656d4967cfd3be04939dbdb16877853b15dcb800b89df
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Функция "Найти" является устаревшей. Рекомендуется использовать функцию "СтрНайти".

## Примеры

Неправильно:

```bsl

Если Найти(Сотрудник.Имя, "Борис") > 0 Тогда

КонецЕсли;

```


Правильно:

```bsl

Если СтрНайти(Сотрудник.Имя, "Борис") > 0 Тогда

КонецЕсли;

```

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/DeprecatedFind.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
