---
schema_version: 1
kind: design
id: mcp-container-distribution
scope: product
requirements:
  introduces:
    - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
    - MCP_RUNTIME_AND_CORPUS_RELEASE_INDEPENDENTLY
    - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
    - MCP_SNAPSHOT_LOAD_IS_ATOMIC
    - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
    - MCP_SNAPSHOT_IO_IS_BOUNDED
    - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
    - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
    - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
    - MCP_RELEASE_SWITCH_IS_REVERSIBLE
    - MCP_SHARED_HOST_LOAD_IS_MEASURED
    - MCP_OFFLINE_USES_VERIFIED_CACHE
    - MCP_DISTRIBUTION_PROVENANCE_IS_VERIFIABLE
  uses:
    - MCP_COMBINED_PAGE_READING_COMPATIBLE
    - MCP_LEGACY_VERSION_REMAINS_COMPATIBLE
    - MCP_POST_ONLY_AGENT_TRANSPORT
    - MCP_EDGE_CONNECTION_CAPACITY
    - MCP_AGENT_REQUESTS_SCALE_HORIZONTALLY
    - MCP_OVERLOAD_RETURNS_RETRYABLE_STATUS
    - MCP_WORKER_DRAIN_IS_BOUNDED
    - MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES
    - MCP_RESOURCE_CATALOG_IS_PAGINATED
    - MCP_RESOURCE_LIST_USES_STABLE_SNAPSHOTS
    - MCP_RESOURCE_NOTIFICATIONS_ARE_OMITTED
    - MCP_RESOURCE_LINKS_RESOLVE_TO_LISTED_RESOURCES
    - MCP_RESOURCES_EXCLUDE_SUPPORT_PAGES
    - MCP_TEMPLATES_EXCLUDE_LANGUAGE_AND_METHOD_SOURCES
    - MCP_SNIPPET_ACCEPTED_INPUT_IS_SCANNED
    - MCP_SNIPPET_TARGETS_SURVIVE_QUERY_BUDGET
    - MCP_SNIPPET_INSTANCE_LIMIT_IS_DISCOVERABLE
    - MCP_SNIPPET_RETRIEVAL_WORK_IS_BOUNDED
    - MCP_SNIPPET_RESPONSE_STAYS_COMPACT
  replaces:
    MCP_COMBINED_ENDPOINT_CAPABILITIES: MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  cancels: []
decisions:
  - adr:MCP_PUBLISHED_COMBINED_RUNTIME
  - adr:MCP_ATOMIC_SITE_SNAPSHOTS
  - adr:MCP_RECOVERABLE_CONTAINER_RELEASE
  - adr:SNIPPET_SIGNALS_OUTSIDE_TEXT_QUERY
invariants:
  - invariant:MCP_PUBLISHED_RUNTIME_IS_ONE_SERVICE
  - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
  - invariant:MCP_SITE_OVERRIDE_HAS_NO_PUBLIC_FALLBACK
  - invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
  - invariant:MCP_SNIPPET_SIGNALS_SURVIVE_TEXT_BUDGET
contracts:
  - contract:MCP_API@2.4
  - contract:MCP_CORPUS_SNAPSHOT@1.0
  - contract:MCP_DISTRIBUTION@1.0
  - contract:MCP_RELEASE_RUNTIME@1.0
supersedes:
  - design:mcp-combined-endpoint
  - design:mcp-large-procedure-retrieval
cancels: []
---

# Единая поставка MCP, сайта и индексов

## Решение и граница этой работы

Пользователь согласовал собственный опубликованный MCP-образ для локальных
агентов и production, локальный сайт в Compose, одну настройку сайта,
раздачу индексов с `ai.v8std.ru` и автоматический production deployment из CI.
Этот пакет переводит согласование в проверяемый проект. Он ещё не является
реализацией, заявкой в Docker Catalog или разрешением удалить данные сервера.
Числовые бюджеты загрузчика ниже — предлагаемые параметры письменного пакета,
не результаты нагрузочных испытаний.

База анализа: `main` `b7bef11e145a188b30e7a7b17df2be4cb1acbd0c`.
В этой поставке нет отдельного v3, нового поискового движка, расширения
Resources или обработки целых репозиториев. Сохраняются алгоритм крупных
процедур, ограничения ответа и пять существующих tools. Политика автоматического
деплоя вынесена в [процессный design](2026-09-10-mcp-ci-deployment-policy-design.md).

## Потоки артефактов

