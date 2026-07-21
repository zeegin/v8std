###### bslls:UsingObjectNotAvailableUnix

# Использование объектов недоступных в Unix системах (UsingObjectNotAvailableUnix)

- Тип: Ошибка
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `standard`, `lockinos`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingObjectNotAvailableUnix.md
source_path=docs/diagnostics/UsingObjectNotAvailableUnix.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=33bad7635b536e5023ef58eb911045d8610b69d52ca460df1abf2028b16d162a
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

В ОС `Linux` недоступны механизмы `COM`, `OLE`, `ActiveDocument`. Для интеграции необходимо использовать другие средства, например файловый обмен в формате XML или web-сервисы.
Внешние компоненты, реализованные по COM-технологии, рекомендуется переработать с использованием технологии `NativeAPI`.

Отслеживаемые механизмы, недоступные в Linux:

* `COMОбъект`
* `Почта`

**Проверка значения выполнения условия пока не выполняется.**

### Дополнительно

При проверке использования недоступных объектов в Linux учитываются условия, в которых можно найти следующий ключевые слова:

* `Linux_x86`
* `Windows`
* `MacOs`

## Примеры

```bsl
Компонента = Новый COMОбъект("System.Text.UTF8Encoding");
```

или

```bsl
Почта = Новый Почта;
```
Вместо этого можно использовать `ЗапуститьПриложение()`.

```bsl
СистемнаяИнформация = Новый СистемнаяИнформация();
Если Не СистемнаяИнформация.ТипПлатформы = ТипПлатформы.Linux_x86 Или ТипПлатформы.Linux_x86_64 Тогда
	Почта = Новый Почта;
КонецЕсли
```

## Источники

* [Особенности разработки кроссплатформенных прикладных решений](https://its.1c.ru/db/v8314doc#bookmark:dev:TI000001208)
* [Особенности работы клиентского приложения под управлением ОС Linux](https://its.1c.ru/db/v8314doc#bookmark:dev:TI000001283)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingObjectNotAvailableUnix.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
