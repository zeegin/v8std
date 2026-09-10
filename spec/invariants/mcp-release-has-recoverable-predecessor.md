---
schema_version: 1
kind: invariant
id: MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
scope: product
introduced_by: adr:MCP_RECOVERABLE_CONTAINER_RELEASE
requirements:
  - MCP_RELEASE_SWITCH_IS_REVERSIBLE
  - MCP_SHARED_HOST_LOAD_IS_MEASURED
owner: v8std maintainers
governs:
  - deploy
check:
  module: tests.test_v8std_mcp_release
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_release -v
required_when: implemented
---

# Переключение сохраняет восстанавливаемого предшественника

До успешного public smoke новый runtime не уничтожает прежние image/config
и совместимый corpus. Одновременно выполняется не более одной host release
transaction. Повтор и устаревшее задание не откатывают более новый успешный
release. Потеря invoker не отменяет recovery на host.

Сбой до switch оставляет старый serving runtime. Сбой после switch приводит
к проверяемому rollback либо явному `RECOVERY_REQUIRED`, но не ложному успеху.
При нехватке памяти для old/new overlap или диска для pinned data переключение
не начинается. Для первого container cutover predecessor — сохранённый и
проверенный старый Python deployment; он не считается обычным container release.

Fitness — будущая матрица faults на переходах release contract, с проверкой
реального endpoint, exact digest и данных после восстановления. Unit mock
успешного `docker restart` не доказывает этот инвариант.
