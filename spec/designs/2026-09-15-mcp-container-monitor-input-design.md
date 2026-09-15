---
schema_version: 1
kind: design
id: mcp-container-monitor-input
scope: product
requirements:
  introduces:
    - MCP_MONITOR_STATE_HAS_BOUNDED_FRESHNESS
    - MCP_MONITOR_OBSERVES_SERVING_RUNTIME
    - MCP_MONITOR_RETAINS_UNPRIVILEGED_READER
    - MCP_CONTAINER_USAGE_SURVIVES_RELEASE
  uses:
    - MONITORING_REMAINS_PUBLIC
    - LEGACY_USAGE_EVENTS_REMAIN_READABLE
    - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
    - MCP_RELEASE_SWITCH_IS_REVERSIBLE
    - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  replaces: {}
  cancels: []
decisions:
  - adr:MCP_PRIVATE_CONTAINER_MONITOR_INPUT
invariants:
  - invariant:MCP_MONITOR_STATE_TRUST_IS_BOUNDED
  - invariant:OPERATOR_DATA_STAYS_OUTSIDE_WEB_ROOT
  - invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
contracts:
  - contract:MCP_CONTAINER_MONITOR_INPUT@1.0
  - contract:MCP_MONITORING_PROJECTION@1.0
  - contract:MCP_USAGE_EVENTS@1.0
  - contract:MCP_RELEASE_RUNTIME@1.0
supersedes: []
cancels: []
---

# Вход мониторинга после контейнерной миграции

## Согласованное направление и статус пакета

Пользователь согласовал закрытый файл свежего состояния без доступа агрегатора
к Docker. Этот пакет уточняет обнаруженную в Task6 границу producer/consumer;
числа и интеграционные детали ниже предлагаются на письменное рассмотрение.
База: `f78b81c6b49d20102735fb0847fb726a06551691`, feature-ветка
`codex/mcp-container-distribution-design`. Реализация ещё не начата.

Нет второго MCP, нового daemon/timer, public endpoint, версии событий,
редизайна dashboard или изменений модели индекса. Схема публичных полей остаётся
legacy. Этот пакет дополняет container design, а не заменяет его или старый
design будущей аналитики. Права на публикацию и production не расширяются.

## Причина

Сейчас `read_service_uptime()` читает `v8std-mcp.service`, который после
миграции остановлен. Новый launcher не передаёт `--usage-log`. Замена имени
unit на release-controller не помогает: COMMITTED означает результат операции,
а active wrapper — процесс контроллера, не жизнь MCP. `loaded_at` меняется
при refresh индекса и также не является временем старта процесса.

Прежнее требование сохранить мониторинг верно, но его доверенная граница была
недоописана. Зелёные старые тесты не закрывают этот пробел.

## Требования

### MCP_MONITOR_STATE_HAS_BOUNDED_FRESHNESS

Отчёт принимает только завершённое наблюдение текущего запуска monitoring job
и текущей загрузки host не старше60 секунд на момент публикации. Отсутствие,
повреждение, чужой владелец,
неподдерживаемая схема или истёкший возраст дают unknown, не healthy и не down.
Wall-clock перевод не делает старую запись свежей. Collector ограничен
8 секундами, включая ожидания/очистку; это предлагаемые бюджеты новой границы,
не изменение 360-секундного loader или release transaction.

### MCP_MONITOR_OBSERVES_SERVING_RUNTIME

Наблюдается только подтверждённый serving predecessor/active runtime,
сопоставленный с managed upstream, реальным процессом и ответами этого процесса.
Живой candidate, чужой контейнер, квитанция или ложный upstream не дают healthy.
Во время switch/неоконченного rollback допустим unknown. Stop/reboot/refresh
проверяются отдельно; обновление corpus не сбрасывает process uptime.

### MCP_MONITOR_RETAINS_UNPRIVILEGED_READER

Root выполняет только фиксированный bounded sampler. Агрегатор сохраняет
`v8std-mcp:v8std-mcp`, доступ adm к nginx logs и запись только своего output.
Ни агрегатор, ни MCP не получают Docker socket/group, sudo, возможность выбрать
root-команду, её путь, target или environment. Private state не является
управляющим входом release-controller.

### MCP_CONTAINER_USAGE_SURVIVES_RELEASE

Новые экземпляры пишут прежние события в отдельный persistent private log,
независимый от slots/cache. Агрегатор читает прежнюю историю и новый log;
перезапуск, rollback и очистка slot их не удаляют и не восстанавливают из backup.
Сохраняется best-effort характер telemetry и существующая политика
daily/365/copytruncate, без обещания нулевых потерь при copytruncate.

## Компоненты и данные

1. Существующий `v8std-mcp-monitoring.service` получает короткий root
   `ExecStartPre` sampler. Его `ExecStart` по-прежнему запускает непривилегированный
   агрегатор. Существующий timer и его пятиминутный период не меняются.
2. Sampler из root-owned `/opt/v8std-release/scripts/` читает ограниченную
   выборку доверенного release state и проверяет runtime. Пишет только
   `/run/v8std-monitor/state.json`, атомарно и без пользовательских payload.
3. Reader читает этот файл, повторно проверяет свежесть непосредственно перед
   публикацией и передаёт только прежние uptime-поля в legacy renderer.
4. Runtime получает writable bind только отдельного файла
   `/var/log/v8std-mcp/tool-usage.jsonl`, не каталога state/cache/логов host.
   Старый `/var/lib/v8std-mcp/tool-usage.jsonl` и его owner не меняются.

