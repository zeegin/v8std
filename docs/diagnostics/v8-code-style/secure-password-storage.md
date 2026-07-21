###### v8cs:secure-password-storage

# Проверка использования безопасного хранилища для паролей (secure-password-storage)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/secure-password-storage.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/secure-password-storage.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=603328268eda394e204a35ee83f895bf8f0c039a7d830aec5459a9604991af9f
-->

Не следует хранить пароли в реквизитах формы, их следует извлекать
только на стороне сервера и непосредственно перед их использованием. В
противном случае, при открытии формы с маскированным вводом (или
просмотром) пароля, пароль передается с  сервера на клиент в открытом
виде, что делает возможным его перехват.

## Неправильно


## Правильно
Процедура ПриСозданииНаСервере()

 УстановитьПривилегированныйРежим(Истина);
 Пароли = ОбщегоНазначения.ПрочитатьДанныеИзБезопасногоХранилища(Объект.Ссылка,
 "Пароль, ПарольSMTP");
 УстановитьПривилегированныйРежим(Ложь);

 Пароль = ?(ЗначениеЗаполнено(Пароли.Пароль),
 ЭтотОбъект.УникальныйИдентификатор, "");
 ПарольSMTP = ?(ЗначениеЗаполнено(Пароли.ПарольSMTP),
 ЭтотОбъект.УникальныйИдентификатор, "");

КонецПроцедуры


## См.

- [Безопасное хранение паролей](https://its.1c.ru/db/v8std#content:740:hdoc)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

- [#std740, п. 3.3: Безопасное хранение паролей](../../std/740.md#33) — Диагностика v8cs:secure-password-storage проверяет требование пункта 3.3 стандарта std740.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/secure-password-storage.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
