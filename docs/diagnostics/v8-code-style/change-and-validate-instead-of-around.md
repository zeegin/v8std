###### v8cs:change-and-validate-instead-of-around

# Используется аннотация &ИзменениеИКонтроль вместо &Вместо (change-and-validate-instead-of-around)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/change-and-validate-instead-of-around.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/change-and-validate-instead-of-around.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=6720ee8cdb9f78cd1f89ee14ead466869dce599a8e1e52eb32fdc5673c6e8ccc
-->

Начиная с релиза платформы 8.3.16, можно использовать аннотацию &ИзменениеИКонтроль вместо аннотации &Вместо в тех случаях, когда внутри метода отсутствует вызов ПродолжитьВызов

## Неправильно

```bsl
&Вместо("МояФункция")
Функция Расш1_МояФункция()

	//Возврат 1;
	Возврат 2;

КонецФункции
```

## Правильно

```bsl
&ИзменениеИКонтроль("МояФункция")
Функция Расш1_МояФункция()

	#Удаление
	Возврат 1;
	#КонецУдаления
	#Вставка
	Возврат 2;
	#КонецВставки

КонецФункции
```

## См.

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/change-and-validate-instead-of-around.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
