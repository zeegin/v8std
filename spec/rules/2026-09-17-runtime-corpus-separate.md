# Runtime и корпус версионируются независимо

Статус: **согласовано пользователем** 2026-09-17.

Изменение только runtime не требует новой исходной версии неизменённого корпуса.

## Проверка

Тип: Поведенческий тест.

На временной истории Git проверяется выбор прежней версии корпуса для изменения runtime.

- `tests.test_mcp_publication.InputIdentityTests.test_runtime_only_and_host_only_reuse_corpus_source_and_rerun_is_stable` — [код](../../tests/test_mcp_publication.py#L516).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_mcp_publication.InputIdentityTests.test_runtime_only_and_host_only_reuse_corpus_source_and_rerun_is_stable
```

Граница доказательства: Проверка локальная; состояние опубликованного сервиса она не подтверждает.
