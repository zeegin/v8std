# Манифест появляется после архива

Статус: **согласовано пользователем** 2026-09-17.

Новый манифест индекса становится доступен только после размещения проверенного архива.

## Проверка

Тип: Поведенческий тест.

Проверяется порядок записи и сохранение прежнего манифеста при сбое размещения.

- `tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_manifest_is_replaced_only_after_verified_archive_exists` — [код](../../tests/test_v8std_mcp_snapshot_format.py#L458).
- `tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_link_or_rename_failure_retains_previous_manifest_and_removes_temporary_files` — [код](../../tests/test_v8std_mcp_snapshot_format.py#L476).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_manifest_is_replaced_only_after_verified_archive_exists tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_link_or_rename_failure_retains_previous_manifest_and_removes_temporary_files
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
