# Локальная упаковка не меняет исходники

Статус: **согласовано пользователем** 2026-09-17.

Сборка поставляемого локального сайта не изменяет подготовленные docs, overrides и публичный site.

## Проверка

Тип: Отдельно включаемая интеграционная проверка.

Реальная сборка сравнивает хеши этих деревьев до и после.

- `tests.test_v8std_mcp_distribution.LocalBuildTests.test_actual_isolated_build_and_canonical_snapshot` — [код](../../tests/test_v8std_mcp_distribution.py#L555).

Запуск из корня репозитория:

```bash
V8STD_TEST_LOCAL_BUILD=1 .venv/bin/python -m unittest tests.test_v8std_mcp_distribution.LocalBuildTests.test_actual_isolated_build_and_canonical_snapshot
```

Граница доказательства: Тест запускается отдельно с V8STD_TEST_LOCAL_BUILD=1. Обычный scripts/zensical_docs.sh пока генерирует файлы в docs; данное правило на него не распространяется.
