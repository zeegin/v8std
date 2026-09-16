---
schema_version: 1
kind: adr
id: MCP_INITIAL_INSTALL_WITHOUT_LEGACY
scope: product
design: design:mcp-clean-host-installation
requirements:
  - MCP_CLEAN_HOST_INSTALL_IS_DISTINCT
  - MCP_FIRST_CONTAINER_ACCEPTANCE_IS_DURABLE
  - MCP_REINSTALL_HANDOFF_PRESERVES_PUBLISHED_CORPUS
  - MCP_HOST_PROVISIONING_IS_REPLAYABLE
  - MCP_RELEASE_SWITCH_IS_REVERSIBLE
  - MCP_SHARED_HOST_LOAD_IS_MEASURED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
aliases: []
supersedes: [adr:MCP_RECOVERABLE_CONTAINER_RELEASE]
cancels: []
invariants:
  introduces: [invariant:MCP_RELEASE_ACCEPTANCE_HAS_REAL_ORIGIN]
  preserves:
    - invariant:MCP_PUBLISHED_RUNTIME_IS_ONE_SERVICE
    - invariant:MCP_TOOLS_ONLY_SURFACE_IS_STABLE
    - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
  replaces:
    invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR: invariant:MCP_RELEASE_ACCEPTANCE_HAS_REAL_ORIGIN
  cancels: []
contracts:
  introduces: [contract:MCP_RELEASE_RUNTIME@1.1]
  preserves:
    - contract:MCP_API@2.4
    - contract:MCP_API@4.0
    - contract:MCP_CORPUS_SNAPSHOT@1.0
    - contract:MCP_CORPUS_SNAPSHOT@1.1
    - contract:MCP_DISTRIBUTION@1.0
  replaces:
    contract:MCP_RELEASE_RUNTIME@1.0: contract:MCP_RELEASE_RUNTIME@1.1
  cancels: []
---

# Отличать первичную установку от обратимого обновления

## Входные требования

Самостоятельная чистая установка, достоверное принятие первого runtime,
сохранение опубликованного corpus при переустановке и повторяемая настройка
host. Гарантии возврата при обычной смене принятого release сохраняются;
производительность подтверждается измерениями, не фактом установки.

## Решение

На пустом host создаётся первый принятый release без legacy predecessor через
отдельную root-only операцию. Она не является вариантом обычного CI deploy и
не расширяет полномочия publisher. Первый public smoke и durable journal
создают базу для будущего rollback; фиктивная история запрещена.

Переустановка ОС уничтожает прежнюю эксплуатационную базу по явному выбору
владельца. Её последствия не маскируются гарантиями старого migration flow:
до первого принятия возможен только ремонт новой установки и явная неготовность.
После принятия восстанавливается новый runtime; обычная смена release сохраняет
предыдущие image/config/corpus и прежние recovery guarantees.

## Влияние на инварианты

Прежний инвариант требовал predecessor также для любого первого container cutover.
Он заменён свойством о двух достоверных источниках принятия: реальный predecessor
при обновлении либо явная clean-host initialization. Исторические ссылки на
single-runtime/API/snapshot читаются через существующих tools-only преемников;
Resources и прежний API не возвращаются.

## Влияние на контракты

Release contract получает совместимую ревизию: старые deploy/bootstrap и envelope
не меняют поведение; добавляется отдельный операторский initial-install с явным
исходом без rollback. Контракт не обещает сохранение static endpoint при удалении
всей ОС. Prepared artifacts сохраняются вне стираемой машины и импортируются
до первого runtime acceptance.

Нет прежнего условия двухчасового окна с возвратом для clean-host операции.
Остаются bounded попытки, пауза владельца перед остановкой и recovery новых
компонентов. Отдельный stage load rehearsal отменён; проверка настоящей готовности
и ограничений будущих автоматических обновлений не отменена.

## Отклонённые альтернативы

Полная VM-копия и второй production host относятся к другим схемам перехода,
не являются необходимой частью чистой установки. Повторное использование
legacy bootstrap без backup или создание active.json вручную не обеспечивает
корректного принятия и отклонено.
