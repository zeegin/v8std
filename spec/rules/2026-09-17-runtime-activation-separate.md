# Активация runtime задаётся отдельно

Статус: **согласовано пользователем** 2026-09-17.

При выключенном runtime_enabled отправка задания обновления не запускает и не планирует runtime.

## Проверка

Тип: Поведенческий тест.

Тест отключает флаг политики и проверяет ошибку runtime_not_activated без вызова schedule.

- `tests.test_v8std_mcp_release.TransactionTests.test_runtime_activation_is_separate_from_publication` — [код](../../tests/test_v8std_mcp_release.py#L1123).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_release.TransactionTests.test_runtime_activation_is_separate_from_publication
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
