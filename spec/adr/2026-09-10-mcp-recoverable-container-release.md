---
schema_version: 1
kind: adr
id: MCP_RECOVERABLE_CONTAINER_RELEASE
scope: product
design: design:mcp-container-distribution
requirements:
  - MCP_RELEASE_SWITCH_IS_REVERSIBLE
  - MCP_SHARED_HOST_LOAD_IS_MEASURED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
aliases: []
supersedes: []
cancels: []
invariants:
  introduces:
    - invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
  preserves:
    - invariant:MCP_PUBLISHED_RUNTIME_IS_ONE_SERVICE
    - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
  replaces: {}
  cancels: []
contracts:
  introduces:
    - contract:MCP_RELEASE_RUNTIME@1.0
  preserves:
    - contract:MCP_API@2.4
    - contract:MCP_CORPUS_SNAPSHOT@1.0
    - contract:MCP_DISTRIBUTION@1.0
  replaces: {}
  cancels: []
---

# Восстанавливаемая транзакция смены runtime

## Входные требования

Обратимость переключения, измеренное совместное потребление host и независимая
раздача индексов во время перезапуска MCP.

## Решение

Host выполняет ограниченную по времени идемпотентную release-транзакцию:
проверить envelope → подготовить образ и corpus → readiness на внутреннем
порту → переключить nginx → публичный smoke → bounded drain старого.
До commit хранятся predecessor image/config и совместимые данные. Сбой после
switch приводит к rollback. SSH служит каналом передачи задания, не владельцем
жизни транзакции; host восстанавливает состояние после потери соединения.

## Влияние на инварианты

Добавляется проверяемый recoverable predecessor; единый endpoint и атомарность
snapshot сохраняются. Capacity gate включает overlap двух runtime и staging
индекса: нельзя обещать бесшовность, если они не помещаются в память host.

## Влияние на контракты

Release runtime 1.0 задаёт состояния, idempotency, наблюдаемые результаты и
fault-injection. API/distribution/snapshot contracts не меняются. Правила
выдачи CI полномочий принадлежат отдельному process design, не этому ADR.

## Отклонённые альтернативы

- `pull latest && restart` без predecessor и post-switch smoke.
- Произвольный shell из входа deploy job или обычная SSH-сессия как транзакция.
- GC прежнего image/cache до успешного переключения.
- Считать активный systemd wrapper доказательством готовности контейнера.
