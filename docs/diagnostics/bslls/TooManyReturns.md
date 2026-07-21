###### bslls:TooManyReturns

# Метод не должен содержать много возвратов (TooManyReturns)

- Тип: Дефект кода
- Важность: Незначительный
- Включена по умолчанию: Нет
- Теги: `brainoverload`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/TooManyReturns.md
source_path=docs/diagnostics/TooManyReturns.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=2d192bb176820a3deb3d0c82c60730fde924319e0d314a9b08814b244bfda0d1
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Большое количество возвратов в методе (процедуре или функции) увеличивает его сложность и снижает производительность и восприятие.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

Пример плохого метода

```bsl
Функция Пример(Условие)
    Если Условие = 1 Тогда
        Возврат "Проверка пройдена";
    ИначеЕсли Условие = 2 Тогда
        ВыполнитьДействие();
        Возврат "Проверка не пройдена";
    ИначеЕсли Условие > 7 Тогда
        Если ВыполнитьПроверку(Условие) Тогда
            Возврат "Проверка пройдена";
        Иначе
            Возврат "Проверка не пройдена";
        КонецЕсли;
    КонецЕсли;
    Возврат "";
КонецФункции
```

## Источники

* [Why Many Return Statements Are a Bad Idea in OOP](https://www.yegor256.com/2015/08/18/multiple-return-statements-in-oop.html)
* [JAVA: Methods should not have too many return statements](https://rules.sonarsource.com/java/RSPEC-1142)
* [Почему ранний возврат из функций так важен?](https://habr.com/ru/post/348074/)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/TooManyReturns.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
