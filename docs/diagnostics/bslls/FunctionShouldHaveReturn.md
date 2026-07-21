###### bslls:FunctionShouldHaveReturn

# Функция должна содержать возврат (FunctionShouldHaveReturn)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `suspicious`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/FunctionShouldHaveReturn.md
source_path=docs/diagnostics/FunctionShouldHaveReturn.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=baf7d225e9c5e97d91483ef25616305d4227f60e4436313a8b94b07fe2e166ad
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

`Функция` отличается от `Процедуры` только тем, что обязательно возвращает значение и может быть использована в выражениях.

Исходя из описанного выше утверждения, `функция` не содержащая возврата, сама по себе является ошибочной. Необходимо внести исправления

- реализовать возврат значения, если реализованный метод все-таки является функцией
- переписать функцию на процедуру, если возврат значения не предусматривается

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/FunctionShouldHaveReturn.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
