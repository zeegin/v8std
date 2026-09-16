---
schema_version: 1
kind: contract
id: MCP_RELEASE_RUNTIME
scope: product
version: 1
revision: 1
compatibility: backward-compatible
design: design:mcp-clean-host-installation
producer: restricted host release controller and operator-only provisioner
consumers:
  - release invoker
  - clean host operator
  - nginx edge
requirements:
  - MCP_CLEAN_HOST_INSTALL_IS_DISTINCT
  - MCP_FIRST_CONTAINER_ACCEPTANCE_IS_DURABLE
  - MCP_REINSTALL_HANDOFF_PRESERVES_PUBLISHED_CORPUS
  - MCP_HOST_PROVISIONING_IS_REPLAYABLE
  - MCP_RELEASE_SWITCH_IS_REVERSIBLE
  - MCP_SHARED_HOST_LOAD_IS_MEASURED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
governs:
  - deploy
  - scripts/v8std_mcp_release.py
  - scripts/v8std_mcp_provision.py
  - tests/test_v8std_mcp_release.py
  - tests/test_v8std_mcp_initial_install.py
  - tests/test_v8std_mcp_provision.py
conformance:
  module: tests.test_v8std_mcp_initial_install
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_initial_install tests.test_v8std_mcp_provision tests.test_v8std_mcp_release -v
required_when: implemented
supersedes: [contract:MCP_RELEASE_RUNTIME@1.0]
deprecates: []
---

# Release runtime: операторская инициализация чистого host

## Совместимость

Нормативно наследуются входная граница/envelope, verification, обычная транзакция,
legacy bootstrap, crash recovery, pinning, privacy и overload из
[ревизии 1.0](mcp-release-runtime-v1-r0.md). Понятие «первая ручная миграция» в
ней относится к пути из существующего Python deployment; в новой ревизии оно
не является единственным способом создания первого контейнера.

Прежние deploy/bootstrap команды и их результаты не ослабляются. Добавляются
операторские `initial-install`, `_initial-install` и `initial-install-recover`.
Они не входят в `release-entry.py` PUBLIC или publisher sudoers. Текущий status
показывает release_id/state/intent/error_code/cleanup_complete и для нового kind.
Схема существующего release envelope остаётся major 1.

## Допуск и состояния

`initial-install` выполняется root на установленном управляемом host с
`enabled=true`, `runtime_enabled=false`, проверенным configuration digest и
root-owned `/etc/v8std-release/initial-install.json`. Разрешение содержит ровно
schema_version 1, `mode: clean-host`, `envelope_sha256` и
`allow_no_predecessor: true`; оно привязано к одной попытке. Не является
подтверждением уведомления потребителей: человеческий stop gate выполняется
раньше переустановки, вне продукта.

Проверяются отсутствие accepted journal/active/predecessor, legacy service/app,
незавершённых release effects и чужого upstream. Совпадающий повтор возвращает
состояние прежней попытки. Другой payload с тем же ID отвергается. После FAILED
новая попытка допустима только после подтверждённого cleanup и с новым ID и
большим sequence. Unknown/corrupt state не считается пустым. COMMITTED
невозможно обойти удалением active.json; imported publication sequences также
не обнуляются и учитываются независимо от runtime sequences.

```text
RECEIVED → VERIFIED → PREPARED → READY → SWITCHED → COMMITTED
  до COMMITTED: ошибка → maintenance + stop owned candidate → FAILED
                    └─ неполный cleanup → RECOVERY_REQUIRED
  после COMMITTED: recovery принятого контейнера → завершение cleanup
```

Как и обычный deploy, работа отсоединена от SSH, сериализована общим lock и
имеет durable journal до side effects. Новый journal имеет
`kind: initial-install`, candidate identity и не имеет predecessor. Корневой
reconciler обрабатывает его явно, не вызывает legacy rollback.