```text
проверенный SHA main
  ├─ сборка runtime → опубликованный MCP image digest
  │                    ├─ production HTTP /mcp
  │                    ├─ локальный stdio / HTTP
  │                    └─ Docker Catalog → тот же образ
  └─ сборка контента → неизменяемый snapshot
                       ├─ nginx ai.v8std.ru/indexes/v1/<sha256>/snapshot.tar.gz
                       │    ↑ manifest публичного сайта на GitHub Pages
                       └─ static-site image с локальным manifest и snapshot
                            ↑ локальный сайт в Compose

MCP → V8STD_MCP_SITE_URL → manifest → проверенный локальный snapshot
                                   └─ URL ответов от того же SITE_URL
```

MCP скачивает подготовленный набор данных, а не обходит HTML сайта.
Обычные tool calls не обращаются к сайту или серверу индексов. nginx раздаёт
готовые файлы, не запускает генератор и не вызывает Python MCP.

## Почему нужна смена механизма, а не только Dockerfile

Текущий индекс обновляется синхронно под блокировкой из поискового пути,
pages и vectors загружаются независимо, cache не разделён по источнику.
Упаковка этого кода в контейнер сохраняет сетевые задержки, смешение поколений
и риск использования данных другого сайта. Новый загрузчик устраняет эти
причины до переключения production.

Текущий docs-builder содержит генераторы, зависимости сайта и исходники.
Runtime-образ получает только сервер и runtime-зависимости; corpus не зашит
в него. Поэтому обновление статьи не пересобирает MCP и не перезапускает его.
Самодостаточный первый запуск без сети достигается локальным сайтом либо
заранее проверенным cache, а не пустым thin image. Это отличие от предложения
PR #33 и ожидания cold-offline в issue #32 необходимо честно указать при закрытии.

## Требования

### MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE

Все способы контейнерного запуска используют один релизный multi-platform
image index в рамках одного выпуска; production закрепляет digest, а не mutable
tag. Один публичный `/mcp` сохраняет совмещённые возможности. Проверка
сопоставляет каждый способ запуска с опубликованным digest его версии.
Каталог может отставать по версии из-за внешнего review: это не другая сборка
той же версии и не причина задерживать production security update.
В устойчивом production-состоянии один
активный экземпляр; при переключении допускаются старый и новый на внутренних
портах с ограниченным drain. Это явная замена буквального требования одного
процесса/systemd unit, а не возвращение разделения v2/v3.

### MCP_RUNTIME_AND_CORPUS_RELEASE_INDEPENDENTLY

Контентный commit публикует новый snapshot без перезапуска MCP; изменение
runtime публикует образ без обязательной смены corpus. Матрица двух типов
commit подтверждает отсутствие лишнего rollout. Совместимость schema/model
проверяется до активации; изменение формата сначала выпускает совместимый
reader, затем новый manifest.

### MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS

`V8STD_MCP_SITE_URL` задаёт bootstrap manifest и основу URL ответов. Значение
по умолчанию — `https://v8std.ru/`. Второй `V8STD_MCP_PUBLIC_BASE_URL` не вводится.
Тест с сайтом под `/knowledge/` проверяет источник, article/Markdown URLs и
внутренние ссылки в телах ответов. Внешние ссылки-первоисточники не переписываются.

### MCP_SNAPSHOT_LOAD_IS_ATOMIC

Pages, vectors и тексты Resources относятся к одному проверенному поколению.
Запрос удерживает один immutable snapshot на всё время обработки. Повреждённый
архив, неизвестная схема или исчезнувший файл не меняют active snapshot.
Параллельные запросы во время refresh видят либо старое, либо новое поколение.

### MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS

Обновление выполняет один фоновый координатор на процесс, а не поиск,
`resources/read` или `get_page`. Тест замедляет источник на 60 секунд и
проверяет отсутствие сетевого I/O и ожидания refresh в рабочих запросах.
Тяжёлая подготовка поколения также не блокирует event loop; влияние CPU/GIL
и пик памяти проверяются нагрузкой, выбор executor фиксируется в plan.

### MCP_SNAPSHOT_IO_IS_BOUNDED

Manifest, скачивание, распаковка, строки JSONL, количество записей, векторы,
время и место на диске имеют отдельные пределы из snapshot contract. Тесты
включают gzip bomb, traversal, медленный поток, oversized record и повторные
ошибки; последняя рабочая копия не повреждается.

До первого выпуска пользователь явно уточнил общий monotonic budget одной
попытки до 360 секунд. Это изменение количественного предела, а не смена
фонового executor, схемы snapshot или свойства atomic activation. Сетевой read
остаётся ограниченным 20 секундами; запросы не ждут refresh, а shutdown
прерывает подготовку раньше общего предела. Host readiness и rollout имеют
собственные меньшие бюджеты и должны отменять candidate при их исчерпании.

### MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART

GET опубликованного immutable snapshot обслуживается nginx при остановленном
MCP. Он не зависит от MCP cache или временного каталога контейнера. Проверка
останавливает только runtime и сравнивает status, hash и длину файла.

### MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS

Локальная публикация поставляет свой manifest, snapshot и необходимые assets.
Заблокированный внешний интернет не мешает MCP работать с доступным локальным
сайтом и браузеру открывать его: нет фоновой аналитики, remote fonts и скрытого
fallback на публичный corpus. Пользовательский переход по внешнему источнику
не является фоновым запросом и не запрещается.

### MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE

Образ поддерживает stdio для контейнерных агентов и stateless Streamable HTTP
для production. stdout в stdio содержит только протокол; завершение stdin и
SIGTERM прекращают фоновые задачи. Warm cache переиспользуется между запусками.
Проверки включают cold/warm start, reconnect и несколько независимых сессий
агента, в том числе через Docker Gateway; контейнер на каждый tool call не нужен.

Согласованное уточнение после проверки Gateway: единый артефакт не означает
идентичные флаги всех launchers. Production и наши direct Docker/Compose
сохраняют read-only rootfs, cap-drop ALL, no-new-privileges, init и ограниченный
tmpfs. Gateway использует нативную изоляцию с проверкой non-root, init,
no-new-privileges, отсутствия privileged mode и Docker socket внутри MCP.
Отсутствующие в Gateway v0.43.3 read-only/cap-drop/tmpfs явно описываются как
различие канала, а не требование отдельного образа или причина отложить Catalog.
Обязательства по источнику данных, lifecycle, отсутствию фонового public egress
для локального сайта и проверяемому происхождению остаются без ослабления.
Реальная cold-маршрутизация Gateway и внешняя приёмка не следуют из warm-теста.

### MCP_RELEASE_SWITCH_IS_REVERSIBLE

Ошибки pull, подготовки corpus, readiness, переключения nginx и smoke после
переключения сохраняют или восстанавливают предыдущие image/config/data.
Потеря SSH и отмена CI не бросают host в промежуточном состоянии. Это
подтверждается fault-injection по каждому переходу release contract.

Уточнение первой миграции, согласованное пользователем: если одновременный
запуск не помещается в память, допускается остановка прежнего Python MCP
в отдельно назначенном окне длительностью до двух часов. Это ручная начальная
миграция с сохранённым и проверенным возвратом, не режим автоматического CI
rollout. Без даты/времени окна и разрешения на конкретный проверенный SHA
остановка не начинается. Окно не увеличивает бюджеты загрузчика и транзакции.

### MCP_SHARED_HOST_LOAD_IS_MEASURED

На production-подобном стенде одновременно воспроизводятся короткие MCP POST,
idle keep-alive, reconnect, общий NAT, refresh, скачивание индексов и rollout.
Публикуются hardware, число соединений и активных запросов, RPS, p95/p99,
ошибки, CPU/RAM, file descriptors и полоса. Цель 100 000 подключений не считается
достигнутой по значению `worker_connections` или по числу idle TCP sockets.

### MCP_OFFLINE_USES_VERIFIED_CACHE

После успешной синхронизации тот же источник работает без сети из persistent
cache. Cold start без доступного источника и без валидного cache возвращает
явную неготовность, не подменяет данные другим сайтом. Тест проверяет отдельно
cache другого origin, повреждённый cache, stale cache и recovery после сети.

### MCP_DISTRIBUTION_PROVENANCE_IS_VERIFIABLE

Образ и snapshot связываются с проверенным SHA и воспроизводимыми входами
сборки; runtime dependencies закреплены, образ имеет SBOM и provenance.
Проверяется поставляемая лицензия кода, данных и зависимостей. Публикация
собственного образа не выдаётся за статус Docker-built/Docker Official Image.

## Контракты и сохранённые решения

- [API 2.4](../contracts/mcp-api-v2-r4.md): прежний surface, stdio и readiness.
- [Snapshot 1.0](../contracts/mcp-corpus-snapshot-v1-r0.md): формат, URL, cache,
  лимиты, consistency и правила переключения поколения.
- [Distribution 1.0](../contracts/mcp-distribution-v1-r0.md): образы, параметры,
  локальный Compose и Docker Catalog.
- [Release runtime 1.0](../contracts/mcp-release-runtime-v1-r0.md): транзакция
  переключения и восстановление.

Из предшествующих combined и large-procedure designs принимаются без
изменения правила чтения страниц и весь алгоритм snippet: полный анализ
допустимого входа, отдельные сигналы, один ограниченный поиск, приоритет целей,
лимиты ответа, discovery и отсутствие исходного кода в usage logs. Их
математическая и тестовая спецификация остаётся в исторических документах.
Смена design нужна из-за ссылки на заменённое топологическое требование, а не
из-за отмены исправления PR #31. ADR `SNIPPET_SIGNALS_OUTSIDE_TEXT_QUERY`
сохраняется; его ссылка на прежний single-runtime invariant читается через
явного преемника этого инварианта.

