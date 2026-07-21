###### bslls:UsingHardcodePath

# Хранение путей к файлам в коде (UsingHardcodePath)

- Тип: Ошибка
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingHardcodePath.md
source_path=docs/diagnostics/UsingHardcodePath.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=d269d900455750813fc0685a5d5a7d9f4a1305fd51f995a2e5370b9982f7d8a5
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Запрещено хранить в коде:

* Пути к файлам и папкам (Windows, Unix)

Есть как минимум несколько способов правильного хранения такой информации:

* Хранение в константе.
* Хранение в регистре сведений.
* Хранение в отдельном модулей, в котором отключена проверка правила (не рекомендуется).
* Хранение в справочнике, узле плана обмена и т.д..

### Особенности

При поиске путей Windows / Unix происходит проверка и на URL в строке. Ключевые слова поиска URL:
* ``http``
* ``https``
* ``ftp``

## Примеры

Неправильно:

```bsl
КаталогОбмена = "c:/обмен/обменданными";
```

Правильно:

```bsl
КаталогОбмена = Константы.КаталогОбмена.Получить();
```

или

```bsl
КаталогОбмена = ОбменДаннымиПовтИсп.КаталогОбмена();
```

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingHardcodePath.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
