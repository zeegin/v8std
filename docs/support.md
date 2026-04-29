---
title: Поддержка
hide:
  - navigation
  - toc
  - feedback
---

# Поддержка

### Нашли ошибку?

[Пожаловаться или предложить идею](https://github.com/zeegin/v8std/issues/new){ .md-button }

### Хотите внести исправление?

Можно просто нажать на иконку :material-file-edit-outline: `Редактировать` и прислать Pull Request.

Основной конфиг проекта: [`zensical.toml`](https://github.com/zeegin/v8std/blob/main/zensical.toml).

### Как развернуть локально?

Для локального запуска без Docker требуется `Python 3.12`. Zensical устанавливается из PyPI в зафиксированной версии.

=== ":fontawesome-brands-apple: mac"
    ```bash
    git clone https://github.com/zeegin/v8std.git
    cd v8std

    python3.12 -m venv .venv
    source .venv/bin/activate

    ./scripts/install_zensical.sh
    ./scripts/zensical_docs.sh serve
    ```

=== ":fontawesome-brands-windows: windows"

    ```bash
    git clone https://github.com/zeegin/v8std.git
    cd v8std

    python3.12 -m venv .venv
    source .venv/bin/activate

    ./scripts/install_zensical.sh
    ./scripts/zensical_docs.sh serve
    ```

    Рекомендуется `WSL 2`: установочные и служебные скрипты репозитория написаны на Bash.

=== ":fontawesome-brands-linux: linux"
    ```bash
    git clone https://github.com/zeegin/v8std.git
    cd v8std

    python3.12 -m venv .venv
    source .venv/bin/activate

    ./scripts/install_zensical.sh
    ./scripts/zensical_docs.sh serve
    ```

=== ":fontawesome-brands-docker: docker"
    ```bash
    git clone https://github.com/zeegin/v8std.git
    cd v8std

    docker compose -f docker-compose/docker-compose.yml up --build
    ```

    Статическая сборка и проверка через `nginx`:

    ```bash
    docker compose -f docker-compose/docker-compose.ngnix.yml up --build
    ```

Скрипт [`./scripts/install_zensical.sh`](https://github.com/zeegin/v8std/blob/main/scripts/install_zensical.sh) устанавливает зафиксированную версию Zensical из PyPI и Python-зависимости проекта из [`requirements.txt`](https://github.com/zeegin/v8std/blob/main/requirements.txt).

Скрипт [`./scripts/zensical_docs.sh`](https://github.com/zeegin/v8std/blob/main/scripts/zensical_docs.sh) перед `serve` и `build` обновляет временные social cards и AI-артефакты. Пример production-сборки:

```bash
./scripts/zensical_docs.sh build --strict
```

Документация будет доступна по адресу `http://127.0.0.1:8000`.

### Локальный MCP { #local-mcp }

Локальный MCP нужен, если вы не хотите отправлять фрагменты закрытого кода в
публичный сервис, работаете без доступа к интернету или проверяете изменения
сайта до публикации.

Самый простой запуск — через Docker:

```bash
git clone https://github.com/zeegin/v8std.git
cd v8std

docker compose -f docker-compose/docker-compose.yml up -d v8std-mcp
```

Локальный адрес MCP:

```text
http://127.0.0.1:8765/mcp
```

Подключение к Codex:

```bash
codex mcp add v8std-local --url http://127.0.0.1:8765/mcp
```

Подключение к Claude Code:

```bash
claude mcp add --transport http v8std-local http://127.0.0.1:8765/mcp
```

Для Cursor и Kiro используйте тот же адрес в `mcp.json`:

```json
{
  "mcpServers": {
    "v8std-local": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

Для Antigravity используйте `mcp_config.json`:

```json
{
  "mcpServers": {
    "v8std-local": {
      "serverUrl": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

Контейнер читает файлы `docs/ai/pages.jsonl` и
`docs/ai/search-vectors.jsonl`. Если их нет, он сгенерирует индекс при старте.

Без Docker MCP можно запустить так:

```bash
python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt -r requirements-mcp.txt
python scripts/generate_ai_artifacts.py
python scripts/generate_search_vectors.py
python scripts/v8std_mcp_server.py \
  --pages docs/ai/pages.jsonl \
  --vectors docs/ai/search-vectors.jsonl \
  --host 127.0.0.1 \
  --port 8765
```

Полезные команды:

```bash
docker logs v8std-mcp
docker compose -f docker-compose/docker-compose.yml restart v8std-mcp
```

### Поиск и LLM-индексы

Форматы запросов описаны на странице [Поиск по сайту](search-help.md).

При `serve` и `build` автоматически генерируются статические AI-артефакты:

- [`/llms.txt`](/llms.txt) — компактная карта сайта для LLM;
- [`/llms-full.txt`](/llms-full.txt) — очищенный полный Markdown-корпус;
- [`/ai/pages.jsonl`](/ai/pages.jsonl) — индекс страниц, алиасов, связей и очищенного Markdown;

Чтобы исключить страницу из `/llms.txt` и `/llms-full.txt`, добавьте в её front matter:

```yaml
llms:
  ignore: true
```

Это не влияет на обычную сборку сайта, навигацию и поиск Zensical. Стандарты с
таким флагом остаются в `/ai/pages.jsonl`, чтобы MCP мог находить их по теме,
номеру или коду диагностики. Служебные страницы с этим флагом в MCP-индекс не
попадают.
