# Рендерер не переписывает исходную статью

Статус: **согласовано пользователем** 2026-09-17.

Рендеринг Markdown не изменяет исходный файл статьи.

## Проверка

Тип: Поведенческий тест.

После рендеринга реальной статьи её исходные байты сравниваются с прочитанными до операции.

- `tests.test_v8std_markdown.MarkdownRenderingTests.test_real_issue_has_valid_structure_without_source_change` — [код](../../tests/test_v8std_markdown.py#L361).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_markdown.MarkdownRenderingTests.test_real_issue_has_valid_structure_without_source_change
```

Граница доказательства: Правило относится к рендереру, а не ко всем генераторам сборки.
