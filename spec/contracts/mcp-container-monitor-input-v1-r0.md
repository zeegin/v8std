---
schema_version: 1
kind: contract
id: MCP_CONTAINER_MONITOR_INPUT
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:mcp-container-monitor-input
producer: root-owned host sampler and existing runtime usage writer
consumers:
  - existing unprivileged monitoring aggregator
  - local operator
requirements:
  - MCP_MONITOR_STATE_HAS_BOUNDED_FRESHNESS
  - MCP_MONITOR_OBSERVES_SERVING_RUNTIME
  - MCP_MONITOR_RETAINS_UNPRIVILEGED_READER
  - MCP_CONTAINER_USAGE_SURVIVES_RELEASE
  - LEGACY_USAGE_EVENTS_REMAIN_READABLE
governs:
  - scripts/v8std_mcp_monitor_state.py
  - scripts/v8std_mcp_monitoring.py
  - scripts/v8std_mcp_release.py
  - scripts/v8std_mcp_server.py
  - deploy/container
conformance:
  module: tests.test_v8std_mcp_monitor_state
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_monitor_state tests.test_v8std_mcp_monitoring tests.test_v8std_mcp_release -v
required_when: implemented
supersedes: []
deprecates: []
---

# Private monitoring input 1.0

## State file и значения

Фиксированный host path `/run/v8std-monitor/state.json`; UTF-8 JSON object,
не более8192 bytes, без duplicate/unknown keys, NaN или неявного coercion.
`schema_version` — integer1, bool и float вместо integer запрещены.
Неизвестная будущая схема не интерпретируется как текущая.

Все перечисленные поля обязательны; nullable означает явный JSON null:

| Поле | Тип и смысл |
|---|---|
| `schema_version` | integer1 |
| `boot_id` | canonical UUID текущей загрузки Linux host |
| `invocation_id` | 32 lowercase hex из systemd INVOCATION_ID текущего monitoring job; null только при invalidation |
| `observed_at` | RFC3339 UTC; timestamp наблюдения, не публикации страницы |
| `observed_boottime_ns` | integer >=0, CLOCK_BOOTTIME host при завершении проверки |
| `backend` | `legacy`, `container`, `unknown` |
| `release_id` | validated release ID для container, иначе null |
| `live` | bool/null; наблюдаемая жизнь выбранного процесса |
| `ready` | bool/null; готовность того же процесса обслуживать MCP |
| `active_since` | RFC3339 UTC/null, действительный старт процесса |
| `uptime_seconds` | integer >=0/null, возраст процесса при наблюдении |
| `restarts` | integer >=0/null; legacy NRestarts, container всегда null |
| `reason` | `ok`, `transition`, `absent`, `unready`, `probe_failed`, `identity_mismatch`, `invalid_state` |

Ни paths/ports/container names, ни Docker inspect, exceptions, environment,
payloads, IP/query/User-Agent, ни вся release-квитанция в файл не копируются.
`release_id` private: в legacy public projection не переносится.

`live=true` требует подтверждённого процесса и `/livez`200 для container;
`ready=true` дополнительно требует валидного `/healthz`200 с `ok=true`,
`ready=true` и ожидаемым runtime SHA. `ready=false` допустимо при валидной
503-неготовности того же runtime. Ошибка транспорта/парсинга не равна доказанной
остановке: live/ready неизвестны. Подтверждённо отсутствующий/остановленный
выбранный runtime даёт live=false, ready=false и reason=absent.
При unknown оба bool и все uptime/restart данные null. `ready=true` при
`live!=true` недопустимо. Corpus ID может обновляться без смены runtime.

## Доверенная идентичность и race

Sampler получает цели только из root-owned validated host state, не из
state.json, args/env агрегатора, сетевого запроса или названия unit контроллера.
Короткая nonblocking release-lock секция снимает fingerprint trusted active
record, terminal/recovery state и managed upstream. Незавершённая транзакция,
busy lock или несовпадающий upstream дают unknown. Lock не удерживается во
время Docker/HTTP/proc I/O и collector не запускает recovery.

Container сверяется с approved descriptor: exact image/config revision и
ownership labels по прежней Adapter.inspect проверке. Проверяются Running,
host PID/start identity до и после HTTP-проб. Процессный возраст берётся из
наблюдения kernel process start в текущем boot; wall-clock timestamp Docker
нельзя использовать для неограниченного вычисления uptime после clock jump.
При недоступном надёжном process age `uptime_seconds` и `active_since` null,
а доказанная liveness может остаться известной. `loaded_at` не используется.

До первого принятого container и после подтверждённого legacy rollback
разрешён только зафиксированный `v8std-mcp.service`, его MainPID/start identity
и неизменённый legacy health endpoint. Не любой inactive old unit обозначает
состояние нового MCP. Корректный legacy результат не требует Docker.

Перед публикацией повторно берётся nonblocking release lock: fingerprint,
serving identity и окончание перехода должны совпасть. Иначе unknown. Под lock
происходит только сравнение trusted state и атомарная запись, без сетевых
операций. Старый collector не может вернуть healthy после начавшегося switch.

Controller атомарно инвалидирует state перед первым serving-affecting stop,
start/restart, upstream switch/restore, bootstrap или rollback side effect.
При ошибке записи пробует безопасно удалить точный старый файл, не трогая
чужие пути. Неудача обоих способов диагностируется, но не запрещает и не
откладывает owed recovery; мониторинг не имеет права блокировать восстановление.
При отказе storage старая корректная сводка может оставаться допустимой до
60s от своего наблюдения; это ограниченная устарелость, не гарантия мгновенной
актуальности. Её нельзя использовать как управляющий вход release или readiness.
Post-success не копирует COMMITTED в live; следующее наблюдение проверяет факт.

