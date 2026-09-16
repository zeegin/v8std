# Стандарты разработки 1С

Сайт: [v8std.ru](https://v8std.ru). MCP: [ai.v8std.ru](https://ai.v8std.ru/mcp).

## Разработка сайта

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-build.lock
VIRTUAL_ENV="$PWD/.venv" bash scripts/zensical_docs.sh serve --dev-addr=127.0.0.1:8000
```

Контент находится в `docs/`, шаблоны — в `overrides/`. Сборка сайта не требует MCP.

## Устройство репозитория

- `scripts/`, `data/`, конфигурации в корне — сборка сайта и индекса.
- `runtime/` — MCP-сервис; имя не конфликтует с Python SDK `mcp`.
- `delivery/` — образы, публикация артефактов и доставка на VPS.
- `dev/` — подготовка контента и инструменты разработчика.
- `tests/` — действующие проверки; `spec/` — цель и устройство поставки.

Python-команды из новых каталогов запускаются из корня через `python -m`,
например `.venv/bin/python -m dev.content.acc_diagnostics generate --check`.
Тестовые зависимости: `.venv/bin/python -m pip install --require-hashes -r dev/requirements-test.lock`.
Тесты: `.venv/bin/python -m unittest discover -s tests -t .`.

## Готовые образы

Публичный и локальный MCP используют Streamable HTTP. Отдельный транспорт для локального запуска не требуется.

Настройки локальной поставки находятся в `delivery/local/compose.yaml`.
Текущий файл описывает сайт и совместный запуск с MCP; самостоятельный MCP
с публичным индексом ещё требует проверки и завершения.

[Целевая поставка](spec/delivery-target.md) · [Файлы сборки сайта](spec/local-site-build-files.md) ·
[План разделения](spec/repository-layout-plan.md)
