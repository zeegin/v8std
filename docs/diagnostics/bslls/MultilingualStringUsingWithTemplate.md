###### bslls:MultilingualStringUsingWithTemplate

# Частично локализованный текст используется в функции СтрШаблон (MultilingualStringUsingWithTemplate)

- Тип: Ошибка
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `error`, `localize`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MultilingualStringUsingWithTemplate.md
source_path=docs/diagnostics/MultilingualStringUsingWithTemplate.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=66d89a9408def8e3975bd3bb434e7d89677deccf8aae8183ba316f1e34287117
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

НСтр в мультиязычной конфигурации имеет разные фрагменты для разных языков.
Если запустить сеанс под кодом языка, которого нет в строке передаваемой в NStr то она вернет пустую строку.
При совместном использовании с СтрШаблон возвращенная из НСтр пустая строка будет выброшено исключение.

## Источники

- [Требования по локализации](https://its.1c.ru/db/v8std/content/763/hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MultilingualStringUsingWithTemplate.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
