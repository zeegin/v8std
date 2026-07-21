###### v8cs:missing-temporary-file-deletion

# Отсутствует удаление временного файла после использования. (missing-temporary-file-deletion)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/missing-temporary-file-deletion.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/missing-temporary-file-deletion.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=a8bea9fa27bf5a9d3aae12d0813f9b2004d26483581e2f7b3af3df903b66c634
-->

После окончания работы с временным файлом или каталогом, его необходимо удалить самостоятельно. Нельзя рассчитывать на автоматическое удаление файлов и каталогов при следующем запуске платформы, это может привести к исчерпанию свободного места в каталоге временных файлов.

## Неправильно

```bsl

ИмяПромежуточногоФайла = ПолучитьИмяВременногоФайла("xml");
Данные.Записать(ИмяПромежуточногоФайла);
// далее нет удаления файла

```

## Правильно

```bsl

ИмяПромежуточногоФайла = ПолучитьИмяВременногоФайла("xml");
Данные.Записать(ИмяПромежуточногоФайла);

// Работа с файлом
...

// Удаляем временный файл
Попытка
   УдалитьФайлы(ИмяПромежуточногоФайла);
Исключение
   ЗаписьЖурналаРегистрации(НСтр("ru = 'Мой механизм.Действие'"), УровеньЖурналаРегистрации.Ошибка, , , ПодробноеПредставлениеОшибки(ИнформацияОбОшибке()));
КонецПопытки;

```

## См.

- [Инструкции по разработке на 1С - Доступ к файловой системе из кода конфигурации, пункт 4](https://its.1c.ru/db/v8std#content:542:hdoc:4)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std542, п. 4: Доступ к файловой системе из кода конфигурации](../../std/542.md#4) — Диагностика v8cs:missing-temporary-file-deletion проверяет требование пункта 4 стандарта std542.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/missing-temporary-file-deletion.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
