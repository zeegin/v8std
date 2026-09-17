# Неудачное переключение возвращает предшественника

Статус: **согласовано пользователем** 2026-09-17.

При провале публичной проверки нового runtime операция обновления восстанавливает прежний runtime.

## Проверка

Тип: Поведенческий тест.

Проверяется сбой после переключения и восстановление прежнего процесса через локальный адаптер.

- `tests.test_v8std_mcp_release.TransactionTests.test_public_failure_restores_observed_predecessor_and_retains_snapshot` — [код](../../tests/test_v8std_mcp_release.py#L1149).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_mcp_release.TransactionTests.test_public_failure_restores_observed_predecessor_and_retains_snapshot
```

Граница доказательства: Тест не подтверждает доступность реального VPS. Неудача самого восстановления — отдельное правило, здесь не объединяется.
