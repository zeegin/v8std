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
| [/llms.txt](/llms.txt) | Компактная карта сайта со стандартами, диагностиками и ссылками на машинные индексы |
| [/llms-full.txt](/llms-full.txt) | Полный Markdown-корпус страниц без front matter |
| [/ai/pages.jsonl](/ai/pages.jsonl) | JSONL-индекс страниц, алиасов, связей и исходного Markdown |
| [/ai/graph.json](/ai/graph.json) | Граф связей стандартов, диагностик, EDT-проверок и внешних источников |
| [/ai/search-aliases.json](/ai/search-aliases.json) | Нормализованные поисковые алиасы для стандартов и диагностик |
