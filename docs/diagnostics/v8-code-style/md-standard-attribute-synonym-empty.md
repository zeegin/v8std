###### v8cs:md-standard-attribute-synonym-empty

# Не задан синоним стандартного реквизита "Родитель" или "Владелец". (md-standard-attribute-synonym-empty)

- Категория: `md`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/md-standard-attribute-synonym-empty.md
source_path=bundles/com.e1c.v8codestyle.md/markdown/ru/md-standard-attribute-synonym-empty.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=2e344a08b3e2217ab89093f99f9fa61e5ee1c845d9e5b07def339e7c0dddb3ce
-->

1.5. При этом для стандартных реквизитов Родитель и Владелец, следует всегда указывать синонимы, отличные от синонимов по умолчанию. Например, в конфигурации имеется справочник Файлы со стандартным реквизитом Владелец типа СправочникСсылка.ПапкиФайлов. В этом случае
неправильно

    * оставлять синоним стандартного реквизита Владелец по умолчанию: «Владелец»;

правильно

    * вложить в синоним прикладной смысл: «Папка» или «Папка с файлом».

## См.

[Пользовательские представления объектов](https://its.1c.ru/db/v8std#content:474:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std474, п. 1.5: Имя, синоним, комментарий](../../std/474.md#15) — Диагностика v8cs:md-standard-attribute-synonym-empty проверяет требование пункта 1.5 стандарта std474.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/md-standard-attribute-synonym-empty.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
