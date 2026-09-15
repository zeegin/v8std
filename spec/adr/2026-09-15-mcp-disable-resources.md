---
schema_version: 1
kind: adr
id: MCP_DISABLE_RESOURCES
scope: product
design: design:mcp-tools-only
requirements:
  - MCP_RESOURCES_ARE_DISABLED
  - MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE
  - MCP_RESOURCE_PRESENTATION_IS_NOT_BUILT
  - MCP_RESOURCE_REMOVAL_PRESERVES_CORPUS_DELIVERY
  - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
  - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
  - MCP_DISTRIBUTION_PROVENANCE_IS_VERIFIABLE
aliases: []
supersedes:
  - adr:MCP_PUBLISHED_COMBINED_RUNTIME
cancels: []
invariants:
  introduces:
    - invariant:MCP_TOOLS_ONLY_SURFACE_IS_STABLE
  preserves:
    - invariant:MCP_SNIPPET_SIGNALS_SURVIVE_TEXT_BUDGET
    - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
    - invariant:MCP_SITE_OVERRIDE_HAS_NO_PUBLIC_FALLBACK
    - invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
  replaces:
    invariant:MCP_PUBLISHED_RUNTIME_IS_ONE_SERVICE: invariant:MCP_TOOLS_ONLY_SURFACE_IS_STABLE
    invariant:MCP_LEGACY_ENDPOINT_STABILITY: invariant:MCP_TOOLS_ONLY_SURFACE_IS_STABLE
  cancels:
    - invariant:MCP_RESOURCE_LINKS_ARE_LISTABLE
contracts:
  introduces:
    - contract:MCP_API@4.0
    - contract:MCP_CORPUS_SNAPSHOT@1.1
  preserves:
    - contract:MCP_DISTRIBUTION@1.0
    - contract:MCP_RELEASE_RUNTIME@1.0
  replaces:
    contract:MCP_API@2.0: contract:MCP_API@4.0
    contract:MCP_API@2.1: contract:MCP_API@4.0
    contract:MCP_API@2.4: contract:MCP_API@4.0
    contract:MCP_CORPUS_SNAPSHOT@1.0: contract:MCP_CORPUS_SNAPSHOT@1.1
  cancels: []
---

# Отключить MCP Resources во всех способах запуска

## Входные требования

Полное отключение Resources, совместимость пяти tools, отсутствие лишней
resource presentation, сохранение corpus delivery и единого проверяемого
опубликованного runtime с прежним lifecycle.

## Решение

Один runtime предоставляет прежние пять tools без MCP Resources, Resource
templates, handlers и дополнительной подготовки их полнокорпусных текстов.
Отсутствие поддержки объявлено при initialize и реально соблюдается dispatch.
HTTP и stdio не расходятся; nginx-only блокировки и env-переключателя нет.

Наследуется опубликованный multi-platform image для одной версии во всех
launchers, один публичный `/mcp`, один active runtime в steady state и
ограниченный old/new overlap при rollout. Различия изоляции Gateway и direct
Docker/Compose сохраняются. Нет `/v3/mcp`, отдельного сервиса или code fork.

## Влияние на инварианты

Стабильность полного legacy API заменена точной стабильностью пяти tools.
Сохранение Resources более не является условием совместимости. Отменяется
инвариант принадлежности Resource links каталогу, поскольку таких ссылок и
каталога теперь нет. Ограничения snippet, приватность логов, POST-only/drain,
целостность snapshot, выбранный SITE_URL и recovery сохраняются.

## Влияние на контракты

API 4.0 — breaking для ресурсных клиентов, совместимый по прежней tool-границе.
Номер 3.0 занят историческим resource-first design и не переиспользуется.
Смена внутреннего номера не меняет protocol negotiation или URL сервиса.
Старые 2.2/2.3 уже заменены цепочкой к 2.4; новый преемник продолжает её.

Snapshot 1.1 не меняет архив или namespace cache: уточняется только отсутствие
resource presentation в MCP. Полнота проверенного поколения продолжает
включать проверку исходных файлов llms; это не требование хранить их вторую
rebased текстовую копию или выдавать их клиенту.

## Отклонённые альтернативы

Пустой каталог сохраняет discovery и capability; переключатель допускает
разные профили и более быстрый возврат. Оба варианта отклонены в пользу
явного полного отключения, согласованного пользователем.
Resource-only клиенту нужен переход на tools. Публичный сайт и статические
индексы остаются доступны; защиту от произвольного crawling это не обещает.
Производительность нового артефакта проверяется заново, старые замеры сохраняются
как история. Публикация и production activation не следуют из принятия ADR.
