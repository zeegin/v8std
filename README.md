# Стандарты разработки 1С

https://v8std.ru

## Локальный MCP

```bash
docker compose -f docker-compose/docker-compose.yml up -d v8std-mcp
```

MCP-сервер будет доступен на `http://127.0.0.1:8765/mcp` и читает локальный индекс
`docs/ai/pages.jsonl` из смонтированного репозитория.

```bash
codex mcp add v8std-local --url http://127.0.0.1:8765/mcp
```
