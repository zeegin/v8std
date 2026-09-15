---
schema_version: 1
kind: contract
id: MCP_CORPUS_SNAPSHOT
scope: product
version: 1
revision: 1
compatibility: backward-compatible
design: design:mcp-tools-only
producer: site artifact builder and static index publisher
consumers:
  - MCP background snapshot loader
  - local static-site image builder
  - release verifier and operators
requirements:
  - MCP_RESOURCE_PRESENTATION_IS_NOT_BUILT
  - MCP_RESOURCE_REMOVAL_PRESERVES_CORPUS_DELIVERY
  - MCP_RUNTIME_AND_CORPUS_RELEASE_INDEPENDENTLY
  - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
  - MCP_SNAPSHOT_LOAD_IS_ATOMIC
  - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
  - MCP_SNAPSHOT_IO_IS_BOUNDED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
  - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
  - MCP_OFFLINE_USES_VERIFIED_CACHE
governs:
  - scripts/generate_ai_artifacts.py
  - scripts/generate_search_vectors.py
  - scripts/v8std_mcp_index.py
  - scripts/v8std_mcp_runtime.py
  - scripts/v8std_mcp_snapshots.py
  - scripts/generate_mcp_snapshot.py
  - deploy/nginx
  - .github/workflows
  - tests/test_v8std_mcp_snapshots.py
  - tests/test_v8std_mcp_runtime.py
conformance:
  module: tests.test_v8std_mcp_tools_only
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_tools_only tests.test_v8std_mcp_runtime tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_snapshot_format -v
required_when: implemented
supersedes:
  - contract:MCP_CORPUS_SNAPSHOT@1.0
deprecates: []
---

# Corpus snapshot 1.1: прежний архив без MCP Resource presentation

Нормативно сохраняется [snapshot 1.0](mcp-corpus-snapshot-v1-r0.md) целиком,
кроме требования представлять llms/pages через MCP Resources. Формат manifest,
пять archive members, canonical content descriptor, hashes, budgets, 360-секундный
deadline, URL trust boundary, cache namespace и atomic activation не меняются.
`schema_version` остаётся 1: revision этого документа не является wire major.

Все исходные файлы, включая llms, по-прежнему проверяются на целостность.
Pages/vectors питают поиск, llms остаются совместимыми web/archive artifacts.
Runtime не создаёт дополнительные rebased full-corpus strings только для
удалённого MCP Resource surface и не удерживает их в готовом поколении.
Проверенный старый cache пригоден без принудительной миграции или download.

Семантическая перепривязка ссылок остаётся обязательной для возвращаемых tools
и самостоятельного локального сайта. Упоминание «выдаваемого pages Resource»
в предыдущей ревизии больше не является требованием MCP: такой ответ запрещён
API 4.0. Код, внешние provenance URLs, fragment/query и ranking input защищены
прежними правилами. Глобальный replace домена по-прежнему недопустим.

Это совместимое уточнение границы archive producer/loader; breaking removal
клиентских Resources отдельно оформлен API 4.0. Статическая раздача, публикация,
recovery и независимые runtime/corpus releases остаются прежними. Отсутствие
Resource presentation не является доказательством конкретного снижения RAM
или latency: их измеряют на новом runtime artifact.
