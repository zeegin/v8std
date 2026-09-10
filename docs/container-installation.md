---
title: Локальная установка в контейнерах
llms:
  ignore: true
---

# Локальная установка в контейнерах

Поставка состоит из двух независимых образов: `ghcr.io/zeegin/v8std-mcp`
с MCP runtime и `ghcr.io/zeegin/v8std-site` с готовым локальным сайтом.
Поддерживаемые архитектуры — `linux/arm64` и `linux/amd64`.

**Первый выпуск ещё не опубликован.** Команды ниже требуют действительных
image references из проверенного выпуска. Наличие Dockerfile или шаблона
Catalog не означает публикацию в GHCR или принятие Docker team. Не используйте
`release-pending` как установленную версию. Для локальной проверки разработчик
может явно передать теги своих тестовых образов вместо release references.

## Сайт и MCP HTTP

Получите `compose.yaml` из той же версии исходников и укажите проверенные
references вида `ghcr.io/zeegin/v8std-site@sha256:…` и
`ghcr.io/zeegin/v8std-mcp@sha256:…`. Значение digest относится к опубликованному
multi-platform index; локальный Docker image ID не заменяет этот digest.

```bash
export V8STD_SITE_IMAGE='ghcr.io/zeegin/v8std-site@sha256:RELEASE_INDEX_DIGEST'
export V8STD_MCP_IMAGE='ghcr.io/zeegin/v8std-mcp@sha256:RELEASE_INDEX_DIGEST'
docker compose -p v8std-local -f compose.yaml up -d site
docker compose -p v8std-local -f compose.yaml --profile mcp up -d
curl --fail http://v8std.localhost:18765/ai/mcp/v1/manifest.json
curl --fail http://127.0.0.1:18766/healthz
```

Сайт открывается по адресу `http://v8std.localhost:18765/`, MCP — по адресу
`http://127.0.0.1:18766/mcp`. До подготовки проверенного поколения `/healthz`
отвечает `503`; `/livez` показывает только жизнь процесса. В `tools/list`
доступны пять инструментов, в `resources/list` — три Resources.

`v8std.localhost` разрешается браузером в loopback, а внутри сети Compose
служит DNS alias сайта. Сайт подключён к внутренней сети `corpus` и обычной
сети `publish`, чтобы Docker Desktop мог опубликовать loopback ports. MCP
подключён только к `corpus`; его HTTP доступен через proxy статического сервера
на отдельном loopback port. Docker socket внутри MCP отсутствует.

Можно изменить `V8STD_SITE_PORT` и `V8STD_MCP_PORT`, выбрав свободные порты.
Site port одинаков снаружи и внутри контейнера. Для образа сайта, подготовленного
под `/kb/`, задайте `V8STD_SITE_PREFIX=/kb/`. Один полный site URL одновременно
определяет источник manifest/archive и ссылки в ответах MCP. У него нет
скрытой публичной альтернативы. Префикс образа и настройка Compose должны совпадать.

Явный `V8STD_MCP_SITE_URL` переопределяет вычисленный локальный URL в Compose:
например, `V8STD_MCP_SITE_URL=http://v8std.localhost:18765/kb/` для доступного
по этому адресу snapshot. Настройка одновременно меняет источник и ссылки,
но не перестраивает сайт и не добавляет MCP сетевой доступ: выбранный URL должен
быть доступен из существующей сети `corpus` и с компьютера пользователя.
Проверьте итоговое значение командой `docker compose --profile mcp config`.

Перед использованием на другой машине проверьте URL из браузера и контейнера:

```bash
curl --fail http://v8std.localhost:18765/ai/mcp/v1/manifest.json
docker run --rm --network v8std-local_corpus --read-only --cap-drop ALL \
  --security-opt no-new-privileges --entrypoint python "$V8STD_MCP_IMAGE" \
  -c "import urllib.request; print(urllib.request.urlopen('http://v8std.localhost:18765/ai/mcp/v1/manifest.json', timeout=5).status)"
```

На Linux не полагайтесь на автоматическое существование `host.docker.internal`.
Если используете собственный доступный контейнерам host/LAN-сайт, явно проверьте
host-gateway и HTTP; успешное разрешение имени само по себе недостаточно:

