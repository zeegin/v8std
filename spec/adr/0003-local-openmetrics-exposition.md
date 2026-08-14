# ADR-0003: Локальная генерация OpenMetrics

- Статус: принято
- Дата: 2026-08-14

## Контекст

Статический dashboard показывает usage analytics, но не заменяет process
metrics и time series. Единый Prometheus будет подключён позднее отдельным
инфраструктурным изменением.

## Решение

Процессы MCP v2 и v3 независимо генерируют OpenMetrics через локальный pull
endpoint. Endpoint доступен только на loopback и не проксируется публичным
Nginx.

Текущий этап заканчивается генерацией и проверкой exposition. Конфигурация
Prometheus, Grafana, alerts, retention и сетевой scrape path в него не входят.

## Отклонённые варианты

- использовать статический сайт вместо process metrics;
- записывать request counters через node_exporter textfile collector;
- одновременно менять приложение и production Prometheus.

## Последствия

- приложение получает стабильную pull-поверхность без нового публичного route;
- до подключения Prometheus time series не сохраняются;
- точные metric families, labels и buckets меняются в design до появления
  потребителей без отмены ADR-0003;
- будущее подключение единого Prometheus является новым независимым решением и
  не заменяет ADR-0003.

## Связанные документы

- [Проект генерации OpenMetrics](../2026-08-14-mcp-openmetrics-generation-design.md)
