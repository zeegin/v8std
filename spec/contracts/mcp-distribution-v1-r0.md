---
schema_version: 1
kind: contract
id: MCP_DISTRIBUTION
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:mcp-container-distribution
producer: v8std image publication pipeline
consumers:
  - production runtime host
  - docker run and Compose operators
  - Docker MCP Catalog and Gateway
requirements:
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
  - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
  - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
  - MCP_OFFLINE_USES_VERIFIED_CACHE
  - MCP_DISTRIBUTION_PROVENANCE_IS_VERIFIABLE
governs:
  - docker-compose
  - Dockerfile.mcp
  - Dockerfile.site
  - deploy
  - .github/workflows
  - scripts/run_v8std_mcp.sh
  - scripts/v8std_mcp_server.py
  - overrides/main.html
  - zensical.toml
  - docs/mcp.md
  - docs/support.md
  - tests/test_v8std_mcp_distribution.py
conformance:
  module: tests.test_v8std_mcp_distribution
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_distribution -v
required_when: implemented
supersedes: []
deprecates: []
---

# Официальная поставка проекта: образы и запуск

## Артефакты

Предлагаемые registry coordinates — `ghcr.io/zeegin/v8std-mcp` и
`ghcr.io/zeegin/v8std-site`; право организации публиковать public packages
проверяется до выпуска. Если реестр недоступен, это release gate, а не повод
создать неподтверждённый альтернативный production image. Образы поддерживают
`linux/amd64` и `linux/arm64`. Immutable `sha-<git-sha>` и release tags указывают
на multi-platform image index; production и release evidence используют digest
этого index с записью выбранного platform child digest. Mutable `latest`
допустим для discovery, но не доказательство точного выпуска.

MCP image содержит только runtime, его закреплённые зависимости, лицензии и
OCI metadata исходного SHA. Не содержит Git checkout, docs generator, Zensical,
Pillow, corpus, private keys или build credentials. Публикация включает SBOM,
build provenance и проверяемую подпись/attestation доверенной workflow identity.
Production verifier не доверяет тегу или произвольной подписи из чужого workflow.
Base images и Actions закреплены по digest/SHA; обновление зависимостей проходит
тот же release путь. Лицензионная проверка данных отделена от лицензии runtime.

Static-site image содержит готовый сайт local publication profile, manifest
и archive, HTTP server без docs build на старте. Такой же исходный corpus
идёт в Pages/public snapshot. Local profile исключает публичную аналитику,
рекордер и загрузку внешних fonts/assets; build-time получение зависимостей
не обещается офлайн. Runtime сайт после установки работает без интернета.

## Интерфейс MCP image

Entrypoint непосредственно запускает runtime, без генерации индексов и shell
install на старте. Default transport — `stdio`, explicit
`--transport streamable-http` — production/local HTTP. CLI имеет приоритет
над одноимённым env; невалидный explicit input завершает процесс с ненулевым
кодом до работы с сетью. CLI `--site-url`/env `V8STD_MCP_SITE_URL` имеют единый
смысл из snapshot contract; второго public base setting нет.

Поддерживаются существующая настройка snippet limit и её порядок CLI/env,
`--cache-dir`/`V8STD_MCP_CACHE_DIR` и `--refresh-seconds`. Точное существующее
имя snippet env и диапазон наследуются из design крупных процедур; не вводится
параллельный alias. Cache path в образе — `/var/lib/v8std-mcp`, persistent volume
с документированным UID/GID. Образ работает non-root, read-only rootfs,
`cap-drop ALL`, `no-new-privileges`, без Docker socket, с writable cache и
ограниченным tmpfs. Stdio stdout чистый; healthcheck HTTP не применяется к stdio.

HTTP слушает внутренний port 8000 на `0.0.0.0`; production публикует его только
на loopback для host nginx, local Compose по умолчанию только на loopback host.
TLS/public access остаются на nginx; open proxy к произвольному SITE_URL не
создаётся. SIGTERM прекращает admission и выполняет bounded drain; EOF stdio
завершает runtime и фоновые задачи. Docker использует init для дочерних процессов.

Legacy direct Python developer/test entrypoints не удаляются в рамках смены
поставки. Старые независимые `--index-url`/`--vectors-url` не становятся
конфигурацией нового образа: их миграция явно описывается, совместное задание с
`--site-url` отклоняется. Внутренние unit-test fixtures могут использовать
локальные files; production loader не получает незаявленный legacy fallback.

## Compose и общий адрес локального сайта

Поставляется один документированный Compose без исходного bind mount:
static-site image + опциональный MCP HTTP image + persistent cache. Для сайта
без MCP не требуется запуск Python. Для одного MCP достаточно `docker run` или
каталога, сайт в Compose не обязателен при использовании публичного source.
Production использует тот же MCP image; nginx/TLS/storage host — окружение,
не другой MCP Dockerfile. Старый docs development Compose остаётся явно dev.

Оператор выбирает один site URL, достижимый с host и из контейнера. Для desktop
пример использует опубликованный host port и проверенное разрешение
`host.docker.internal` на выбранной платформе; для LAN — общий DNS/адрес host.
Именно этот адрес виден и в ссылках ответов. Linux example включает явную
проверку host-gateway, а не предполагает desktop DNS. Site base-prefix и
redirects проверяются end-to-end. Никакой скрытой подмены source на `site`
с сохранением другого public URL не допускается.

## Docker MCP Catalog

Catalog entry ссылается на наш опубликованный image digest и точный source SHA;
в нём объявлены site URL, snippet limit и persistent cache volume. Требуется
реальный прогон через Gateway: initialize/tools/list/tool call, продолжительная
сессия, повторный запуск с warm cache и несколько сессий. Жизнь контейнера
не должна ограничиваться одним tool call; настройка `longLived` проверяется
по актуальной версии Gateway. Нельзя предполагать один контейнер на всех
агентов: Gateway может изолировать сессии. Shared volume экономит downloads,
не объединяет автоматически Python heaps независимых процессов.

Каталог может временно указывать предыдущую проверенную версию, пока Docker
рассматривает обновление entry. Для каждого release image digest одинаков во
всех каналах этой версии; одновременное равенство версий каталога и production
не требуется. Новый production release не ожидает внешнего catalog review.

Проверки каталога/лицензий и принятие Docker team — внешний gate. Наш образ
официальный для проекта v8std, но без отдельного принятия не называется
Docker Official Image или Docker-built. Отказ каталога не блокирует исправный
direct Docker и production путь и не даёт оснований сообщить о публикации там.

## Приёмка

Будущие container tests проверяют оба platform artifacts, non-root/read-only,
чистый stdio, реальный HTTP POST, сохранение лимитов и cache, cold-offline
неготовность, warm-offline работу и локальный сайт с запрещённым internet egress.
Egress-проверка браузера включает fonts/analytics, а не только MCP socket trace.
CI сравнивает image digests deployment references с опубликованным
артефактом соответствующей версии. Документация показывает проверенные команды, не пример сборки
пользователем ещё одного production образа.
