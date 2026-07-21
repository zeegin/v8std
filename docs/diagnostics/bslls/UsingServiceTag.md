###### bslls:UsingServiceTag

# Использование служебных тегов (UsingServiceTag)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingServiceTag.md
source_path=docs/diagnostics/UsingServiceTag.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=04c278cec8089c07ffcb8bc5f3ac8bd9099d84c6f97ca11785c4a230452c88c3
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Диагностика отлавливает использование служебных тегов в комментариях. Список тегов:

* TODO
* FIXME
* !!
* @
* MRG
* ОТЛАДКА
* ДЛЯ ОТЛАДКИ
* КОНСТРУКТОР_ЗАПРОСА_С_ОБРАБОТКОЙ_РЕЗУЛЬТАТА
* КОНСТРУКТОР_ДВИЖЕНИЙ_РЕГИСТРОВ
* КОНСТРУКТОР_ПЕЧАТИ
* КОНСТРУКТОР_ВВОДА_НА_ОСНОВАНИИ
* Вставить содержимое обработчика
* Insert handler code
* Insert handler contents
* Paste handler content

Список тегов так же можно расширить через настройки.

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingServiceTag.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