## Freshness, сохранение и reader

Root-owned parent0750 и regular file0640 с группой reader проверяются по
descriptor; symlink, hardlink count!=1, чужой owner или group/world write
отклоняются. Parent не writable reader/runtime. Temporary file создаётся в
том же parent c O_EXCL/no-follow, полное содержимое flush/fsync, rename и fsync
parent; в случае незавершённой записи reader видит прежний целый файл либо
unknown. Boot directory создаётся заново: persistent last-good не нужен.

Reader требует совпадения invocation_id с текущим systemd INVOCATION_ID,
boot_id с host, собственного CLOCK_BOOTTIME и возраста0..60s;
mtime и wall-clock не продлевают доверие. Проверка выполняется при чтении и
непосредственно перед записью готовой публичной проекции. Если данные успели
устареть/измениться, uptime пересчитывается из нового валидного наблюдения
или заменяется на unknown, без повтора aggregation и без Docker-вызова.
Обнаружение clock inconsistency не даёт отрицательного/ложного uptime.

Public mapping: статическая прежняя `service`; `active=live`,
`active_since`, `seconds=uptime_seconds`, `restarts`; `human` вычисляет прежний
normalizer. Выдаётся возраст на момент наблюдения, не экстраполяция после
возможной остановки. Private schema не передаётся через `dict.update` целиком.
`ready`, `reason`, boot/time identity и release ID в public fields не добавляются.
При неизвестном state нет fallback на active controller или старый healthy JSON.
Без нового CLI `--runtime-state-file` прежний standalone режим --service
сохраняется; production unit явно включает новый reader.

## Выполнение sampler

Фиксированная команда root из защищённого host tooling — единственный
ExecStartPre существующего monitoring job. Она делает только ограниченные
read-only наблюдения и запись state. Timer не меняется. User/Group основного
ExecStart остаются прежними; расширенного sudo verb или setuid-бинарника нет.
Команда не принимает произвольный path/target из stdin, CLI или environment.
Единственное входное значение от systemd — валидированный INVOCATION_ID,
который не выбирает путь или команду. Его отсутствие/невалидность даёт unknown.
Перед probe записывается unknown текущего invocation; завершённый результат
заменяет его. Даже SIGKILL до этой записи не позволяет reader принять файл
предыдущего запуска. Controller invalidation может писать invocation_id=null.

Предлагается общий monotonic watchdog8s с reap потомков; один probe <=2s,
HTTP body <=16KiB, CLI output <=256KiB. Нет retry-loop и DNS/public запросов:
только доверенный local Docker и фиксированный loopback target. Timeout/error
пишет unknown с code; raw command output не печатается. При аварии helper
существующий unprivileged ExecStart должен всё равно запускаться и обработать
missing/stale input. Ошибки обнаруживаемы по private диагностике, не скрываются
как успешная проверка. Native systemd test обязан проверить credentials,
watchdog, failure continuation и сохранение sandbox; один YAML/string test
этого не доказывает. Ни loader360s, ни release300s budgets не меняются.
Watchdog находится вне probe worker, а его8s включают kill/reap; поток с
невозможностью прервать I/O не подходит. Завершение watchdog — завершение
отдельной `-!` pre-команды, а не истечение TimeoutStartSec всего monitoring job:
последнее могло бы не запустить reader и потому не удовлетворяет контракту.

## Private usage stream

Отдельный новый host-файл `/var/log/v8std-mcp/tool-usage.jsonl` создаёт root
до запуска container, owner10001, группа существующего reader,0640.
Parent root:reader0750; runtime получает file bind в
`/var/log/v8std-mcp/tool-usage.jsonl` и явный `--usage-log` этого path.
Только этот файл writable, не directory/raw legacy history или control state.
Формат payload остаётся `MCP_USAGE_EVENTS@1.0`. Encoded line ограничена64KiB,
одна append-write на строку; oversize/write failure не влияет на MCP ответ и
не вызывает неограниченные повторы. Межпроцессные строки не склеиваются при
штатном append; partial I/O остаётся явно best-effort telemetry.

Новый logrotate stanza повторяет daily/365/compress/copytruncate; root
сохраняет точные owner/mode и inode file bind. Старый stanza и старая история
не меняются. Reader получает оба источника и их прежние rotation variants;
один inode не читается дважды через алиасы. Cleanup slot, rollback restore и
публикация corpus не владеют этими логами. Они недоступны из nginx/static tree.
Rotation/read race и copytruncate не дают exactly-once гарантии; этот пакет
не меняет историческую retention policy и не называет числа unique users.

## Conformance и статус

Обязательны fault cases: stale/wrong boot/clock/oversize/schema/types/owner/
symlink, write failure/SIGKILL, container absent/foreign/unready/restarted,
collector-vs-switch race, rollback legacy и refresh без сброса process age.
Тесты разделяют real process/socket/UID проверки и substituted Docker faults.
Проверяется отрицательный доступ reader к state write/Docker/release root и
отсутствие private полей в public output. Реальный container writer/overlap/
rotation/reader прогон доказывает передачу новых событий вместе с историей.
Нативная host-интеграция и server deployment — последующие внешние gates,
не результат принятия этого spec. Future tests ещё не реализованы.