До VERIFIED проверяются provenance, main ancestry, index/platform membership,
config, локальный manifest/archive и host paths. Candidate определяется по
release ID и envelope hash, использует первый разрешённый loopback port.
Pins закрепляют выбранный corpus до запуска. PREPARED/READY используют прежние
hold/readiness и полный five-tools smoke. SWITCHED — проверенный nginx reload;
COMMITTED — durable запись после public MCP/static smoke с exact identities.
Только затем записывается настоящий active.json, снимается hold и завершается
cleanup. Ни первого predecessor.json, ни поддельного успешного legacy release нет.

## Ошибка и restart

До принятия закрывается только управляемый MCP upstream: 503 с Retry-After,
static store/TLS не останавливаются. Останавливается только контейнер,
подтверждённый owned name/labels/envelope digest. Cache и journals сохраняются;
общий prune/delete отсутствует. До восстановления этой границы новая попытка
запрещена. Результат не называется ROLLED_BACK: рабочего предшественника нет.

При сбое fsync/rename состояние перечитывается с диска, не выбирается по
последнему in-memory присваиванию. COMMITTED без active.json означает
восстановление уже принятого runtime, не разрешение новой установки. Ошибка
post-commit cleanup не отменяет принятие и не включает runtime CI. Recovery
после потери SSH/reboot не зависит от действительности первоначального deadline,
но само ограничено временем; неуспех требует действия оператора.

Сохраняются transaction/readiness/smoke/stop 300/90/30/45 s; initial cleanup
reserve 60 s. У обычного rollout остаётся прежний recovery reserve 180 s.
Первый запуск не требует legacy return reserve или назначенного двухчасового
окна; timeout не создаёт неограниченных автоматических повторов. Ни один путь
не меняет loader 360 s/read 20 s.

## Host provisioning и перенос публикации

Provisioner принимает только операторские локальные файлы из проверенной
поставки, не shell/env/mount из CI envelope. Конкретный CLI и JSON schema
handoff фиксируются в implementation plan до кодирования. Вывод plan описывает
все создаваемые fixed paths; apply отказывает на неуправляемых конфликтах.
Credentials не печатаются, конфиги root-owned, publisher без общего shell,
Docker group или широкого sudo. Повторное применение не включает runtime CI.

Maintenance config и static routes устанавливаются до runtime. TLS/renewal
для публичного MCP независимы от сторонних сайтов. Handoff сохраняет signed artifacts,
manifests, publication journals/references и sequence continuity, проверяет
контрольные суммы и provenance заново при импорте. Restore не загружает legacy
runtime state, OS files, site vhosts или секреты из публичного архива.

Ошибки import оставляют maintenance, не заменяют уже опубликованный Pages
manifest. GC не запускается до проверки всех current/uncertain/grace references.
Все сохраняемые immutable URLs доступны после import по прежнему содержимому.
Остановка всего host временно прерывает раздачу; контракт гарантирует её
независимость от MCP runtime, не от переустановки ОС.

## Приёмка и conformance

До первого запуска не требуется отдельный production-like load стенд. Проверки
disk space, FD, permissions, container limits и artifact integrity сохраняются;
положительный `network_evidence` не подделывается ради initial-install.
Реальный post-install smoke и измерения не заменяются зелёным unit suite.
Обычный автоматический rollout по-прежнему требует настоящий predecessor и
capacity для old/new runtime. Успешная первая установка сама CI не включает.

Тестовая матрица: clean/dirty/legacy host; root versus restricted invoker;
duplicate/mutated/stale; wrong main/image/platform/config/corpus; invalid TLS,
nginx, readiness и public smoke; crash до/после каждого durable transition;
lost active pointer после commit; maintenance/stop failure; reboot;
повторный provisioning; imported publication history; старые deploy/bootstrap
regressions. Продолжаются guards no Resources, JSON POST, static hashes и
отсутствие секретов/raw procedures в status.
