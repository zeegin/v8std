---
schema_version: 1
kind: design
id: mcp-clean-host-installation
scope: product
requirements:
  introduces:
    - MCP_CLEAN_HOST_INSTALL_IS_DISTINCT
    - MCP_FIRST_CONTAINER_ACCEPTANCE_IS_DURABLE
    - MCP_REINSTALL_HANDOFF_PRESERVES_PUBLISHED_CORPUS
    - MCP_HOST_PROVISIONING_IS_REPLAYABLE
  uses:
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
    - MCP_RESOURCES_ARE_DISABLED
    - MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE
    - MCP_RESOURCE_PRESENTATION_IS_NOT_BUILT
    - MCP_RESOURCE_REMOVAL_PRESERVES_CORPUS_DELIVERY
    - PUBLIC_MONITORING_IS_RETIRED
    - PRIVATE_USAGE_HISTORY_IS_PRESERVED
    - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
  replaces: {}
  cancels: []
decisions:
  - adr:MCP_INITIAL_INSTALL_WITHOUT_LEGACY
  - adr:MCP_DISABLE_RESOURCES
  - adr:MCP_ATOMIC_SITE_SNAPSHOTS
  - adr:RETIRE_PUBLIC_MCP_MONITORING
invariants:
  - invariant:MCP_RELEASE_ACCEPTANCE_HAS_REAL_ORIGIN
  - invariant:MCP_TOOLS_ONLY_SURFACE_IS_STABLE
  - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
  - invariant:MCP_SITE_OVERRIDE_HAS_NO_PUBLIC_FALLBACK
  - invariant:PRIVATE_OPERATIONAL_DATA_IS_NOT_PUBLISHED
  - invariant:PUBLIC_MONITORING_ROUTES_ARE_GONE
contracts:
  - contract:MCP_RELEASE_RUNTIME@1.1
  - contract:MCP_API@4.0
  - contract:MCP_CORPUS_SNAPSHOT@1.1
  - contract:MCP_DISTRIBUTION@1.0
  - contract:MCP_USAGE_EVENTS@1.1
  - contract:MCP_MONITORING_PROJECTION@3.0
supersedes: []
cancels: []
---

# Чистая установка MCP после переустановки выделенной машины

## Граница решения

Поддерживается установка MCP на чистую ОС из заранее опубликованной поставки.
Этот режим не требует сохранённого прежнего deployment и не обещает его
восстановление. Подготовка, разрешение на остановку, установка и приёмка
автоматической доставки разделены. Публикация локального контейнера в Docker
MCP Catalog входит в состав поставки. Конкретные цели, разрешения и условия
эксплуатационной операции хранятся отдельно от публичного решения.

Это расширение действующего tools-only/distribution design, а не отмена пяти
tools, единого SITE_URL, постоянного cache, фонового refresh или ограничений
крупных процедур. Новое создание сервиса на пустом host отделено от смены
работающего release. Старый механизм миграции с Python сохраняет собственные
гарантии, но не используется для этой переустановки. Создание первого runtime
не выдаётся за обратимое переключение с прежней ОС.

## Основание и impact

`BootstrapController` требует backup manifest, legacy unit и recovery guard;
обычный `Controller.deploy` требует настоящий `active.json`. Оба механизма
не подходят для пустой машины. Подставить фиктивного предшественника означало
бы обойти проверку, а не реализовать чистую установку.

Ручная оценка семи вопросов architecture skill: добавляется режим установки,
меняются решение о первом предшественнике и его проверяемое свойство, расширяется
операторский CLI и затрагиваются release/deploy contracts. Legacy путь остаётся
корректным для миграции существующего deployment; чистая установка имеет другой
жизненный цикл. Изменение архитектурное; старые structured-документы не редактируются.

В этом пакете оформляется решение. Код установки, публикация и переустановка
ещё не выполнены. Процессные полномочия и Catalog completion определены в
[отдельном process design](2026-09-16-mcp-clean-host-release-policy-design.md).

## Требования

### MCP_CLEAN_HOST_INSTALL_IS_DISTINCT

Добавляется root-only `initial-install` для машины без принятого runtime,
legacy deployment и незавершённых runtime-транзакций. Он использует тот же
проверяемый image/config/corpus envelope, но явно помечает journal
`kind: initial-install` и не создаёт `predecessor.json`.

