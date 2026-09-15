---
schema_version: 1
kind: design
id: mcp-public-monitoring-retirement
scope: product
requirements:
  introduces:
    - PUBLIC_MONITORING_IS_RETIRED
    - PRIVATE_USAGE_HISTORY_IS_PRESERVED
    - MONITORING_RETIREMENT_PRESERVES_MCP
  uses:
    - OPERATOR_DETAILS_STAY_OUTSIDE_WEB_ROOT
    - MCP_RELEASE_SWITCH_IS_REVERSIBLE
  replaces:
    MONITORING_REMAINS_PUBLIC: PUBLIC_MONITORING_IS_RETIRED
    PUBLIC_MONITORING_EXCLUDES_SENSITIVE_DATA: PUBLIC_MONITORING_IS_RETIRED
    LEGACY_USAGE_EVENTS_REMAIN_READABLE: PRIVATE_USAGE_HISTORY_IS_PRESERVED
    MCP_CONTAINER_USAGE_SURVIVES_RELEASE: PRIVATE_USAGE_HISTORY_IS_PRESERVED
  cancels:
    - MONITORING_SHOWS_AGENT_FAMILIES
    - MONITORING_SHOWS_API_VERSIONS
    - MONITORING_SHOWS_MCP_OPERATIONS
    - MCP_MONITOR_STATE_HAS_BOUNDED_FRESHNESS
    - MCP_MONITOR_OBSERVES_SERVING_RUNTIME
    - MCP_MONITOR_RETAINS_UNPRIVILEGED_READER
decisions: [adr:RETIRE_PUBLIC_MCP_MONITORING]
invariants:
  - invariant:PUBLIC_MONITORING_ROUTES_ARE_GONE
  - invariant:PRIVATE_OPERATIONAL_DATA_IS_NOT_PUBLISHED
  - invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
contracts:
  - contract:MCP_MONITORING_PROJECTION@3.0
  - contract:MCP_USAGE_EVENTS@1.1
  - contract:MCP_RELEASE_RUNTIME@1.0
supersedes:
  - design:mcp-monitoring-dashboard
  - design:mcp-container-monitor-input
cancels: []
---

# Полное отключение публичного мониторинга

## Согласование и границы

Пользователь запросил полное удаление публичного мониторинга и подтвердил
предложенный письменный scope словом «согл» 2026-09-15: отключить job/timer,
убрать HTML/JSON и alias, вернуть 410, удалить генератор и ссылки, отменить
старые требования и исключить сохранение dashboard из container release.
Подтверждение явно включает production. Существующие файлы сначала переносятся
в закрытый архив. Это фиксация согласованного решения, не расширение полномочий.

Не входят: MCP deploy/restart, push, публикация Docker, удаление raw logs,
чужих vhosts, TLS/renewal, SSH или fail2ban. Health/readiness, закрытая
диагностика и recoverable release сохраняются. Отдельный design локальных
OpenMetrics не отменяется и не реализуется этой работой.

## Требования

### PUBLIC_MONITORING_IS_RETIRED

На production и в следующей поставке `/monitoring` и всё `/monitoring/`
возвращают HTTP410 с `Cache-Control: no-store`, без прежнего отчёта или redirect
на него. Генератор, timer/service и deploy-ссылки больше не публикуют dashboard.
Прежние файлы не остаются ни в web root, ни за другим alias.

### PRIVATE_USAGE_HISTORY_IS_PRESERVED

Существующие access/usage logs и rotation сохраняются без переписывания истории
или изменения формата. Отмена aggregator не отменяет закрытые JSONL-события.
Container migration не может удалить прежние журналы; persistent private
usage logging для нового runtime остаётся отдельной проверкой выпуска.
Новый sampler, dashboard reader и его log-to-public pipeline не создаются.

### MONITORING_RETIREMENT_PRESERVES_MCP

Изменяются только мониторинговые unit/files и два nginx location.
После успешного `nginx -t` используется reload. PID и время старта MCP
не меняются; health и реальные initialize/tools/list остаются успешными.
Архив root-owned0700 вне web root содержит оригинальную конфигурацию,
unit/drop-in, генератор и опубликованные файлы для ручного восстановления.

## Решение и альтернативы

Выбрано полное прекращение публикации, а не скрытие ссылки, `noindex` или
пароль поверх существующего генератора. Удаление только HTML оставило бы
публичный JSON и timer, воссоздающий оба файла. Поэтому отключается вся цепочка.
Архив не обслуживается HTTP и не включается в Git или Docker context.
Уже скачанные сторонними клиентами копии отозвать невозможно; прежний origin
отдавал max-age60, после смены отдаёт no-store.

Legacy projection и её не реализованный редизайн заменены tombstone-контрактом.
Dashboard-specific v2 events и private monitor-input contract отменены:
их producer/consumer ещё не реализованы и больше не нужны этому dashboard.
Это не удаляет нынешний logger и не запрещает отдельное будущее проектирование
закрытой телеметрии. Privacy-инвариант оператора заменён эквивалентным вне
зависимости от удалённого renderer; принятую историю в main не переписываем.

## Проверки и восстановление

До изменения фиксируются HTTP-коды, unit state, MCP PID/start и права журналов.
После остановки timer/service оригиналы перемещаются в root-only archive;
оба unit маскируются от случайного запуска. Nginx получает только два tombstone
location; при ошибке `nginx -t` исходный конфиг восстанавливается без reload.
Проверяются GET/HEAD, JSON/query/unknown descendant, отсутствие генератора и
публичного каталога, masked/inactive units, сохранение процесса и MCP ответов.
Локальный настоящий nginx проверяет shipped include, в том числе при лежащих
под ним старых файлах и при недоступном MCP upstream.

Rollback конфигурации и файлов технически возможен из архива, но повторная
публикация мониторинга требует нового явного решения пользователя. Для ремонта
nginx сначала сохраняется закрытая граница, а не автоматически возвращается
утечка. Изменение не доказывает производительность на100000 подключений.
