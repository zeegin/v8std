# Тег исходной версии не перезаписывается

Статус: **согласовано пользователем** 2026-09-17.

Публикация образа не перезаписывает неизменяемый тег, если он уже указывает на другой digest.

## Проверка

Тип: Поведенческий тест.

При конфликтующем содержимом реестра тест ожидает отказ без команды записи.

- `tests.test_mcp_publication.TransportBoundaryTests.test_immutable_tag_never_overwrites_conflict_and_rechecks_main_before_write` — [код](../../tests/test_mcp_publication.py#L1098).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_mcp_publication.TransportBoundaryTests.test_immutable_tag_never_overwrites_conflict_and_rechecks_main_before_write
```

Граница доказательства: Ответ реестра подменён в тесте; реальная публикация в GHCR в этом прогоне не выполнялась.
