# Запрос использует одно поколение индекса

Статус: **согласовано пользователем** 2026-09-17.

Один вызов инструмента использует одно поколение индекса до завершения вложенных операций.

## Проверка

Тип: Поведенческий тест.

Тест меняет активное поколение во время запроса и запрещает обращение к новому поколению из этого запроса.

- `tests.test_v8std_mcp_runtime.RuntimeTests.test_generation_capture_pins_nested_calls_and_returns_independent_copy` — [код](../../tests/test_v8std_mcp_runtime.py#L64).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_runtime.RuntimeTests.test_generation_capture_pins_nested_calls_and_returns_independent_copy
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
