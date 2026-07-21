###### bslls:UsingHardcodeSecretInformation

# Хранение конфиденциальной информации в коде (UsingHardcodeSecretInformation)

- Тип: Уязвимость
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingHardcodeSecretInformation.md
source_path=docs/diagnostics/UsingHardcodeSecretInformation.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=99d173230b8bf5046081f9b9426a1bec3f83ac983d0ef2c9dffd07e337b075a8
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики

Запрещено хранить конфиденциальную информацию в коде. Список конфиденциальной информации:

* Пароли
* Персональные ключи доступа

Если в проекте 1С используется подсистема БСП, то хранение паролей можно организовать через безопасное хранилище.

### Дополнительно

В значений паролей исключаются строки, где все символы `*`:

```bsl
Пароль = "**********";
```

## Примеры

Неправильно:

```bsl
Пароль = "12345";
```

Правильно:

```bsl
Пароли = ОбщегоНазначения.ПрочитатьДанныеИзБезопасногоХранилища("ИдентификаторХранения", "Пароль");
Пароль = Пароли.Пароль;
```

## Источники

* [Стандарт: Безопасное хранение паролей](https://its.1c.ru/db/v8std#content:740:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std740, п. 3.2: Безопасное хранение паролей](../../std/740.md#32) — Диагностика «Хранение конфиденциальной информации в коде (UsingHardcodeSecretInformation)» проверяет условие пункта 3.2 стандарта std740.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingHardcodeSecretInformation.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
