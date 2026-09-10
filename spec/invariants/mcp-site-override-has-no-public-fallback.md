---
schema_version: 1
kind: invariant
id: MCP_SITE_OVERRIDE_HAS_NO_PUBLIC_FALLBACK
scope: product
introduced_by: adr:MCP_ATOMIC_SITE_SNAPSHOTS
requirements:
  - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
  - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
owner: v8std maintainers
governs:
  - scripts/v8std_mcp_snapshots.py
  - scripts/v8std_mcp_index.py
  - docker-compose
  - overrides/main.html
  - zensical.toml
check:
  module: tests.test_v8std_mcp_distribution
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_distribution tests.test_v8std_mcp_snapshots -v
required_when: implemented
---

# Выбранный локальный сайт определяет источник и ссылки

Для нестандартного SITE_URL bootstrap, archive и их redirects остаются в
разрешённых origin/base path выбранного сайта. Внутренние article/Markdown
ссылки выдачи используют этот же base. Отказ local source не разрешает запрос
к публичному корпусу, reuse его cache или возврат публичных article URLs.

Local-site publication не выполняет фоновые запросы analytics/recorder/fonts
в public internet. Внешние provenance links остаются ссылками; их явное
открытие пользователем и build-time dependency downloads не входят в запрет.

Fitness — будущий network-deny integration test local-site+MCP+browser,
cross-origin redirect rejection, смена SITE_URL с cache и body/code link fixtures.
Проверка только env или только верхнего `url` недостаточна.
