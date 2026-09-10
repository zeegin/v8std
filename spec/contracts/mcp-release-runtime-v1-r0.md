---
schema_version: 1
kind: contract
id: MCP_RELEASE_RUNTIME
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:mcp-container-distribution
producer: restricted host release controller
consumers:
  - release invoker
  - nginx edge
  - operators and monitoring
requirements:
  - MCP_RELEASE_SWITCH_IS_REVERSIBLE
  - MCP_SHARED_HOST_LOAD_IS_MEASURED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
governs:
  - deploy
  - scripts/v8std_mcp_server.py
  - tests/test_v8std_mcp_release.py
conformance:
  module: tests.test_v8std_mcp_release
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_release -v
required_when: implemented
supersedes: []
deprecates: []
---

# Транзакция выпуска MCP

## Входная граница

Invoker передаёт небольшой versioned JSON envelope: schema major, release ID,
монотонный sequence, полный source SHA, immutable image index digest, platform
child digest, configuration digest, совместимый corpus ID и deadline. Образ и
конфигурация проверяются по разрешённому namespace и происхождению; envelope
не содержит shell commands, arbitrary mount paths, environment passthrough
или writable path в static index store. Unknown schema и невалидные поля
отклоняются до побочных эффектов.

Host credential разрешает только валидируемый release command и отдельную
ограниченную публикацию static artifacts, не общий root shell или docker group.
CI permissions и правила выдачи credential определены process design. Host
проверяет ожидаемую publisher identity/attestation, digest и конфигурацию;
произвольный образ из доверенного registry сам по себе не разрешён.

Release ID идемпотентен: повтор с теми же полями возвращает текущий/конечный
результат; повтор с другими полями отклоняется. Sequence ниже уже принятого
не активируется. Rollback предыдущего image — часть текущей транзакции, не
старый CI job; ручной новый rollback request имеет новый sequence. Lock
сериализует releases и static manifest pointer updates, но не file GET.

## Состояния и переходы

```text
RECEIVED → VERIFIED → PREPARED → READY → SWITCHED → COMMITTED
   └──────── до SWITCHED: FAILED, старый runtime продолжает работать
                                        └─ smoke error → ROLLED_BACK
```

В VERIFIED сверяются authority, digest, compatibility и capacity. PREPARED
означает pull image, подготовленную конфигурацию и валидный corpus нового
runtime; старые image/config/data закреплены. В READY новый runtime на
внутреннем candidate port прошёл healthz и реальные initialize/tools/list/
search/get_page/explain_snippet. Проверяются runtime SHA и corpus ID.

SWITCHED — атомарная замена управляемого upstream include, успешный `nginx -t`
и reload. Если проверка конфигурации не прошла, старый include восстанавливается
до reload. Публичный smoke проверяет TLS, `/mcp`, правильный image/corpus и
сохранение static index download. COMMITTED наступает только после smoke,
затем старый runtime завершает ограниченный drain.

Предлагаемые safety budgets: вся host-транзакция до 5 минут; readiness до
90 секунд в пределах общего deadline; post-switch smoke до 30 секунд;
drain старого runtime до 30 секунд и окончательный stop до 45 секунд.
Исчерпание бюджета не оставляет candidate активным без результата. Значения
проверяются на production-подобном стенде до включения автоматизации.

Ошибка после switch возвращает predecessor config/upstream, reload и
проверяет старый endpoint; candidate прекращает admission и завершается.
Rollback failure — отдельный terminal `RECOVERY_REQUIRED` с alert и сохранёнными
артефактами; нельзя обозначать его как успешный rollback. Предыдущий runtime
не останавливается до успешного post-switch smoke нового.

## Crash recovery и данные

Release controller исполняется как ограниченная host job независимо от жизни
SSH. Durable journal фиксирует intent и каждый переход с fsync до необратимой
операции. На restart reconciler сравнивает journal, реальные контейнеры и nginx
upstream; непринятый SWITCHED release возвращается к predecessor. Два controller
не выполняют операции одновременно. Нельзя счесть отмену CI успешным deploy.

Pinned generations и текущие cache pointers разделены. Candidate может скачать
и проверить новый corpus, но не меняет данные, нужные старому для rollback.
На время release автоматическое следование manifest не отбирает совместимый
rollback snapshot. После commit normal refresh возобновляется; unsupported
schema/model оставляет последний валидный index и выдаёт сигнал оператору.

Predecessor включает не только image, но и configuration digest, cache schema
и валидный corpus; предыдущий image не обязан читать будущую schema. Retention
хранит хотя бы один успешно работавший predecessor и все in-flight pins.
Первые migration/startup не выдают отсутствие predecessor за гарантию rollback:
до начального container cutover сохранены Python deployment и его конфигурация,
данные и проверенный путь возврата. После проверки первого container release
формируется обычная цепочка predecessors.

## Host и нагрузка

nginx static store не находится внутри runtime container или MCP cache.
Контейнеры слушают loopback; наружу открыты только необходимые TLS/MCP и
административные порты согласно host inventory. Сертификаты, renewal и
мониторинг проверяются независимо от application migration. Systemd active
wrapper без готового контейнера не удовлетворяет readiness.

Перед переключением capacity check проверяет disk headroom для pull/staging,
RAM для old+new runtime и index preparation, file descriptors и сетевой бюджет.
При дефиците switch не начинается. Admission ограничивает одновременно
выполняемые MCP запросы, idle keep-alive и большие downloads раздельно;
перегрузка отвечает retryable status по прежней edge policy. Конкретные
настройки допускаются в production только после mixed-load evidence.

## Наблюдаемость и conformance

Structured result содержит release ID/sequence, exact digests/SHA/corpus,
время, конечное состояние и компактный error code. Secrets, raw procedures и
arbitrary command output не попадают в public status. Мониторинг различает
runtime liveness, readiness, stale corpus, refresh failures, deploy/rollback
failures, memory/FD exhaustion и static egress. Расширенный публичный dashboard
из других designs не объявляется реализованным этим контрактом.

Будущий module плюс стенд проверяют duplicate/stale/concurrent jobs, failed
pull/signature/config, corrupt corpus, readiness timeout, invalid nginx config,
post-switch failure, SSH drop, CI cancellation, kill/reboot между каждым
переходом и rollback failure. Сравниваются реальные endpoint/digest/state,
а не только exit code controller. Отдельный mixed-load отчёт фиксирует
предельную проверенную нагрузку; 100 000 подключений пока являются целью.
