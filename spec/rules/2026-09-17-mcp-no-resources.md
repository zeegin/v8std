# MCP не предоставляет Resources

Статус: **согласовано пользователем** 2026-09-17.

MCP отклоняет обращения к Resources через HTTP.

## Проверка

Тип: Поведенческий тест.

Реальные HTTP-обращения проверяют отсутствие capability и отказ методов Resources до и после загрузки индекса.

- `tests.test_v8std_mcp_tools_only.ToolsOnlyWireTests.test_http_cold_and_ready_resources_fail_while_tools_keep_their_contract` — [код](../../tests/test_v8std_mcp_tools_only.py#L171).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_tools_only.ToolsOnlyWireTests.test_http_cold_and_ready_resources_fail_while_tools_keep_their_contract
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
