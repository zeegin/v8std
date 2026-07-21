###### v8cs:self-assign

# Присвоение переменной самой себе (self-assign)

- Категория: `bsl`

<!-- diagnostic-source:start
source_url=https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/self-assign.md
source_path=bundles/com.e1c.v8codestyle.bsl/markdown/ru/self-assign.md
revision=c8fe7932babf718c0ace3cf836a99d6a3b98d098
SPDX-License-Identifier: EPL-2.0
sha256=3d2cb31050ae8c5f5ab1ac98f2b1e14416f1dd18b48a432577e1b552c3101991
-->

Присвоение переменной самой себе не имеет смысла и обычно указывает на ошибку.

## Неправильно

Например, неправильно:

П1 = "";
П1 = П1;

## Правильно

Например, правельно:

П1 = "";

 ## См.

- [Присвоение переменной самой себе](https://1c-syntax.github.io/bsl-language-server/diagnostics/SelfAssign/)

<!-- diagnostic-source:end -->

## Соответствие стандартам

- Нет прямой привязки к v8std в описании проверки

## Источник диагностики

- [Исходная статья](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/bundles/com.e1c.v8codestyle.bsl/markdown/ru/self-assign.md)
- Ревизия: `c8fe7932babf718c0ace3cf836a99d6a3b98d098`
- Лицензия: `EPL-2.0`
