# Стандарты разработки 1С

https://v8std.ru

## Локальный MCP

```bash
docker compose -f docker-compose/docker-compose.yml up -d v8std-mcp
```

MCP-сервер будет доступен на `http://127.0.0.1:8765/mcp` и читает локальный индекс
`docs/ai/pages.jsonl` из смонтированного репозитория.

Только MCP, без сервера документации — из готового образа Docker Hub (индекс
запечён на этапе сборки, монтирование репозитория не нужно):

```bash
docker compose -f docker-compose-mcp-only/docker-compose.yml up -d v8std-mcp
```

Запуск без клонирования репозитория:

```bash
docker run -d --name v8std-mcp -p 127.0.0.1:8765:8765 malikovpro/v8std-mcp:latest
```

```bash
codex mcp add v8std-local --url http://127.0.0.1:8765/mcp
```
