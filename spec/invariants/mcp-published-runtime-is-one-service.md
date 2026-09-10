---
schema_version: 1
kind: invariant
id: MCP_PUBLISHED_RUNTIME_IS_ONE_SERVICE
scope: product
introduced_by: adr:MCP_PUBLISHED_COMBINED_RUNTIME
requirements:
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_server.py
  - Dockerfile.mcp
  - docker-compose
  - deploy
check:
  module: tests.test_v8std_mcp_distribution
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_distribution tests.test_v8std_mcp_combined -v
required_when: implemented
---

# Один логический сервис из опубликованного runtime image

В production существует один публичный `/mcp` без самостоятельного v3
endpoint/listener/profile. В устойчивом состоянии один активный runtime;
ограниченный overlap old/new при release не создаёт второго пользовательского
сервиса. Каждый serving container относится к проверенному опубликованному
release digest, старому или новому; произвольная локальная сборка не участвует.

Local stdio/HTTP и catalog используют тот же multi-platform image для той же
версии, с допустимым различием platform child digest. Отставание версии catalog
из-за внешнего review не создаёт вторую сборку и не блокирует production release.
Пять tools, существующие Resources и
snippet-поведение совпадают. CPU architecture, транспорт и конфигурация сайта
не выбирают другую кодовую реализацию MCP.

Равенство артефакта и API не означает равенства флагов изоляции launchers.
Production/direct Docker/Compose и Gateway применяют явно различённые профили
distribution contract; это не отдельные сборки или сервисы.

Fitness — будущие проверки digest/reference parity, surface parity, отсутствие
v3 route, warm agent session и ограниченный old/new overlap. Наличие этого
файла не означает, что контейнеры уже собраны или опубликованы.
