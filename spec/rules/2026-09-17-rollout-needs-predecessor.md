# Обновление требует предшественника

Статус: **согласовано пользователем** 2026-09-17.

Обычная операция обновления MCP без принятого предшественника завершается отказом.

## Проверка

Тип: Поведенческий тест.

Тест удаляет сведения о предшественнике и проверяет отказ до постановки операции в очередь.

- `tests.test_v8std_mcp_release.TransactionTests.test_ordinary_submit_rejects_missing_predecessor_before_scheduling` — [код](../../tests/test_v8std_mcp_release.py#L1134).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_release.TransactionTests.test_ordinary_submit_rejects_missing_predecessor_before_scheduling
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
