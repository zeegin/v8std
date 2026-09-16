# Каталог инструментов HTTP MCP

Статус: **согласовано пользователем** 2026-09-17.

MCP через HTTP предоставляет каталог из пяти инструментов: v8std_search, v8std_get_page, v8std_get_related, v8std_explain_snippet и v8std_explain_diagnostics.

## Проверка

Тип: Поведенческий тест.

Тест вызывает assert_tool_catalog на настоящем протокольном ответе.

- `tests.test_v8std_mcp_tools_only.ToolsOnlyWireTests.test_http_cold_and_ready_resources_fail_while_tools_keep_their_contract` — [код](../../tests/test_v8std_mcp_tools_only.py#L171).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_tools_only.ToolsOnlyWireTests.test_http_cold_and_ready_resources_fail_while_tools_keep_their_contract
```

Граница доказательства: Это проверка каталога и фиксированных сценариев, а не доказательство эквивалентности всех возможных ответов.
