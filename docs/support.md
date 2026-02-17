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
Выполните следующие операции на своем компьютере:

```cmd
git clone https://github.com/zeegin/v8std.git

cd v8std

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdocs serve --watch-theme
```

Если нужно локально генерировать social cards (Open Graph), установите системную библиотеку Cairo и включите плагин переменной окружения `MKDOCS_SOCIAL=true`.
Например:

- macOS: `brew install cairo`
- Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y libcairo2 libcairo2-dev`

Пример запуска:

- macOS (Apple Silicon + Homebrew):
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:/usr/lib MKDOCS_SOCIAL=true mkdocs build --strict`
- Linux:
  `MKDOCS_SOCIAL=true mkdocs build --strict`

Теперь по адресу `http://127.0.0.1:8000` можно открыть документацию на своем компьютере.
