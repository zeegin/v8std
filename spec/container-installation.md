# Локальная установка в контейнерах

Поставка состоит из двух независимых образов: `ghcr.io/zeegin/v8std-mcp`
с MCP runtime и `ghcr.io/zeegin/v8std-site` с готовым локальным сайтом.
В CI настроена сборка для `linux/arm64` и `linux/amd64`; это не подтверждение
проверки текущего выпуска на обеих платформах.

**Публикация текущего кандидата ещё не выполнена.** Команды ниже требуют действительных
image references из проверенного выпуска. Наличие Dockerfile не означает публикацию в GHCR. Не используйте
`release-pending` как установленную версию. Для локальной проверки разработчик
может явно передать теги своих тестовых образов вместо release references.

## Сайт и MCP HTTP

Получите `delivery/local/compose.yaml` из той же версии исходников и укажите проверенные
references вида `ghcr.io/zeegin/v8std-site@sha256:…` и
`ghcr.io/zeegin/v8std-mcp@sha256:…`. Значение digest относится к опубликованному
multi-platform index; локальный Docker image ID не заменяет этот digest.

У MCP и сайта разные digests. Для неизменяемой версии используйте подтверждённый
`sha-<git-sha>` или digest; `stable` служит для обнаружения версии, а не для
фиксации установки. Обновление статей может сохранить прежний runtime SHA:
это повторное использование того же образа, не новая метка исходников.
Публикация образов и корпуса не включает автоматически развёртывание сервера.

```bash
export V8STD_SITE_IMAGE='ghcr.io/zeegin/v8std-site@sha256:RELEASE_INDEX_DIGEST'
export V8STD_MCP_IMAGE='ghcr.io/zeegin/v8std-mcp@sha256:RELEASE_INDEX_DIGEST'
docker compose -p v8std-local -f delivery/local/compose.yaml up -d site
docker compose -p v8std-local -f delivery/local/compose.yaml --profile mcp up -d
curl --fail http://v8std.localhost:18765/ai/mcp/v1/manifest.json
curl --fail http://127.0.0.1:18766/healthz
```

Сайт открывается по адресу `http://v8std.localhost:18765/`, MCP — по адресу
`http://127.0.0.1:18766/mcp`. До подготовки проверенного поколения `/healthz`
отвечает `503`; `/livez` показывает только жизнь процесса. В `tools/list`
доступны пять инструментов: `v8std_search`, `v8std_get_page`, `v8std_get_related`,
`v8std_explain_snippet`, `v8std_explain_diagnostics`. MCP Resources отключены
в HTTP: capability `resources` отсутствует, все Resource methods
возвращают `-32601 Method not found`. Клиентам, использовавшим `resources/read`,
нужно перейти на поиск и чтение отдельных страниц через инструменты.
Файлы сайта `llms.txt`, `llms-full.txt` и `ai/pages.jsonl` остаются доступны
для скачивания; состав snapshot и persistent cache сохраняются.

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
Проверьте итоговое значение командой `docker compose -p v8std-local -f delivery/local/compose.yaml --profile mcp config`.

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

## HTTP-образ MCP

Образ запускает HTTP-сервис на порту 8000. Клиент подключается по URL /mcp.
Для локального использования порт публикуют только на 127.0.0.1.
Источник индекса задаётся V8STD_MCP_SITE_URL. Отдельного транспорта для локальной
работы нет. Самостоятельный Compose-сценарий MCP с публичным индексом ещё
требует завершения; текущий Compose выше описывает совместный запуск с сайтом.

## Проверка разработчиком

После сборки образов:

```bash
.venv/bin/python -m dev.checks.check_mcp_container \
  --mcp-image "$V8STD_MCP_IMAGE" --site-image "$V8STD_SITE_IMAGE" \
  --platform linux/arm64
```

Проверяются HTTP, отказ Resources, холодный старт, повторный запуск с кэшем
без сети и завершение контейнера по SIGTERM. Опция --chrome добавляет проверку
браузером. Проверка удаляет только созданные ею контейнеры, сети и тома.
