# Дисковое поколение переключается атомарно

Статус: **согласовано пользователем** 2026-09-17.

После сбоя записи кэша доступно целое старое либо целое новое поколение индекса.

## Проверка

Тип: Поведенческий тест.

Тесты прерывают запись на стадиях commit и внедряют ошибки fsync.

- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_crash_at_commit_stages_recovers_complete_old_or_new_generation` — [код](../../tests/test_v8std_mcp_snapshots.py#L574).
- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_each_commit_fsync_failure_keeps_old_disk_pointer` — [код](../../tests/test_v8std_mcp_snapshots.py#L562).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_crash_at_commit_stages_recovers_complete_old_or_new_generation tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_each_commit_fsync_failure_keeps_old_disk_pointer
```

Граница доказательства: Проверены перечисленные стадии записи; это не моделирование всех отказов диска и файловой системы.
