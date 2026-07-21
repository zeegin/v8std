###### v8cs:document-post-in-privileged-mode

# В документе, предполагающем проведение, не установлен флаг "Привилегированный режим при проведении / отмене проведения" (document-post-in-privileged-mode)

- Категория: `md`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/document-post-in-privileged-mode.md
source_path=bundles/com.e1c.v8codestyle.md/markdown/ru/document-post-in-privileged-mode.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=cc03d492d7b6fad23b51c23e0c4809ced52c70b6706b854f71f0ea1fb35403ec
-->

1.7. Во всех документах, предполагающих проведение, должны быть
выставлены флаги «Привилегированный режим при проведении» и
«Привилегированный режим при отмене проведения», поэтому не нужно
создавать роли, дающие права на изменение регистров, подчиненных
регистраторам.

Исключение: документы, предназначенные для непосредственной
корректировки записей регистров, могут проводиться с проверкой прав
доступа, но в этом случае необходимо предусмотреть роли, дающие права на
изменение регистров.

## Неправильно

## Правильно

## См.

[Настройка ролей и прав доступа](https://its.1c.ru/db/v8std#content:689:hdoc:1.7)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std689: Настройка ролей и прав доступа](../../std/689.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.md/markdown/ru/document-post-in-privileged-mode.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
