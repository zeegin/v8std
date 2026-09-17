# Индекс доступен при недоступном MCP

Статус: **согласовано пользователем** 2026-09-17.

HTTP-раздача архива индекса на VPS не зависит от доступности upstream MCP.

## Проверка

Тип: Отдельно включаемая Docker-проверка.

Реальный nginx отдаёт fixture архива при намеренно недоступном upstream.

- `tests.test_v8std_mcp_monitoring_retirement.MonitoringRetirementTests.test_index_download_stays_available_with_dead_upstream` — [код](../../tests/test_v8std_mcp_monitoring_retirement.py#L178).

Запуск из корня репозитория:

```bash
V8STD_MONITORING_RETIREMENT_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring_retirement.MonitoringRetirementTests.test_index_download_stays_available_with_dead_upstream
```

Граница доказательства: Это проверка nginx include, не реального ai.v8std.ru; по умолчанию пропущена.

Основание: [исходный документ](../delivery-target.md). Извлечена только сформулированная выше обязанность; остальные требования источника не переносятся.
