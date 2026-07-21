###### bslls:ReservedParameterNames

# Зарезервированные имена параметров (ReservedParameterNames)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ReservedParameterNames.md
source_path=docs/diagnostics/ReservedParameterNames.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=4e5547c8278aa9c74d0d541432d554cff5eb5c264ec825d0c0ebb6dea96a437a
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
Если имя параметра совпадает с именем системного перечисления, то невозможно будет обратиться к значениям этого системного перечисления, потому что параметр его скроет.
Синтаксическая проверка кода модуля не выявит такую ошибку. Чтобы предотвратить эту ситуацию имя параметра не должно совпадать с именами системных перечислений.
Список зарезервированных слов задается регулярным выражением.
Поиск производится без учета регистра символов.

**Примеры настройки:**

"ВидГруппыФормы|ВидПоляФормы"

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->

* Источник: [Стандарт: Параметры процедур и функций](https://its.1c.ru/db/v8std/content/640/hdoc)
* Источник: [Стандарт: Правила образования имен переменных](https://its.1c.ru/db/v8std#content:454:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ReservedParameterNames.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
