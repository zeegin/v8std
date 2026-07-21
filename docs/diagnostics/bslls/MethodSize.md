###### bslls:MethodSize

# Ограничение на размер метода (MethodSize)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MethodSize.md
source_path=docs/diagnostics/MethodSize.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=b9da1f16be0e09e438ea549dd3cf95bb24a8362bfae539c90e8ca84e4218006d
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Существуют громоздкие методы (процедуры и функции), с которыми невозможно эффективно работать именно из-за их огромного размера.
Большой метод зачастую возникает, когда разработчик добавляет в метод новый функционал. "Зачем мне выносить проверку параметров в отдельный метод, если я могу написать ее тут?", "Для чего необходимо выделять метод поиска максимального элемента в массиве, оставим его тут. Так код яснее", - и прочие заблуждения.

Есть два правила рефакторинга большого метода:

- Если при написании метода хочется добавить комментарий в код, необходимо выделить этот функционал в отдельный метод
- Если метод занимает более 50-100 строк кода, следует определить задачи и подзадачи, которые он выполняет, и попробовать вынести подзадачи в отдельный метод

## Источники

- [Рефакторинг архитектуры программного обеспечения: выделение слоев](http://citforum.ru/SE/project/refactor/)
- [Martin Fowler: Refactoring](https://www.refactoring.com/)
- [Инструменты рефакторинга и отказа от модальности](https://v8.1c.ru/o7/201312ref/index.htm)
- [Инструменты рефакторинга в 1С](https://www.koderline.ru/expert/programming/article-vspomogatelnye-funktsii-v-1s/#anchor6)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/MethodSize.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
