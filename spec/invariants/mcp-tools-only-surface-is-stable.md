---
schema_version: 1
kind: invariant
id: MCP_TOOLS_ONLY_SURFACE_IS_STABLE
scope: product
introduced_by: adr:MCP_DISABLE_RESOURCES
requirements:
  - MCP_RESOURCES_ARE_DISABLED
  - MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE
  - MCP_RESOURCE_PRESENTATION_IS_NOT_BUILT
  - MCP_RESOURCE_REMOVAL_PRESERVES_CORPUS_DELIVERY
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_runtime.py
  - scripts/v8std_mcp_index.py
  - scripts/check_mcp_container.py
  - scripts/check_mcp_load.py
  - Dockerfile.mcp
  - compose.yaml
  - deploy
  - docs/mcp.md
  - docs/container-installation.md
check:
  module: tests.test_v8std_mcp_tools_only
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_tools_only tests.test_v8std_mcp_server tests.test_v8std_mcp_runtime tests.test_v8std_mcp_distribution tests.test_v8std_mcp_combined tests.test_v8std_mcp_snippet -v
required_when: implemented
---

# Все launchers сохраняют одну tool-границу без Resources

Один логический `/mcp` и один опубликованный multi-platform image на версию
обслуживают HTTP и stdio. В steady state production один active runtime,
во время release возможен bounded overlap проверенных old/new digests.
Catalog может отставать по версии, но не использовать другую сборку той же
версии. Launcher isolation различается только по distribution contract.

Пять прежних tools сохраняют имена, inputs, outputs, limits и retrieval.
Ни один launcher, агент, SITE_URL или режим готовности не добавляет Resources:
capability отсутствует, корректные resource requests отклоняются без доступа
к индексу, ответы tools не содержат ResourceLink/embedded Resources.

Готовое поколение не хранит дополнительные rebased llms/полный JSONL только
для Resources. Индекс поиска остаётся общим для запросов; persistent cache
старого формата, атомарность refresh и статическая доставка сохраняются.
Логи, EOF/SIGTERM, POST-only/drain и прежняя snippet-защита не ослабляются.

Fitness требует будущих wire tests обоих транспортов и реального container
surface/lifecycle test, сравнения пяти schemas/results, запрета data access
на resource error, отсутствия лишней generation presentation, warm/offline
restart и refresh. Декларация этих тестов не является выполненным доказательством.
