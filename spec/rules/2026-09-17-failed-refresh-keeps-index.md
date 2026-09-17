# Неудачное обновление сохраняет рабочий индекс

Статус: **согласовано пользователем** 2026-09-17.

Ошибка фонового обновления не заменяет рабочее поколение индекса повреждёнными данными.

## Проверка

Тип: Поведенческий тест.

Реальный локальный источник выдаёт медленный или повреждённый архив; MCP продолжает возвращать прежнюю страницу.

- `tests.test_v8std_mcp_runtime.RuntimeTests.test_tools_serve_warm_page_through_slow_and_corrupt_refresh` — [код](../../tests/test_v8std_mcp_runtime.py#L163).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_runtime.RuntimeTests.test_tools_serve_warm_page_through_slow_and_corrupt_refresh
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
