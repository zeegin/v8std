# Разные источники имеют отдельный кэш

Статус: **согласовано пользователем** 2026-09-17.

MCP не использует кэш одного источника индекса как кэш другого источника.

## Проверка

Тип: Поведенческий тест.

Проверяется смена источника и работа двух источников на общем дисковом томе.

- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_normalized_source_reuses_cache_and_other_sources_never_do` — [код](../../tests/test_v8std_mcp_snapshots.py#L340).
- `tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_different_sources_on_shared_volume_download_and_cache_independently` — [код](../../tests/test_v8std_mcp_snapshots.py#L347).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_normalized_source_reuses_cache_and_other_sources_never_do tests.test_v8std_mcp_snapshots.SnapshotStoreTests.test_different_sources_on_shared_volume_download_and_cache_independently
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
