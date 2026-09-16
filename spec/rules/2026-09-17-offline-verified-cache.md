# Офлайн-запуск использует проверенный кэш

Статус: **согласовано пользователем** 2026-09-17.

MCP может стать готовым без доступа к источнику, если сохранилось проверенное поколение его индекса.

## Проверка

Тип: Поведенческий тест.

Тест запускает runtime на ранее сохранённом индексе после отключения локального источника.

- `tests.test_v8std_mcp_runtime.RuntimeTests.test_verified_warm_generation_becomes_ready_with_source_offline` — [код](../../tests/test_v8std_mcp_runtime.py#L207).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_runtime.RuntimeTests.test_verified_warm_generation_becomes_ready_with_source_offline
```

Граница доказательства: Первый запуск без индекса офлайн не обещается.
