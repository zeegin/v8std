# Одинаковые входы дают одинаковый архив

Статус: **согласовано пользователем** 2026-09-17.

Повторная упаковка одного корпуса с одинаковыми параметрами даёт побайтово одинаковый архив индекса.

## Проверка

Тип: Поведенческий тест.

Сравниваются байты повторных сборок и метаданные tar/gzip.

- `tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_00_producer_exists_and_rebuilds_identical_archive` — [код](../../tests/test_v8std_mcp_snapshot_format.py#L42).
- `tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_tar_gzip_metadata_is_exact_and_deterministic` — [код](../../tests/test_v8std_mcp_snapshot_format.py#L74).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_00_producer_exists_and_rebuilds_identical_archive tests.test_v8std_mcp_snapshot_format.SnapshotFormatTests.test_tar_gzip_metadata_is_exact_and_deterministic
```

Граница доказательства: Проверяется одинаковое окружение упаковки; воспроизводимость на произвольных версиях Python не заявляется.
