# Runtime получает только приватный файл журнала

Статус: **согласовано пользователем** 2026-09-17.

При запуске runtime журнал подключается отдельным приватным файлом, без монтирования всего каталога журналов хоста.

## Проверка

Тип: Поведенческий тест.

Проверяется команда запуска контейнера из действующего адаптера хоста.

- `tests.test_v8std_mcp_logging.LoggingLaunchTests.test_actual_host_start_binds_only_the_private_file_and_enables_existing_flag` — [код](../../tests/test_v8std_mcp_logging.py#L30).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_logging.LoggingLaunchTests.test_actual_host_start_binds_only_the_private_file_and_enables_existing_flag
```

Граница доказательства: Проверка команды не доказывает отсутствие HTTP alias на реальном VPS.