Существующие три bulk Resources остаются совместимыми, но новые полные
каталоги и greedy discovery в эту поставку не добавляются. Их удаление или
смена политики потребует отдельного согласования. Новые snapshots — служебная
доставка corpus экземпляру MCP, а не новые MCP Resources для агента.

## Последовательность публикации и отказов

Для контента CI сначала строит и проверяет snapshot, загружает неизменяемый
файл на ai-host, проверяет его извне, затем публикует Pages с manifest этого
файла. Если загрузка или проверка неудачны, новый Pages manifest не публикуется.
Если Pages deployment не состоялся, остаётся безопасный неиспользуемый объект.
Local-site image содержит ту же версию corpus и локальную ссылку на архив;
публичный и локальный HTML могут различаться только publication profile.
Это необходимо для удаления публичной аналитики и внешних fonts локально.

Работающий MCP при временном отказе manifest или archive продолжает использовать
last-good snapshot. Runtime rollout не требует одновременного Pages deployment;
активное поколение и поколение для rollback остаются совместимыми с обоими
образами на период переключения.

## Production и внешние условия выпуска

Docker migration требует отдельной подготовки целевого сервера и свежего
замера ресурсов до начала работ.
Для автоматического rollout одновременные old/new runtime плюс staging нового
index должны поместиться с запасом. Для первой ручной миграции разрешён
описанный выше stop/start: отдельно проверяется, что новый runtime, preparation,
nginx и системные службы помещаются без старого MCP. Если это не выполняется,
миграция не начинается. Если помещается только один runtime, первая миграция
возможна, но автоматическая смена runtime остаётся выключенной до решения
capacity gate. Публикация образов и доставка corpus могут работать независимо.
Увеличение лимита nginx не устраняет дефицит памяти или полосы.

На выделенном host остаются ai.v8std.ru, SSH, TLS renewal, защита, закрытые
журналы и health/readiness. Публичный dashboard отменён отдельным согласованным
`design:mcp-public-monitoring-retirement`; его job и private bridge не сохраняем.
Посторонний vhost нельзя удалить вслепую: сначала backup вне host, проверка
зависимости default TLS от его сертификата, затем согласованный cleanup и smoke
ai/TLS/private operations. Никакая стадия CI не удаляет посторонние сайты автоматически.

Три границы приёмки нельзя смешивать:

1. Локальные gates: воспроизводимая сборка, новый код и contracts, fixture и
   container tests, security checks, смешанная нагрузка на стенде.
2. Управляемая активация: production protection/secrets, Docker, storage,
   firewall, backup/rollback, начальный digest и отдельное включение CI deploy.
3. Внешняя поставка: доступный registry artifact, post-deploy evidence, review
   Docker Catalog. Его сроки и принятие не зависят только от нашего PR.

Новый PR в v8std оформляется отдельно от PR #33. Закрывать #33 как альтернативно
решённый следует после merge, публикации и проверки локального/production
пути, с благодарностью автору и точным отличием cold-offline. Принятие в Docker
Catalog отмечается отдельно; issue #32 не закрывается автоматически. Внешние
комментарии содержат результат, а не внутренние неудачи проверок.

## Влияние и следующий gate

Архитектурное влияние нетривиально: lifecycle источника, формат corpus,
границы сети и cache, процесс агента, схема release и его авторизация.
Будущие пути: MCP server/index, генераторы AI artifacts, Docker/Compose,
nginx/systemd, workflows, local-site profile, docs и tests. В этой ветке
изменяются только новые файлы `spec/`; старые structured documents не правятся.

После просмотра письменного пакета создаётся отдельный implementation plan
со срезами loader → containers → publication → host migration → release
verification. Это порядок проектирования, не готовый plan и не разрешение
начать implementation до следующего gate. Объявленные будущие fitness-модули
в contracts/invariants ещё не существуют; `required_when: implemented` не
позволяет представить их как доказательства готовой реализации.

## Проверенные внешние границы

На 2026-09-10 Docker Registry допускает собственный образ через `--image`,
но включение требует review команды Docker; параметры надо объявлять в
catalog config. Перед отправкой нужен повторный live-check правил:
[Docker contribution guide](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md).
Выбран self-built путь, поэтому происхождение/SBOM обеспечивает наш CI.

GitHub environment и branch restrictions — отдельные защитные настройки,
их нельзя считать существующими из наличия YAML:
[GitHub deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
Для файловой раздачи используется nginx:
[nginx sendfile](https://nginx.org/en/docs/http/ngx_http_core_module.html#sendfile).
Сам перенос трафика с Pages на целевой сервер не увеличивает доступную полосу host.
