---
schema_version: 1
kind: contract
id: MCP_MONITORING_PROJECTION
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:mcp-monitoring-dashboard
producer: current monitoring aggregator
consumers:
  - public legacy monitoring JSON and page
requirements:
  - MONITORING_REMAINS_PUBLIC
  - LEGACY_USAGE_EVENTS_REMAIN_READABLE
governs:
  - scripts/v8std_mcp_monitoring.py
conformance:
  module: tests.test_v8std_mcp_monitoring
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring -v
required_when: accepted
supersedes: []
deprecates: []
---

# MCP monitoring projection v1.0

## Legacy projection

Текущий aggregator продолжает формировать существующие JSON/static artifacts и
публичную страницу `/monitoring/` из legacy events. Их поля и readers
сохраняются до отдельного rollout v2 projection, чтобы текущий сайт не зависел
от design-only редизайна.

Контракт фиксирует только существующую совместимость. Он не разрешает считать
сырые query, IP или user-agent безопасными для новой публичной проекции.