CI forced command, sudoers и обычный `deploy` не получают этот режим. Отсутствие
`active.json` после повреждения или удаления файла не доказывает чистую машину:
проверяются журналы, slots, owned containers и upstream. Любая неоднозначность
останавливает попытку без удаления обнаруженных данных. После первого durable
COMMITTED новый initial-install запрещён, даже если active pointer отсутствует.

Проверка: пустой host проходит; активный, ранее принятый, повреждённый либо
legacy host отвергается; CI не может вызвать новый операторский режим.

### MCP_FIRST_CONTAINER_ACCEPTANCE_IS_DURABLE

Первый runtime становится принятым только после проверки доверенного main SHA,
index/platform image digests, configuration digest, совместимого corpus,
внутреннего readiness и реального public smoke с теми же идентификаторами.
Durable COMMITTED journal — точка принятия; active pointer записывается после
неё и восстанавливается из неё, а не используется как доказательство сам по себе.

До принятия ошибка или restart возвращает обслуживаемый nginx `/mcp` в 503 с
Retry-After и останавливает только контейнер этой попытки. Индексы продолжают
раздаваться. Если остановка или закрытие маршрута не подтверждены, состояние
RECOVERY_REQUIRED, а не успешный rollback. После принятия recovery восстанавливает
принятый контейнер; прежняя ОС, Python-сервис и публичный мониторинг не запускаются.
После начала обычных updates продолжает действовать recoverable predecessor.

Проверка: разрыв SSH, отмена invoker, kill/reboot и сбой записи journal/pointer
в каждом переходе. Нельзя оставить до принятия candidate доступным по MCP после
успешного reconciliation или принять его только по `docker inspect Running`.

### MCP_REINSTALL_HANDOFF_PRESERVES_PUBLISHED_CORPUS

До остановки готовится закрытый off-host handoff новой поставки: точные source
SHA/digests, опубликованные archives и manifest, доказательства происхождения,
publication receipts/references и их sequence high-water marks. Сохраняются все
архивы, защищённые текущим manifest, незавершённым подтверждением Pages или
семидневным сроком хранения, а не только последний файл. In-flight publication
должна завершиться либо получить явный сохранённый recovery outcome до фиксации
handoff; пустая папка не подменяет историю публикации.

Handoff не содержит старую ОС, сторонние приложения, legacy app или фиктивные runtime
journals. Это доставка новой поставки, не резервная система возврата. Секреты и
закрытые usage logs передаются отдельно от публичных артефактов и не попадают
в Git, образ, Pages или доступный nginx путь. Существующие закрытые архивы не
удаляются; последний хвост usage history сохраняется отдельно перед стиранием.

На свежем host сначала восстанавливаются и проверяются static objects и
publication continuity, затем запускается MCP. При несовпадении manifest,
archive hash, receipt или sequence дальнейшая активация запрещена. Нельзя
перепубликовать отсутствующий corpus как новый успешный Pages release или
снять provenance verification ради первого запуска.

Во время переустановки недоступны и MCP, и загрузка индексов с этого host;
независимость static delivery от runtime restart не означает независимость
от удаления всей машины. Работающий локальный MCP с last-good cache продолжает
обслуживать запросы; cold installation может быть временно неготова.

### MCP_HOST_PROVISIONING_IS_REPLAYABLE

Поставка содержит повторяемую root-only настройку чистой Ubuntu 24.04 x86_64:
Docker/Compose и необходимые средства проверки, nginx/TLS, restricted publisher,
release controller/recovery, статическое хранилище, private logging и rotation.
Источник установки — проверенный main SHA, runtime — опубликованный digest;
production не собирает образ, сайт или индексы.

ОС переустанавливается отдельным операторским действием у провайдера: provisioning
не содержит API удаления/reinstall, очистки дисков, общего Docker prune или
автоматического удаления чужих vhosts. Сначала он показывает точные изменения;
при неожиданном существующем файле, symlink или сервисе останавливается.
Повтор на собственном совпадающем состоянии не стирает cache, journals и logs.

Первоначально nginx отдаёт для MCP maintenance 503; public monitoring paths
остаются 410/no-store. Наружу публикуются HTTP/TLS и административный SSH;
контейнеры доступны только через loopback. Runtime CI выключен. TLS renewal
и recovery запускаются независимо от SSH-сессии. Новая SSH identity сверяется
через доверенную консоль, после чего заменяется pin в CI; проверки SSH/TLS
не отключаются. Личный GitHub token пользователя на сервер не копируется.

