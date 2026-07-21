###### bslls:UnaryPlusInConcatenation

# Унарный плюс в конкатенации строк (UnaryPlusInConcatenation)

- Тип: Ошибка
- Важность: Блокирующий
- Включена по умолчанию: Да
- Теги: `suspicious`, `brainoverload`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnaryPlusInConcatenation.md
source_path=docs/diagnostics/UnaryPlusInConcatenation.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=eb9db93963bf0cf83db929c281b9af38b5a94998199112340d706445197c3d25
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

При конкатенации строк разработчик может ошибочно написать код вида Строка + + Строка2, т.е. второй плюс платформа распознает как унарный и попытается выолнить преобразование к числу, что в большинстве случаев приведет к ошибке исполнения

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnaryPlusInConcatenation.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
