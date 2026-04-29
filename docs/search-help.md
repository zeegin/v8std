---
title: Поиск по сайту
hide:
  - navigation
  - toc
---

# Поиск по сайту

## Форматы запросов

| Что нужно найти | Примеры запросов |
| --- | --- |
| Стандарт | `#std437`, `std 437`, `стандарт 437` |
| Диагностику BSLLS | `bslls:AssignAliasFieldsInQuery`, `AssignAliasFieldsInQuery` |
| Диагностику АПК | `acc:1245`, `апк 1245`, `ACC 1245` |
| Диагностику EDT / v8-code-style | `v8cs:common-module-name-client-server`, `edt common-module-name-client-server` |
| Тему | `транзакции`, `запросы`, `общие модули`, `права` |

## Индексы для LLM

| Файл | Назначение |
| --- | --- |
| [/llms.txt](/llms.txt) | Компактная карта сайта со стандартами, диагностиками и ссылками на машинный индекс |
| [/llms-full.txt](/llms-full.txt) | Очищенный полный Markdown-корпус страниц без front matter и служебной разметки темы |
| [/ai/pages.jsonl](/ai/pages.jsonl) | JSONL-индекс страниц, алиасов, связей и очищенного Markdown |
| [/std/437.md](/std/437.md) | Пример очищенной Markdown-версии страницы; для публичных страниц используется исходный путь `.md` |

Страницы с front matter `llms.ignore: true` исключаются из `/llms.txt` и `/llms-full.txt`.
Стандарты с таким флагом остаются в `/ai/pages.jsonl`, чтобы MCP мог искать и возвращать
их по идентификатору или теме. Это не влияет на обычные страницы сайта и поиск Zensical.