```bash
docker run --rm --add-host host.docker.internal:host-gateway \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint python "$V8STD_MCP_IMAGE" \
  -c "import socket,urllib.request; print(socket.gethostbyname('host.docker.internal')); print(urllib.request.urlopen('http://host.docker.internal:18765/ai/mcp/v1/manifest.json',timeout=5).status)"
```

Для сайта, опубликованного **только** на `127.0.0.1`, последний HTTP probe
на Linux может не пройти: gateway IP не является host loopback. Не меняйте
bind/DNS автоматически. Основная схема выше использует общий `.localhost`
адрес и внутренний DNS alias; native Linux acceptance проверяется отдельно
от amd64-эмуляции Docker Desktop.

## Только MCP через stdio

Runtime image не содержит corpus или генератор документации. Для первого
запуска нужен доступный сайт с v1 snapshot. Public source по умолчанию —
`https://v8std.ru/`; первый выпуск может работать с ним только после публикации
`ai/mcp/v1/manifest.json` и указанного archive.

```bash
docker volume create v8std-mcp-cache
docker run --rm -i --init --read-only --cap-drop ALL \
  --security-opt no-new-privileges --memory 1536m --cpus 2 --pids-limit 128 \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m,uid=10001,gid=10001 \
  -v v8std-mcp-cache:/var/lib/v8std-mcp "$V8STD_MCP_IMAGE"
```

Для локального сайта добавьте `--network v8std-local_corpus` и
`-e V8STD_MCP_SITE_URL=http://v8std.localhost:18765/` **перед** именем образа.
Default CMD выбирает stdio; `stdout` предназначен только для MCP JSON-RPC.
EOF завершает runtime. Для HTTP передайте после имени образа
`--transport streamable-http --host 0.0.0.0 --port 8000` и опубликуйте порт
только на loopback либо используйте Compose.

UID/GID runtime — `10001:10001`, cache — `/var/lib/v8std-mcp`.
Новый named volume наследует владельца каталога из образа. Для существующего
bind mount оператор должен заранее обеспечить права этого UID/GID;
контейнер не выполняет `chown` при старте. Не удаляйте cache для обычного restart.
`docker compose down -v` удаляет проверенный cache и лишает следующий запуск
возможности работать offline.

С сохранённым cache и тем же SITE_URL warm restart работает без сети.
Cold-offline запуск без cache остаётся неготовым; это не самодостаточный образ
со встроенным корпусом. Другой SITE_URL создаёт другую cache namespace.
Общий volume экономит загрузки, но процессы разных агентов сохраняют отдельные
поколения индекса в памяти. Указанные memory/CPU limits — параметры проверок,
не обещание пропускной способности.

`--site-url`, `--cache-dir` и `--max-snippet-chars` имеют приоритет над
`V8STD_MCP_SITE_URL`, `V8STD_MCP_CACHE_DIR` и `V8STD_MCP_MAX_SNIPPET_CHARS`.
Snippet default — 4000, максимум — 32000 символов. `--refresh-seconds 0`
отключает периодический refresh, но не первую попытку обновления после старта.
Общая попытка загрузки, проверки и построения поколения ограничена 360 секундами;
один сетевой read — 20 секундами и остатком общего бюджета. Это не timeout RPC:
до готовности tools возвращают INDEX_NOT_READY, не ожидая завершения построения.
Close/SIGTERM отменяет worker без ожидания всех 360 секунд.
Старые `--index-url`/`--vectors-url` не являются настройками нового образа;
не смешивайте их с `--site-url`. Прямой Python CLI для разработки по-прежнему
по умолчанию выбирает HTTP `127.0.0.1:8765`.

## Docker MCP Catalog и Gateway

`deploy/docker-catalog/server.yaml` — шаблон в формате исходников Docker
mcp-registry. Перед выпуском его image reference и `source.commit` должны
быть заменены подтверждёнными digest/SHA. Это образ проекта v8std, не Docker
Official Image. CC0 проекта не заменяет лицензии зависимостей и корпуса:
три опубликованных текста доступны по `/LICENSES/`, атрибуция — на странице
[сторонних материалов](THIRD_PARTY_DIAGNOSTIC_ARTICLES.md).

