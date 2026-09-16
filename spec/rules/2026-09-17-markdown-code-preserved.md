# Нормализация Markdown сохраняет код

Статус: **согласовано пользователем** 2026-09-17.

Нормализация границ Markdown-блоков сохраняет содержимое отображаемого блока кода.

## Проверка

Тип: Поведенческий тест.

HTML с плотными границами блока сравнивается с эквивалентом с явными разделителями, включая отступы и спецсимволы.

- `tests.test_v8std_markdown.MarkdownRenderingTests.test_code_preservation_and_fence_recognition` — [код](../../tests/test_v8std_markdown.py#L69).

Запуск из корня репозитория:

```bash
.venv/bin/python -m unittest tests.test_v8std_markdown.MarkdownRenderingTests.test_code_preservation_and_fence_recognition
```

Граница доказательства: Проверены fixtures рендерера; копирование из браузера отдельно не проверялось.
