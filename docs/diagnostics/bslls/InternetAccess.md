###### bslls:InternetAccess

# Обращение к Интернет-ресурсам (InternetAccess)

- Тип: Уязвимость
- Важность: Важный
- Включена по умолчанию: Нет
- Теги: `suspicious`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/InternetAccess.md
source_path=docs/diagnostics/InternetAccess.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=13f0383bb6f56b16b4a746ac461d771cf4990fc514bf09543398e968681af5a3
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->
Проверьте обращение к Интернет-ресурсам и набор передаваемых данных для исключения передачи конфиденциальной или защищенной информации.

## Примеры
<!-- В данном разделе приводятся примеры, на которые диагностика срабатывает, а также можно привести пример, как можно исправить ситуацию -->
```bsl
HTTPСоединение = Новый HTTPСоединение("zabbix.localhost", 80); // замечание
FTPСоединение = Новый FTPСоединение(Сервер, Порт, Пользователь, Пароль); // замечание
```

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->
<!-- Примеры источников

* Источник: [Стандарт: Тексты модулей](https://its.1c.ru/db/v8std#content:456:hdoc)
* Полезная информация: [Отказ от использования модальных окон](https://its.1c.ru/db/metod8dev#content:5272:hdoc)
* Источник: [Cognitive complexity, ver. 1.4](https://www.sonarsource.com/docs/CognitiveComplexity.pdf) -->

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к стандарту

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/InternetAccess.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
