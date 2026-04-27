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

### Поиск и LLM-индексы

Форматы запросов описаны на странице [Поиск по сайту](search-help.md).

При `serve` и `build` автоматически генерируются статические AI-артефакты:

- [`/llms.txt`](/llms.txt) — компактная карта сайта для LLM;
- [`/llms-full.txt`](/llms-full.txt) — очищенный полный Markdown-корпус;
- [`/ai/pages.jsonl`](/ai/pages.jsonl) — индекс страниц, алиасов, связей и очищенного Markdown;

Чтобы исключить страницу из публичных LLM-артефактов (`/llms.txt`, `/llms-full.txt`, `/ai/pages.jsonl`), добавьте в её front matter:

```yaml
llms:
  ignore: true
```

Это не влияет на обычную сборку сайта, навигацию и поиск Zensical.
