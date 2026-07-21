###### bslls:CompilationDirectiveNeedLess

# Лишняя директива компиляции (CompilationDirectiveNeedLess)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `clumsy`, `standard`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CompilationDirectiveNeedLess.md
source_path=docs/diagnostics/CompilationDirectiveNeedLess.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=71ee198f34b37cdbf8daba9b8045f52dbd9cd64f4202e0a7eb9d2a9f0837d6d9
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Директивы компиляции:

```bsl
&НаКлиенте (&AtClient)
&НаСервере (&AtServer)
&НаСервереБезКонтекста (&AtServerNoContext)
```

Следует применять только в коде модулей управляемых форм и в коде модулей команд. В остальных модулях рекомендуется
применять инструкции препроцессору.

В серверных или клиентских общих модулях контекст исполнения очевиден, поэтому смысла в директивах компиляции нет.
В общих модулях с признаками клиент и сервер применение директив компиляции затрудняет понимание, какие же
процедуры (функции) доступны в конечном итоге.

## Источники
* Источник: [Использование директив компиляции и инструкций препроцессора](https://its.1c.ru/db/v8std#content:439:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std439, п. 1: Использование директив компиляции и инструкций препроцессора](../../std/439.md#1) — Диагностика «Лишняя директива компиляции (CompilationDirectiveNeedLess)» проверяет условие пункта 1 стандарта std439.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CompilationDirectiveNeedLess.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
