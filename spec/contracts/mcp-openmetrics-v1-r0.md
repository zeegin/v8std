---
schema_version: 1
kind: contract
id: MCP_OPENMETRICS
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:mcp-openmetrics-generation
producer: MCP v2 and v3 metric registries
consumers:
  - future unified Prometheus
requirements:
  - OPENMETRICS_IS_GENERATED_LOCALLY
  - PROMETHEUS_INTEGRATION_IS_DEFERRED
  - METRICS_EXCLUDE_HIGH_CARDINALITY_LABELS
  - METRICS_ENDPOINTS_USE_LOOPBACK
  - METRIC_NAMES_ARE_VERSIONED_CONTRACTS
governs:
  - scripts/v8std_mcp_metrics.py
  - scripts/v8std_mcp_server.py
  - scripts/v8std_mcp_v3.py
conformance:
  module: tests.test_v8std_mcp_metrics
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_metrics -v
required_when: implemented
supersedes: []
deprecates: []
---

# MCP OpenMetrics v1.0

## Exposition

Каждый MCP process отдаёт `/metrics` только на loopback с content type
`application/openmetrics-text; version=1.0.0; charset=utf-8`, `Cache-Control:
no-store`, LF и завершающим `# EOF`. Публичный Nginx не proxy-ирует endpoint.

Обязательные metric families:

```text
v8std_mcp_info{api_version,resource_schema}
v8std_mcp_operations_total{api_version,method,outcome}
v8std_mcp_operation_duration_seconds{api_version,method}
v8std_mcp_operations_in_progress{api_version,method}
v8std_mcp_tool_calls_total{api_version,tool,outcome}
v8std_mcp_resource_reads_total{api_version,resource_type,outcome}
v8std_mcp_resource_list_requests_total{api_version,outcome}
v8std_mcp_resource_list_items_total{api_version}
v8std_mcp_catalog_rows{api_version}
v8std_mcp_catalog_resources{api_version}
v8std_mcp_catalog_refresh_total{api_version,outcome}
v8std_mcp_catalog_last_success_timestamp_seconds{api_version}
v8std_mcp_catalog_degraded{api_version}
v8std_mcp_agent_operations_total{api_version,agent_family,operation_class}
```

Method, outcome, resource type, agent family и operation class используют
закрытые нормализованные множества с `other`/`unknown`. Query, arguments,
page/title/URL, resource URI, cursor, diagnostic code, IP, raw client identity,
request ID, build SHA и revision запрещены как labels.

Появление новой metric family, переименование или изменение смысла labels
требует revision либо major-версию по совместимости. Scrape configuration,
retention, dashboard и alerts не входят в этот контракт.
