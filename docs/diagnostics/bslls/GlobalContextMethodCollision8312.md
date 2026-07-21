###### bslls:GlobalContextMethodCollision8312

# Конфликт имен методов с методами глобального контекста (GlobalContextMethodCollision8312)

- Тип: Ошибка
- Важность: Блокирующий
- Включена по умолчанию: Да
- Теги: `error`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/GlobalContextMethodCollision8312.md
source_path=docs/diagnostics/GlobalContextMethodCollision8312.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=cae62c71f1a4bf37413d226a3deff312060cc71a1bc517f335f8e391f59b7d05
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Начиная с версии платформы `8.3.12`, реализованы новые методы глобального контекста, которые могут совпаcть по имени с существующими функциями в коде конфигурации прикладного решений.

Метод|Английский вариант
:-: | :-:
ПроверитьБит|CheckBit
ПроверитьПоБитовойМаске|CheckByBitMask
УстановитьБит|SetBit
ПобитовоеИ|BitwiseAnd
ПобитовоеИли|BitwiseOr
ПобитовоеНе|BitwiseNot
ПобитовоеИНе|BitwiseAndNot
ПобитовоеИсключительноеИли|BitwiseXor
ПобитовыйСдвигВлево|BitwiseShiftLeft
ПобитовыйСдвигВправо|BitwiseShiftRight

Необходимо существующие функции конфигурации прикладного решения переименовать или удалить, заменив обращение к ним на методы глобального контекста.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->
<!-- Примеры источников

* Источник: [Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:456:hdoc)
* Полезная информация: [Отказ от использования модальных окон](https://its.1c.ru/db/metod8dev#content:5272:hdoc)
* Источник: [Cognitive complexity, ver. 1.4](https://www.sonarsource.com/docs/CognitiveComplexity.pdf) -->

* Источник: [Перевод конфигураций на платформу "1С:Предприятие 8.3" без режима совместимости с версией 8.2](https://its.1c.ru/db/metod8dev#content:5293:hdoc:pereimenovaniya_metodov_i_svojstv)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/GlobalContextMethodCollision8312.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
