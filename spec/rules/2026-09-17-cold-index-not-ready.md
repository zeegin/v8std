# Отсутствие индекса означает неготовность

Статус: **согласовано пользователем** 2026-09-17.

MCP без проверенного рабочего индекса сообщает INDEX_NOT_READY.

## Проверка

Тип: Поведенческий тест.

При недоступном источнике current() возвращает ошибку неготовности, а не пустой успешный индекс.

- `tests.test_v8std_mcp_snapshots.SnapshotCoordinatorTests.test_cold_failure_is_explicit_and_status_does_not_expose_raw_errors` — [код](../../tests/test_v8std_mcp_snapshots.py#L836).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots.SnapshotCoordinatorTests.test_cold_failure_is_explicit_and_status_does_not_expose_raw_errors
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
