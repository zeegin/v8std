---
schema_version: 1
kind: invariant
id: MCP_RELEASE_ACCEPTANCE_HAS_REAL_ORIGIN
scope: product
introduced_by: adr:MCP_INITIAL_INSTALL_WITHOUT_LEGACY
requirements:
  - MCP_CLEAN_HOST_INSTALL_IS_DISTINCT
  - MCP_FIRST_CONTAINER_ACCEPTANCE_IS_DURABLE
  - MCP_RELEASE_SWITCH_IS_REVERSIBLE
owner: v8std maintainers
governs:
  - deploy
  - scripts/v8std_mcp_release.py
  - scripts/v8std_mcp_provision.py
check:
  module: tests.test_v8std_mcp_initial_install
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_initial_install tests.test_v8std_mcp_release -v
required_when: implemented
---

# Принятие release имеет достоверное основание

Обычный rollout всегда имеет реально принятый predecessor image/config/corpus;
старый runtime сохраняется до успешного нового public smoke. Его отсутствие
не включает clean-host режим автоматически. Legacy bootstrap, если явно выбран,
сохраняет прежние backup/restore guards.

Только отдельная root-only операция на доказанно неинициализированном host
может впервые принять контейнер без predecessor. Вход имеет доверенные
source/image/config/corpus identities; journal предшествует побочному эффекту,
COMMITTED следует за public smoke. Наличие active.json не заменяет эти условия.
CI не создаёт такого исключения; повтор не создаёт второй принятый runtime.

До принятия reconciliation останавливает owned candidate и возвращает maintenance,
не восстанавливает старую ОС. Неудача cleanup — RECOVERY_REQUIRED. После
COMMITTED восстанавливается принятый runtime, а не пустое состояние. Durable
неопределённость не объявляется ни успешным acceptance, ни успешным rollback.

Fitness должна включать настоящие state transitions и fault injection плюс
smoke boundary; одни assertions о наличии имени команды недостаточны.
Заявленный новый test module пока не является выполненным доказательством.
