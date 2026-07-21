###### bslls:CrazyMultilineString

# Безумные многострочные литералы (CrazyMultilineString)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `badpractice`, `suspicious`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CrazyMultilineString.md
source_path=docs/diagnostics/CrazyMultilineString.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=f46081784db016553588b918d461f0d309fd517aadb3b883e2c98f94326f6599
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

В исходном тексте многострочные константы могут задаваться двумя способами:

- 'классический', в котором используется символ переноса строки и конкатенация строк
- 'странный', при котором строки разделяются пробельными символами

Второй способ усложняет восприятие, при его использовании проще допустить и пропустить ошибку.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

Усложняет восприятие:

```bsl
Строка = "ВВВ" "СС"
"Ф";
```

Классический вариант:

```bsl
Строка = "ВВВ" + "СС"
         + "Ф";
```

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->
<!-- Примеры источников

* Источник: [Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:456:hdoc)
* Полезная информация: [Отказ от использования модальных окон](https://its.1c.ru/db/metod8dev#content:5272:hdoc)
* Источник: [Cognitive complexity, ver. 1.4](https://www.sonarsource.com/docs/CognitiveComplexity.pdf) -->

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CrazyMultilineString.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
