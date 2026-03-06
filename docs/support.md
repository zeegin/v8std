---
hide:
  - navigation
  - toc
  - feedback
---

# Поддержка

### Нашли ошибку?

Рано или поздно мы поддержим все стандарты и все правила статического анализа кода.

[Пожаловаться или предложить идею](https://github.com/zeegin/v8std/issues/new){ .md-button }

### Хотите внести исправление?

Можно просто нажать на иконку `Редактировать` и прислать Pull Request.

Хотите изменить дизайн и посмотреть, как отладить сайт локально?

### Вариант 1. Локально через `venv`

Выполните следующие операции на своем компьютере:

```cmd
git clone https://github.com/zeegin/v8std.git

cd v8std

# Требуется Python 3.10+, а также установленный Rust toolchain (cargo/rustc) и git.
# Если ваш `python3` указывает на более старую версию, используйте `python3.12`.
python3.12 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

./scripts/install_zensical.sh

zensical serve
```

### Вариант 2. Локально через Docker

```cmd
git clone https://github.com/zeegin/v8std.git

cd v8std

docker compose -f docker-compose/docker-compose.yml up --build
```

Сборка статической версии + проверка через `nginx`:

```cmd
docker compose -f docker-compose/docker-compose.ngnix.yml up --build
```

Пример запуска:

- `MKDOCS_SOCIAL=true zensical build --strict`

Теперь по адресу `http://127.0.0.1:8000` можно открыть документацию на своем компьютере.
