###### v8cs:security-software-call

# Безопасность программного обеспечения, вызываемого через открытые интерфейсы (security-software-call)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/security-software-call.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/security-software-call.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=4186a613a4969678ae4650d4ad7c3b1cca2e0a422fe66bbf75251868f87917f2
-->

При использовании интеграции со сторонними приложениями с помощью открытых интерфейсов
 (в частности, с помощью COM) требуется отключать исполнение произвольного кода средствами вызываемого приложения.

## Неправильно

ОбъектWord = Новый COMОбъект("Word.Application");
Документ = ОбъектWord.Documents.Open(ИмяФайла);

## Правильно

ОбъектWord = Новый COMОбъект("Word.Application");
ОбъектWord.WordBasic.DisableAutoMacros(1);
Документ = ОбъектWord.Documents.Open(ИмяФайла);

 ## См.
- [Безопасность программного обеспечения, вызываемого через открытые интерфейсы](https://its.1c.ru/db/v8std#content:775:hdoc)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- [#std775: Безопасность программного обеспечения, вызываемого через открытые интерфейсы](../../std/775.md)

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/security-software-call.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
