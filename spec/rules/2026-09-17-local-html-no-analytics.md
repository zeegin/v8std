# Локальный HTML не подключает публичную аналитику

Статус: **согласовано пользователем** 2026-09-17.

HTML локальной поставки не содержит подключения публичной аналитики u.ingvar.pro.

## Проверка

Тип: Отдельно включаемая интеграционная проверка.

Проверяется HTML реально собранной страницы std/437.

- `tests.test_v8std_mcp_distribution.LocalBuildTests.test_actual_isolated_build_and_canonical_snapshot` — [код](../../tests/test_v8std_mcp_distribution.py#L555).

Запуск из корня репозитория:

```bash
V8STD_TEST_LOCAL_BUILD=1 .venv/bin/python -m unittest tests.test_v8std_mcp_distribution.LocalBuildTests.test_actual_isolated_build_and_canonical_snapshot
```

Граница доказательства: Проверяется одна собранная страница std/437 с V8STD_TEST_LOCAL_BUILD=1. Общее правило «браузер не обращается в интернет» не извлечено: такого доказательства нет.
