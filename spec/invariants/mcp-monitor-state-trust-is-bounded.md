---
schema_version: 1
kind: invariant
id: MCP_MONITOR_STATE_TRUST_IS_BOUNDED
scope: product
introduced_by: adr:MCP_PRIVATE_CONTAINER_MONITOR_INPUT
requirements:
  - MCP_MONITOR_STATE_HAS_BOUNDED_FRESHNESS
  - MCP_MONITOR_OBSERVES_SERVING_RUNTIME
  - MCP_MONITOR_RETAINS_UNPRIVILEGED_READER
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_monitor_state.py
  - scripts/v8std_mcp_monitoring.py
  - scripts/v8std_mcp_release.py
  - deploy/container
check:
  module: tests.test_v8std_mcp_monitor_state
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_monitor_state -v
required_when: implemented
---

# Состояние не переживает границу доверия

Положительная liveness допустима только для свежего root-owned наблюдения
текущей загрузки host, идентичность процесса которого совпала с serving
runtime. Просрочка, race переключения или повреждение не превращаются в успех.
Reader не может подделать сводку, управлять Docker или публиковать её целиком.

Fitness включает реального непривилегированного reader, race collector/switch,
boot/clock/freshness/identity faults и отсутствие private fields в projection.
Декларация будущего теста не является выполненным доказательством.
