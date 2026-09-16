# Локальный источник не заменяется публичным

Статус: **согласовано пользователем** 2026-09-17.

Ошибка выбранного локального источника индекса не вызывает переход к публичному источнику.

## Проверка

Тип: Поведенческий тест.

Тесты подают неверный архив и манифест со ссылкой на публичный архив и проверяют отказ без подмены источника.

- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_invalid_selected_archive_preserves_cache_without_public_fallback` — [код](../../tests/test_v8std_mcp_snapshots.py#L365).
- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_local_manifest_cannot_select_public_archive` — [код](../../tests/test_v8std_mcp_snapshots.py#L375).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_invalid_selected_archive_preserves_cache_without_public_fallback tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_local_manifest_cannot_select_public_archive
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
