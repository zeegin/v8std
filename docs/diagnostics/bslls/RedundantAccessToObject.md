###### bslls:RedundantAccessToObject

# Избыточное обращение к объекту (RedundantAccessToObject)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `standard`, `clumsy`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/RedundantAccessToObject.md
source_path=docs/diagnostics/RedundantAccessToObject.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=e79af16bc8653fa6e81f3a35230341d6367a7eb7b0d28d5ce5e909afd7b5be49
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
В формах и модулях объектов избыточно обращаться к реквизитам через ЭтотОбъект. В общих модулях избыточно обращаться к методам через свое имя, кроме модулей с ПовтИсп.

## Примеры
В модуле объекта документа с реквизитом `Контрагент` неправильно писать
```bsl
ЭтотОбъект.Контрагент = ПолучитьКонтрагента();
```

правильно будет обратиться к реквизиту напрямую
```bsl
Контрагент = ПолучитьКонтрагента();
```

В общем модуле `ОбщегоНазначения` неправильным будет такой вызов метода
```bsl
ОбщегоНазначения.СообщитьПользователю("ru = 'Привет мир!'");
```

а правильным
```bsl
СообщитьПользователю("ru = 'Привет мир!'");
```

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/RedundantAccessToObject.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
