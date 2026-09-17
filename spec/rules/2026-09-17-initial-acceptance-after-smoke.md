# Первичная установка принимается после проверки

Статус: **согласовано пользователем** 2026-09-17.

Первичная установка не становится принятой при провале публичной проверки MCP.

## Проверка

Тип: Поведенческий тест.

После внедрённого провала public smoke проверяются непринятое состояние и закрытый маршрут.

- `tests.test_v8std_mcp_initial_install.InitialInstallTests.test_public_smoke_failure_closes_route_without_accepting` — [код](../../tests/test_v8std_mcp_initial_install.py#L367).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_initial_install.InitialInstallTests.test_public_smoke_failure_closes_route_without_accepting
```

Граница доказательства: Используется тестовый адаптер хоста; успешная установка на новом VPS этим не доказана.