Один общий новый log допустим для ограниченного old/new overlap, поскольку
события не являются управляющими данными. Запись одной сериализованной строки
делается одной ограниченной append-операцией; частичные строки остаются
ошибками telemetry, а не ошибками MCP. Нельзя обещать exactly-once или считать
internal smoke calls отдельными людьми. Межпроцессный append проверяется
реальными параллельными writers, а его стоимость входит в общий mixed-load.

## Привилегии и установка

Для единственной root-команды выбирается `ExecStartPre` с префиксом `-!`, а не
`+`: первый меняет credentials, не снимая остальные sandbox-настройки unit.
`-` позволяет основному reader запуститься после отказа sampler; несовпадающий
с текущим systemd invocation ID файл тогда не принимается даже внутри TTL.
Смысл проверен по [systemd v255](https://github.com/systemd/systemd/blob/v255/man/systemd.service.xml).
Нативная проверка установленной версии systemd остаётся gate перед активацией.
Root sampler не импортирует код из writable каталогов; использует isolated
Python, фиксированный PATH и endpoint Docker, без наследуемых Docker/Python
параметров. Обычный пользователь не может изменять unit или sampler.

`/run/v8std-monitor` создаётся root при host setup/boot с mode0750 и группой
`v8std-mcp`; файл root:`v8std-mcp`0640. Добавление каталога в ReadWritePaths
не даёт агрегатору DAC write. Root release state остаётся0700. Raw log имеет
UID10001, группу `v8std-mcp` и0640, parent root:`v8std-mcp`0750. Числовой GID
группы определяется на host; runtime остаётся10001:10001 и пишет как owner.
nginx/CI не входят в эту группу. Проверяется отсутствие иных путей доступа.

Новый monitor code устанавливается как host tooling вместе с controller,
не зависит от изменяемого container cache. Python runtime старого сервиса
остаётся доступным для rollback. Установка/boot directory rules, unit и
logrotate policy входят в будущий локальный plan; применение на host отдельно.

## Совместимость и ошибки

Точные поля, идентичность и invalidation определяет
[private input contract](../contracts/mcp-container-monitor-input-v1-r0.md).
`uptime.service` сохраняет логическую legacy-метку; image/port/path/journal
не добавляются в публичный JSON. `active` остаётся liveness, не readiness.
Readiness и failure reason доступны только в private state.

Для container `restarts` возвращается `null`: надёжного общего счётчика
Docker-policy и ручных/controller перезапусков сейчас нет. `RestartCount`
нельзя выдавать за их сумму, а пропущенные между polls рестарты — считать
нулём. Legacy сохраняет `NRestarts`. Поле и допустимый тип сохраняются; потеря
числовой метрики при смене backend явно принята к рассмотрению, не спрятана.
Введение точного lifecycle counter требует отдельного решения и не входит сюда.

Ошибка sampler даёт unknown и краткую диагностику без raw output. Агрегатор
продолжает строить статистику; невозможность его публикации сохраняет прошлый
артефакт с прежним `generated_at`. Batch-страница — наблюдение на указанное
время, не real-time alert: истечение TTL файла не изменяет уже отданный HTML.
State не разрешает и не запрещает recovery. Перед serving mutation controller
инвалидирует его, но ошибка invalidation не задерживает аварийный возврат:
остаётся явная диагностика и верхняя граница доверия60s. Принципиально нельзя
обещать мгновенную актуальность статического отчёта при отказе его storage.

У текущего renderer есть отдельная известная публикация поисковых текстов
(`search_events`, HTML и stats.json). Private state этих данных не содержит;
этот пакет не объявляет реализованным общий privacy invariant будущего
dashboard и не отменяет его. Перед публичным выпуском нужна отдельная
диспозиция этого риска; сохранение схемы не является разрешением на утечку.

## Проверки и включение в оставшуюся работу

Будущая conformance проверяет fresh/stale/boot/schema/owner/symlink/oversize,
живой candidate вместо serving, missing/foreign/restarted контейнер,
раздельные live/ready, refresh без сброса uptime, collector во время switch и
SIGKILL между invalidation и side effect. Сбой чтения не вызывает Docker от
имени агрегатора. Реальный launcher/logger/rotation/aggregator проверяется
с UID10001 и прежней историей, включая overlap и rollback.

После письменного рассмотрения пакета writing-plans создаёт отдельный
незавершённый plan этого среза, связанный с Task6 основного container plan:
контракт/reader → sampler/invalidation → logs/unit integration → совместимость.
Только после его реализации и review возобновляется оставшаяся Task6 CI.
Ранее пройденные тесты относятся к прежнему коду и не принимают этот design.
Ни весь container design, ни внешние release/capacity gates не становятся
IMPLEMENTED от завершения этого небольшого среза.

## Отклонённые варианты

- Docker socket/group или произвольный sudo у reader: новая избыточная власть.
- Фиксированный sudo RPC: возможен, но создаёт вызываемую привилегированную
  поверхность; для batch-reader достаточно файла.
- Сбор только во время deploy/recover: связывает свежесть с ремонтом runtime,
  а не генерацией мониторинга; требует отдельного расписания или budget coupling.
- Новый daemon/exporter: не требуется для сохранения текущего batch-dashboard.

Semantic impact: добавлена private boundary и уточнены обязанности freshness/
runtime identity; существующие требования/ADR/invariants сохраняются, ничего
не отменяется. В этом шаге создаются только новые spec-файлы; structured main,
runtime, units, permissions и production не меняются.
