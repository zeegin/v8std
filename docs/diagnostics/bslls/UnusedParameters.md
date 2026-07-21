###### bslls:UnusedParameters

# Неиспользуемый параметр (UnusedParameters)

- Тип: Дефект кода
- Важность: Важный
- Включена по умолчанию: Да
- Теги: `design`, `unused`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnusedParameters.md
source_path=docs/diagnostics/UnusedParameters.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=323fa45dfb6b6cb89c9fed9f1e22c01f1b626a7e6275f3c4ac1ecedaca6dbd41
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
Методы не должны содержать неиспользуемых параметров.

## Примеры

```bsl
Функция СложитьДваЧисла(Знач ПервоеЧисло, Знач ВтороеЧисло, Знач ЛишнийПараметр)

    Возврат ПервоеЧисло + ВтороеЧисло;

КонецФункции
```

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UnusedParameters.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
