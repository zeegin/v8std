###### bslls:MissingCommonModuleMethod

# Обращение к отсутствующему методу общего модуля (MissingCommonModuleMethod)

- Тип: Ошибка
- Важность: Блокирующий
- Включена по умолчанию: Да
- Теги: `error`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MissingCommonModuleMethod.md
source_path=docs/diagnostics/MissingCommonModuleMethod.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=29266eb1f5bd1f827c8b51f67c8a5192dd42e62a74e62bcdbe6feaf75b0d67fc
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->
Правило регистрирует ошибочные обращения к методам общих модулей.
Находятся проблемные варианты
- когда метода нет в указанном общем модуле
- когда метод есть в общем модуле, но метод не является экспортным
- когда у общего модуля отсутствуют исходники, все обращения к любым его методам помечаются как ошибочные

Исключаются варианты
- когда имя переменной совпадает с именем общего модуля
## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

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

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MissingCommonModuleMethod.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