Проверка: два применения к совпадающему состоянию, конфликт/симлинк/чужой
контейнер, запрет широких прав CI, maintenance и static route, сохранность
cache/logs и отказ по недоступной аутентификации provenance verifier.

## Устройство реализации

В `scripts/v8std_mcp_release.py` добавляется отдельный `InitialInstallController`
с теми же locking, envelope validation, HostAdapter verification, smoke и
bounded subprocess helpers. `recover` выбирает обработчик по сохранённому kind.
Legacy `BootstrapController` и обычный `Controller` не ослабляются и остаются
покрыты прежними regression tests. Новый flow описан в
[release contract 1.1](../contracts/mcp-release-runtime-v1-r1.md).

Отдельный `scripts/v8std_mcp_provision.py` отвечает за проверяемый fixed-path
host installation и handoff import/export; он не входит в runtime image и не
доступен publisher identity. Конкретные интерфейсы и разбиение этого модуля
фиксируются в implementation plan после проверки пакета. `deploy/container/`
содержит root-owned шаблоны maintenance, host services и разрешений; secrets
не являются шаблонными значениями по умолчанию.

Новая установка использует существующий runtime profile: non-root 10001:10001,
read-only rootfs, cap-drop ALL, no-new-privileges, init, bounded tmpfs, persistent
cache и private usage binding. Не вводится второй образ для каталога, иной
SITE_URL для ссылок или загрузка полного сайта на каждый вызов.

## Бюджеты и граница отказа от репетиции

Первичная попытка ограничена 300 s, readiness — 90 s, public smoke — 30 s,
stop — 45 s. В initial-install вместо legacy rollback резервируется 60 s на
возврат maintenance и stop. Перед попыткой образ и corpus уже доставлены и
проверены; 300 s не включает переустановку ОС или package installation.
Loader budget остаётся 360 s/read 20 s: более короткий readiness может прервать
первую попытку. Истечение времени не означает автоматическое увеличение
лимитов или ложную готовность. Таймауты обычного rollout не меняются.

Отдельный стенд, предварительный mixed-load прогон и подбор тарифа не являются
условиями этого режима первичной установки. Сохраняются локальные unit/wire
и container acceptance checks, лимиты контейнера и обычные проверки disk/FD.
Первый запуск не требует old/new overlap или выдуманного network_evidence.
Конфигурация первого контейнера ограничивает RAM и CPU; недостаток ресурсов
даёт ошибку новой установки, не запускает автоматическую покупку тарифа.

После запуска фиксируются реальные hardware, RAM/CPU/FD, active requests,
idle connections, RPS, p95/p99 и отказы. Требование измерять capacity остаётся;
его выполнение перенесено после первого запуска, не заменено утверждением
«100000 агентов». Автоматический rollout включается только при выполнении его
прежних capacity/rollback checks. Если один контейнер помещается, а два нет,
публичный MCP работает, но runtime CI остаётся выключенным и сообщается причина.

## Отклонённые варианты

- Возврат полной прежней VM — другой режим перехода, не гарантия чистой установки.
- Временный второй production host — альтернативная топология, не обязательная
  часть этого режима.
- Ручная подстановка active.json или вызов legacy bootstrap без backup — ложная
  история принятия, не способ чистой установки.
- `docker run latest` без проверки main/digest/corpus — расходится с единой
  опубликованной поставкой и лишает следующие обновления достоверной базы.
- Отключение обычного rollback вместе с отказом от возврата старой ОС — разные
  риски; откат будущих обновлений сохраняется.

## Пакет и дальнейшая работа

[ADR](../adr/2026-09-16-mcp-initial-install-without-legacy.md),
[инвариант](../invariants/mcp-release-acceptance-has-real-origin.md),
[release contract](../contracts/mcp-release-runtime-v1-r1.md),
[политика](2026-09-16-mcp-clean-host-release-policy-design.md),
[операционная последовательность](../operations/2026-09-16-mcp-clean-host-release-roadmap.md).

Это письменный design для проверки пользователем. Следующий gate по
brainstorming — просмотр пакета; после него writing-plans создаёт задачи
реализации. Здесь нет implementation checkboxes, поддельных fitness evidence
или заявления, что новое поведение уже реализовано.
