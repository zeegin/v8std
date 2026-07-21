###### bslls:WrongUseFunctionProceedWithCall

# Некорректное использование функции ПродолжитьВызов() (WrongUseFunctionProceedWithCall)

- Тип: Ошибка
- Важность: Блокирующий
- Включена по умолчанию: Да
- Теги: `error`, `suspicious`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/WrongUseFunctionProceedWithCall.md
source_path=docs/diagnostics/WrongUseFunctionProceedWithCall.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=6efbf16de0f404a787615de878e31ff1631b5720466bb8ee4bbdd6d6102dd2f1
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Использование функции `ПродолжитьВызов` не в методах расширения с аннотацией `&Вместо` приведет к ошибке времени выполнения.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

```bsl
&НаКлиенте
Процедура Тест()

    // этот код возможно был внесен копипастой, при переносе из расширения
    ПродолжитьВызов(); // Срабатывание здесь

КонецПроцедуры
```

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->

Источник: [Расширения конфигураций. Функциональность -> Модули](https://its.1c.ru/db/pubextensions#content:54:1)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/WrongUseFunctionProceedWithCall.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
