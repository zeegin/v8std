###### v8cs:doc-comment-use-minus

# Использование только дефис-минуса в документирующем комментарии (doc-comment-use-minus)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-use-minus.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-use-minus.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=44835166adcb06ebbe71b64e493bf233be31a40ee370d4c31803643096e5bbfb
-->

В описании в модели документирующего комментария необходимо использовать только символ дефис-минус вместо обычного дефиса или различных вариантов тире.

Эта проверка анализирует неправильные "минусы" в первом текстовом элементе в описании, идущем после декларации поля, чтобы найти возможное неправильное построение модели документирующего комментария.

## Неправильно

```bsl
// Параметры:
//  Параметры – Структура - первый это "среднее тире" а второй это "минус":
//  * Ключ1 - Число ⸺ некорректное длинное тире
Процедура NonComplaint(Параметры) Экспорт
	// пустая
КонецПроцедуры
```

## Правильно


```bsl
// Параметры:
//  Параметры - Структура - оба использованы минусы:
//  * Ключ1 - Число - использованы корректные дефис-минусы
Процедура Complaint(Параметры) Экспорт
	// пустая
КонецПроцедуры
```

## См.

- [Википедия: Дефис](https://ru.wikipedia.org/wiki/Дефис)
- [Википедия: Тире](https://ru.wikipedia.org/wiki/Тире)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/doc-comment-use-minus.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
