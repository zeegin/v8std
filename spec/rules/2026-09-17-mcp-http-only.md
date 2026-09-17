# MCP использует только HTTP

Статус: **согласовано пользователем** 2026-09-17.

Публичный и локальный MCP используют только Streamable HTTP.

## Проверка

`tests.test_v8std_mcp_runtime.ConfigurationTests.test_http_is_only_supported_transport`
проверяет HTTP по умолчанию и отказ CLI от stdio.
`tests.test_v8std_mcp_distribution.DistributionTests.test_images_are_thin_pinned_and_unprivileged`
проверяет HTTP-команду Docker-образа.

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_runtime.ConfigurationTests.test_http_is_only_supported_transport tests.test_v8std_mcp_distribution.DistributionTests.test_images_are_thin_pinned_and_unprivileged
```

Граница доказательства: CLI и описание образа. Запуск собранного образа
проверяется отдельно HTTP-сценариями `dev.checks.check_mcp_container`.

Основание: [целевая поставка](../delivery-target.md).
