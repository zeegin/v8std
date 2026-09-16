# Публичный мониторинг закрыт

Статус: **согласовано пользователем** 2026-09-17.

Маршруты /monitoring и /monitoring/ возвращают 410 независимо от наличия прежних файлов.

## Проверка

Тип: Отдельно включаемая Docker-проверка.

Реальный nginx с действующими include-файлами получает запросы к старым страницам и файлам.

- `tests.test_v8std_mcp_monitoring_retirement.MonitoringRetirementTests.test_retired_paths_never_serve_legacy_files_or_redirect` — [код](../../tests/test_v8std_mcp_monitoring_retirement.py#L139).

Запуск из корня репозитория:

```bash
V8STD_MONITORING_RETIREMENT_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring_retirement.MonitoringRetirementTests.test_retired_paths_never_serve_legacy_files_or_redirect
```

Граница доказательства: По умолчанию пропущен. Требуются V8STD_MONITORING_RETIREMENT_DOCKER=1 и локальный pinned nginx image.
