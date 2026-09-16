# MCP не открывает поток по GET

Статус: **согласовано пользователем** 2026-09-17.

GET /mcp с Accept: text/event-stream возвращает 405 вместо открытия длительного потока.

## Проверка

Тип: Поведенческий тест.

ASGI-запрос получает 405; нижележащий обработчик не вызывается.

- `tests.test_v8std_mcp_server.SelfDocumentingMcpAppTests.test_mcp_get_with_event_stream_accept_is_rejected` — [код](../../tests/test_v8std_mcp_server.py#L279).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_server.SelfDocumentingMcpAppTests.test_mcp_get_with_event_stream_accept_is_rejected
```

Граница доказательства: Проверяется приложение. Лимиты nginx и число допустимых соединений сюда не входят.
