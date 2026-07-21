###### bslls:SeveralCompilerDirectives

# Ошибочное указание нескольких директив компиляции (SeveralCompilerDirectives)

- Тип: Ошибка
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `unpredictable`, `error`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SeveralCompilerDirectives.md
source_path=docs/diagnostics/SeveralCompilerDirectives.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=c33f12a187a7942aa4b7b9618c86dcf56409417af2580a4d139b5e2714325052
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Указание нескольких директив компиляции методу или переменной модуля является ошибкой само по себе. Кроме того, указание нескольких различных директив приводит к неопределенностям: будет ли скомпилирован коде? а если будет, то в каком контексте?

## Примеры

Неправильно

```bsl
&НаСервере
&НаКлиенте
Перем МояПеременная;

&НаСервере
&НаКлиенте
Процедура МояПроцедура()

КонецПроцедуры
```

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/SeveralCompilerDirectives.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
