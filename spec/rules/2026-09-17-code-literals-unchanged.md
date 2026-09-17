# Перенос ссылок не изменяет примеры кода

Статус: **согласовано пользователем** 2026-09-17.

Замена адресов внутренних ссылок не меняет URL, записанные внутри примеров кода.

## Проверка

Тип: Поведенческий тест.

Тест сравнивает литералы в inline-коде, fenced-блоках, отступном коде и HTML code/pre.

- `tests.test_v8std_mcp_presentation.PresentationTests.test_link_nodes_and_nested_urls_preserve_literals_and_provenance` — [код](../../tests/test_v8std_mcp_presentation.py#L35).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_presentation.PresentationTests.test_link_nodes_and_nested_urls_preserve_literals_and_provenance
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
