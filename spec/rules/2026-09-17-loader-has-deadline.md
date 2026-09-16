# Загрузка индекса ограничена временем

Статус: **согласовано пользователем** 2026-09-17.

Истечение общего срока загрузки индекса завершает загрузочный процесс, включая зависшую подготовку данных.

## Проверка

Тип: Поведенческий тест.

Тестируются зависание подготовки/DNS и процесс, игнорирующий мягкое завершение.

- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_prepare_and_dns_are_terminated_at_whole_attempt_deadline` — [код](../../tests/test_v8std_mcp_snapshots.py#L539).
- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_uncooperative_worker_is_killed_and_reaped_after_terminate_grace` — [код](../../tests/test_v8std_mcp_snapshots.py#L553).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_prepare_and_dns_are_terminated_at_whole_attempt_deadline tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_uncooperative_worker_is_killed_and_reaped_after_terminate_grace
```

Граница доказательства: Конкретные значения таймаутов — параметры реализации; это правило не утверждает каждую текущую константу.
