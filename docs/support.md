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

Можно просто нажать на иконку `Редактировать` и прислать Pull Request.

Основной конфиг проекта: `zensical.toml`.

### Как развернуть локально?

Для локального запуска без Docker требуются `Python 3.12`, `Rust toolchain 1.86+` (`cargo`, `rustc`) и `git`.

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
    Рекомендуется `WSL 2`: установочные и служебные скрипты репозитория написаны на Bash.

    ```bash
    git clone https://github.com/zeegin/v8std.git
    cd v8std

    python3.12 -m venv .venv
    source .venv/bin/activate

    ./scripts/install_zensical.sh
    ./scripts/zensical_docs.sh serve
    ```

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

Скрипт `./scripts/install_zensical.sh` устанавливает зафиксированную версию Zensical и Python-зависимости проекта из `requirements.txt`.

Скрипт `./scripts/zensical_docs.sh` перед `serve` и `build` обновляет временные social cards. Пример production-сборки:

```bash
./scripts/zensical_docs.sh build --strict
```

Документация будет доступна по адресу `http://127.0.0.1:8000`.
