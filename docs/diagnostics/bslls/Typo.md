###### bslls:Typo

# Опечатка (Typo)

- Тип: Дефект кода
- Важность: Информационный
- Включена по умолчанию: Да
- Теги: `badpractice`

<!-- diagnostic-source:start
source_url=https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/Typo.md
source_path=docs/diagnostics/Typo.md
revision=f4616cda8a216789ee40529ed857e614b9e2ea25
SPDX-License-Identifier: LGPL-3.0-or-later
sha256=f5a7dfe7f03a292dec6fa02aba5a27f0b333a5b9b211c869f098b9c70a7e3a23
-->

<!-- Блоки выше заполняются автоматически, не трогать -->
## Описание диагностики
<!-- Описание диагностики заполняется вручную. Необходимо понятным языком описать смысл и схему работу -->
Проверка орфографических ошибок осуществляется с помощью [LanguageTool](https://languagetool.org/ru/). Проверяемые строки разбиваются по camelCase
и проверяются на соответствие во встроенном словаре.

## Кэш
Диагностика использует персистентный кэш на диске (EhCache) для хранения информации об уже проверенных словах. Путь к каталогу кэша настраивается с помощью свойств `app.cache.basePath` и `app.cache.fullPath` в конфигурации приложения.

По умолчанию в приложении установлено:

```properties
app.cache.basePath=${user.home}
app.cache.fullPath=
```

Это означает, что:
- Кэш будет создаваться в каталоге пользователя (`${user.home}/.bsl-language-server/cache/<hash>/`)
- `<hash>` — MD5-хэш абсолютного пути к текущей рабочей директории, что обеспечивает изоляцию кэша для разных workspace
- Кэш не создается в рабочей директории проекта, не захламляя git-репозитории

Для переопределения пути к кэшу можно использовать:
- `app.cache.fullPath` — полный путь к каталогу кэша (если задан, используется напрямую)
- `app.cache.basePath` — базовый путь для автоматического вычисления (по умолчанию `${user.home}`)

Пример переопределения:

```properties
# Задать явный путь к кэшу
app.cache.fullPath=/custom/cache/location

# Или изменить только базовый путь
app.cache.basePath=/opt/bsl-ls
# Результат: /opt/bsl-ls/.bsl-language-server/cache/<hash>/
```

Рекомендации для CI:

**Важно**: С новой версией кэш по умолчанию хранится в каталоге пользователя с хэшем workspace. Для CI рекомендуется явно задать `app.cache.fullPath` для упрощения кэширования между сборками.

- GitHub Actions
  - Задайте явный путь к кэшу в переменных окружения или конфигурации
  - Используйте `actions/cache` для сохранения каталога между прогоном сборок и тестов

  ```yaml
  - name: Cache BSL LS Typo
    uses: actions/cache@v3
    with:
      path: .bsl-ls-cache
      key: ${{ runner.os }}-bsl-typo-${{ hashFiles('**/*.bsl') }}
      restore-keys: |
        ${{ runner.os }}-bsl-typo-
  ```

- GitLab CI
  - В `.gitlab-ci.yml` используйте секцию `cache`:

    ```yaml
    variables:
      APP_CACHE_FULLPATH: ".bsl-ls-cache"

    cache:
      key: "bsl-ls-typo-cache"
      paths:
        - .bsl-ls-cache/
      policy: pull-push
    ```

  - При необходимости задайте уникальный `key` для разных веток/раннеров.

- Jenkins
  - Задайте переменную окружения `APP_CACHE_FULLPATH` для явного пути к кэшу
  - В pipeline можно сохранить каталог кэша между сборками несколькими способами:
    - Использовать `stash`/`unstash` для передачи данных между этапами в одной сборке.
    - Использовать плагин `Workspace Cleanup` и настроить сохранение workspace на агенте (если агенты постоянные) или архивировать артефакт с помощью `archiveArtifacts` и скачивать при следующих сборках.
    - Для Jenkins при использовании динамических агентов (например, Kubernetes) рекомендуется сохранять кэш в сетевом хранилище или в объектном хранилище (S3) и восстанавливать его в начале job.

Общие рекомендации:
- Для CI-окружений рекомендуется явно задать `app.cache.fullPath` (например, `.bsl-ls-cache` в workspace проекта) для упрощения кэширования
- Убедитесь, что путь к кэшу доступен процессу сборки и имеет достаточные права.

## Источники
<!-- Необходимо указывать ссылки на все источники, из которых почерпнута информация для создания диагностики -->

* Полезная информация: [Русский язык для всех](http://gramota.ru/)
* [Страница LanguageTool](https://languagetool.org/ru/)

<!-- diagnostic-source:end -->

<!-- diagnostic-standards:start -->
## Соответствие стандартам

Нет подтверждённых связей со стандартами.
<!-- diagnostic-standards:end -->

## Источник диагностики

- [Исходная статья](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/docs/diagnostics/Typo.md)
- Ревизия: `f4616cda8a216789ee40529ed857e614b9e2ea25`
- Лицензия: `LGPL-3.0-or-later`
