###### bslls:UsingHardcodeNetworkAddress

# Хранение ip-адресов в коде (UsingHardcodeNetworkAddress)

- Тип: Уязвимость
- Важность: Критичный
- Включена по умолчанию: Да
- Теги: `standard`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingHardcodeNetworkAddress.md
source_path=docs/diagnostics/UsingHardcodeNetworkAddress.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=9b84c48246ea5bdb8e98151f7e376d7707254b05f1942bc2a2ec626058249313
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->

Запрещено хранить в коде:

* Сетевые адреса (ip6, ip4)

Есть как минимум несколько способов правильного хранения такой информации:

* Хранение в константе.
* Хранение в регистре сведений.
* Хранение в отдельном модулей, в котором отключена проверка правила (не рекомендуется).
* Хранение в справочнике, узле плана обмена и т.д..

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->

Неправильно:
```bsl
СетевойАдрес = "192.168.0.1";
```

Правильно:
```bsl
СетевойАдрес = МойМодульПовтИсп.СетевойАдресСервера();
```

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/UsingHardcodeNetworkAddress.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
