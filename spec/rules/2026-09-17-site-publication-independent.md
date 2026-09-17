# Сайт публикуется без активации MCP

Статус: **согласовано пользователем** 2026-09-17.

При выключенных трёх флагах поставки MCP workflow пропускает этапы prepare-pages, finish и accepted-publication, сохраняя публикацию Pages.

## Проверка

Тип: Статическая проверка workflow.

Тест проверяет условия этих шагов и отсутствие MCP-условия у deploy-pages.

- `tests.test_mcp_publication.WorkflowTests.test_site_only_publication_does_not_require_an_mcp_manifest` — [код](../../tests/test_mcp_publication.py#L1200).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_mcp_publication.WorkflowTests.test_site_only_publication_does_not_require_an_mcp_manifest
```

Граница доказательства: Проверка статическая. Успешный запуск этого нового workflow на GitHub ещё не получен.

Основание: [исходный документ](../delivery-target.md). Извлечена только сформулированная выше обязанность; остальные требования источника не переносятся.