Catalog объявляет site URL, snippet limit, shared cache volume и `longLived`.
Gateway может запускать отдельный контейнер для каждой сессии. Host CLI
Gateway v0.43.3 не имеет флага подключения к дополнительной сети. Для локального
источника требуется отдельно проверенная маршрутизация containerized Gateway;
его доступ к Docker API требует полномочий оператора. Не монтируйте socket в MCP.

Профиль изоляции задаёт launcher, а не образ. Production controller и наши
direct Docker/Compose используют строгий профиль: UID/GID `10001:10001`,
nonprivileged, без Docker socket, `init`, `no-new-privileges`, read-only rootfs,
`cap-drop ALL` и ограниченный tmpfs. Native Gateway v0.43.3 использует другой
согласованный профиль: тот же UID/GID, nonprivileged, без Docker socket,
`init` и `no-new-privileges`. Read-only rootfs, cap-drop и tmpfs через его схему
Catalog не задаются и для этого канала не обещаются. Их отсутствие само по себе
не блокирует Catalog; если эти ограничения нужны, используйте direct Docker/Compose.

После обновления Gateway проверяйте фактические controls и mounts **каждого**
созданного MCP-сервера. Warm harness допускает только ожидаемый named cache
volume; неожиданный bind mount отклоняется независимо от имени socket alias.
До запуска harness отклоняет непустой `DOCKER_MCP_IN_DIND`, который может
заставить Gateway добавить `--privileged`; настройки пользователя не меняются.
Соответствие native-профилю не заменяет проверку cold source routing,
происхождения образа, внешнюю приёмку Catalog, registry publication или native CI.

## Проверка разработчиком

Старый `docker-compose/docker-compose.yml` — dev-only: он монтирует исходники
и может генерировать индекс при старте. Для проверки release path используйте
`Dockerfile.mcp`, `Dockerfile.site` и два hash-lock файла. `local-builder` в
`Dockerfile.site` содержит pinned Python/Zensical и зависимости без apt install.
Он потребляет подготовленные canonical `docs/ai/*` и `docs/llms*.txt`.

`scripts/build_local_site.py --output NEW_DIRECTORY --site-url URL --source-sha SHA`
работает во временной копии входов. Он не вызывает public wrapper и не меняет
canonical docs/site. Local HTML отключает аналитику, recorder, внешние шрифты
и запросы статистики GitHub. Snapshot использует неизменённый canonical producer;
его archive bytes совпадают с public producer для тех же входов и Python/zlib.
Build-time установка зависимостей требует сети; подготовленный builder может
построить local profile с `--network none`.

Статический образ собирается с именованным context
`--build-context local-site=NEW_DIRECTORY`; для base prefix используйте
`--build-arg SITE_PREFIX=kb`. Запускайте focused проверки:

```bash
V8STD_TEST_LOCAL_BUILD=1 .venv/bin/python -m unittest \
  tests.test_v8std_mcp_distribution tests.test_published_license_links -v
.venv/bin/python scripts/check_mcp_container.py \
  --mcp-image LOCAL_MCP_IMAGE --site-image LOCAL_SITE_IMAGE \
  --platform linux/arm64 --prefix /kb/ \
  --chrome '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --node /opt/homebrew/bin/node --host-gateway
```

Harness проверяет реальные HTTP/stdio, холодный и тёплый cache, владельца volume,
сигналы завершения, snippet rule, ссылки с prefix, cache headers и запросы Chrome.
Опция `--host-gateway` использует два изолированных Gateway и warm cache без
сети; она не подменяет проверку сети containerized Gateway. Harness выбирает
уникальные имена ресурсов, проверяет свободные порты и удаляет только свои
контейнеры, сети, cache и временный Catalog. Образы остаются для анализа.

Для узкой повторной проверки native Gateway используйте `--gateway-warm-only`
вместо `--host-gateway`: harness подготовит один новый cache и проверит две
warm-сессии без сети, пропуская остальные HTTP/browser сценарии. Это не тест
cold routing Gateway. Обычный SITE_URL override допускает работающий default
source; только явный флаг `--require-default-source-404` дополнительно требует
404 от default manifest для специальной регрессии запрета fallback.
