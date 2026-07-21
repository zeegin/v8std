###### bslls:CompilationDirectiveLost

# Директивы компиляции методов (CompilationDirectiveLost)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `standard`, `unpredictable`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CompilationDirectiveLost.md
source_path=docs/diagnostics/CompilationDirectiveLost.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=daa2b48ab17d7956f58a149a7198a2881179293d81792e5e4e07107bebc6b02d
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
У всех методов управляемых форм и команд должны быть указаны директивы компиляции.

## Примеры

#### Неправильно:
```bsl
Процедура ПриСозданииНаСервере()
...
КонецПроцедуры
```

#### Правильно:
```bsl
&НаСервере
Процедура ПриСозданииНаСервере()
...
КонецПроцедуры
```

## Источники

* Полезная информация: [Разработка интерфейса прикладных решений на платформе "1С:Предприятие 8"](https://its.1c.ru/db/pubv8devui#content:189:1)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/CompilationDirectiveLost.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
