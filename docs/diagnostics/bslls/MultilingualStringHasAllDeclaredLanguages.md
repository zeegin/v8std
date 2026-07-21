###### bslls:MultilingualStringHasAllDeclaredLanguages

# Есть локализованный текст для всех заявленных в конфигурации языков (MultilingualStringHasAllDeclaredLanguages)

- Тип: Ошибка
- Важность: Незначительный
- Включена по умолчанию: Да
- Теги: `error`, `localize`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MultilingualStringHasAllDeclaredLanguages.md
source_path=docs/diagnostics/MultilingualStringHasAllDeclaredLanguages.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=9f1d05bf489aa266a775adde6d5c3d27a3d68e904b41013dd628763e31dec493
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

НСтр в мультиязычной конфигурации имеет разные фрагменты для разных языков.
Если запустить сеанс под кодом языка, которого нет в строке передаваемой в NStr то она вернет пустую строку.

## Источники

- [требования по локализации](https://its.1c.ru/db/v8std/content/763/hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MultilingualStringHasAllDeclaredLanguages.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
