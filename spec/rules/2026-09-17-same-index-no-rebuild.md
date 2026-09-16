# Неизменившийся индекс не пересобирается

Статус: **согласовано пользователем** 2026-09-17.

Готовый MCP не пересоздаёт поколение поиска, если проверенное обновление указывает на тот же архив.

## Проверка

Тип: Поведенческий тест.

Тест считает вызовы проверки и построения при ответах 200 и 304.

- `tests.test_v8std_mcp_snapshots.IdentityRefreshTests.test_ready_200_and_304_build_only_at_bootstrap_and_verify_once_per_attempt` — [код](../../tests/test_v8std_mcp_snapshots.py#L960).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_snapshots.IdentityRefreshTests.test_ready_200_and_304_build_only_at_bootstrap_and_verify_once_per_attempt
```

Граница доказательства: Проверка архива не отменяется; правило относится к повторному построению поколения в памяти.
