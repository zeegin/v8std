###### bslls:UnusedLocalVariable

# Неиспользуемая локальная переменная (UnusedLocalVariable)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `brainoverload`, `badpractice`, `unused`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnusedLocalVariable.md
source_path=docs/diagnostics/UnusedLocalVariable.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=cd9276f4d7c2788360c3e421e563099f7412c50dcd1d8f1d6cab0a476515037b
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
Программные модули не должны иметь неиспользуемых переменных.

Если локальная переменная объявлена, но не используется, это мертвый код, который следует удалить.
Это улучшит удобство обслуживания, поскольку разработчики не будут удивляться, для чего используется переменная.

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnusedLocalVariable.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
