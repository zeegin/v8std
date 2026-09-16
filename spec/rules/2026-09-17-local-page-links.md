# Ссылки статей указывают на выбранный сайт

Статус: **согласовано пользователем** 2026-09-17.

Внутренние ссылки статей в ответе MCP используют базовый адрес выбранного сайта.

## Проверка

Тип: Поведенческий тест.

Проверяются Markdown-ссылки, ссылки HTML, изображения и связанные страницы с локальным базовым адресом.

- `tests.test_v8std_mcp_presentation.PresentationTests.test_link_nodes_and_nested_urls_preserve_literals_and_provenance` — [код](../../tests/test_v8std_mcp_presentation.py#L35).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_presentation.PresentationTests.test_link_nodes_and_nested_urls_preserve_literals_and_provenance
```

Граница доказательства: Это не проверка полного отсутствия сетевых запросов браузера.
