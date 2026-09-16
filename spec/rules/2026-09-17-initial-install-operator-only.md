# Первичная установка недоступна CI

Статус: **согласовано пользователем** 2026-09-17.

Команды первичной установки MCP доступны только root-оператору и запрещены ограниченному SSH-входу CI.

## Проверка

Тип: Поведенческий тест.

Проверяется отказ непривилегированному вызову CLI и реальному процессу restricted entry для initial-install команд.

- `tests.test_v8std_mcp_initial_install.InitialBoundaryTests.test_initial_verbs_are_root_only_and_restricted_entry_denies_them` — [код](../../tests/test_v8std_mcp_initial_install.py#L527).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_initial_install.InitialBoundaryTests.test_initial_verbs_are_root_only_and_restricted_entry_denies_them
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
