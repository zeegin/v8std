---
schema_version: 1
kind: invariant
id: MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
scope: product
introduced_by: adr:MCP_ATOMIC_SITE_SNAPSHOTS
requirements:
  - MCP_SNAPSHOT_LOAD_IS_ATOMIC
  - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
  - MCP_SNAPSHOT_IO_IS_BOUNDED
  - MCP_OFFLINE_USES_VERIFIED_CACHE
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_index.py
  - scripts/v8std_mcp_snapshots.py
check:
  module: tests.test_v8std_mcp_snapshots
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_snapshots -v
required_when: implemented
---

# Готовый MCP обслуживает запрос одним полным поколением

Ready runtime имеет валидный неизменяемый snapshot одного source namespace:
pages, vectors и Resource texts проверены по одному descriptor. Каждый запрос
удерживает это поколение до завершения. Ни один запрос не инициирует сетевое
обновление и не ждёт его lock. Background verification/parse/build не
модифицируют active generation.

Сбой загрузки, превышение любого бюджета, неизвестная schema и crash записи
не подменяют active частичным или чужим corpus. Если рабочего поколения нет,
runtime явно не готов; пустой corpus не имитирует успешную готовность.

Fitness — будущие concurrent-query generation assertions и fault-injection
каждой стадии fetch/verify/build/commit, с offline restart и bounded-resource
проверками. Медленный источник не добавляет сетевое ожидание в tool latency.
