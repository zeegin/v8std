###### bslls:ProcedureReturnsValue

# Процедура не должна возвращать значение (ProcedureReturnsValue)

- Тип: Ошибка
- Важность: Блокирующий
- Включена по умолчанию: Да
- Теги: `error`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ProcedureReturnsValue.md
source_path=docs/diagnostics/ProcedureReturnsValue.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=8fc915aa79e971d1e1ab1efecaaebf459c34a36321f77b93e6031665925a3004
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

`Процедура`, в отличие от `Функции` не может возвращать значения. Эта диагностика находит процедуры, где есть `Возврат` со значением.

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/ProcedureReturnsValue.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
