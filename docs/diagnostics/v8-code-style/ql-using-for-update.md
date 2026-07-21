###### v8cs:ql-using-for-update

# Запрос содержит конструкцию "ДЛЯ ИЗМЕНЕНИЯ" (ql-using-for-update)

- Категория: `ql`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.ql/markdown/ru/ql-using-for-update.md
source_path=bundles/com.e1c.v8codestyle.ql/markdown/ru/ql-using-for-update.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=8007c2a9c0acf28ec556c70ce2ffaf6686d0e0d403349c22d9c050dd2da3e14b
-->

Конструкция ДЛЯ ИЗМЕНЕНИЯ позволяет заблаговременно заблокировать некоторые данные (которые могут читаться транзакцией другого соединения)
уже при считывании, чтобы исключить взаимные блокировки при записи. Однако, при использовании в конфигурации управляемого режима блокировок, данная конструкция игнорируется и
следовательно, не имеет смысла.

## Неправильно

```bsl
ВЫБРАТЬ
  Док.Ссылка,
ИЗ
  Документ.РеализацияТоваров Док
ГДЕ
  Док.Ссылка = &ДокументСсылка
ДЛЯ ИЗМЕНЕНИЯ РегистрНакопления.КонтрагентыВзаиморасчетыКомпании.Остатки // Блокирующие чтение таблицы остатков регистра для разрешения
```

## Правильно

```bsl
ВЫБРАТЬ
  Док.Ссылка,
ИЗ
  Документ.РеализацияТоваров Док
ГДЕ
  Док.Ссылка = &ДокументСсылка
```

## См.

- [Использование управляемого режима блокировки](https://its.1c.ru/db/v8std#content:460:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std460: Использование управляемого режима блокировки](../../std/460.md#std460) — Диагностика v8cs:ql-using-for-update проверяет требование пункта std460 стандарта std460.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.ql/markdown/ru/ql-using-for-update.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
