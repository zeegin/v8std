---
schema_version: 1
kind: design
id: mcp-tools-only
scope: product
requirements:
  introduces:
    - MCP_RESOURCES_ARE_DISABLED
    - MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE
    - MCP_RESOURCE_PRESENTATION_IS_NOT_BUILT
    - MCP_RESOURCE_REMOVAL_PRESERVES_CORPUS_DELIVERY
  uses:
    - MCP_ONE_LOGICAL_SERVICE_FROM_PUBLISHED_IMAGE
    - MCP_RUNTIME_AND_CORPUS_RELEASE_INDEPENDENTLY
    - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
    - MCP_SNAPSHOT_LOAD_IS_ATOMIC
    - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
    - MCP_SNAPSHOT_IO_IS_BOUNDED
    - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
    - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
    - MCP_CONTAINER_DISTRIBUTION_SUPPORTS_AGENT_LIFECYCLE
    - MCP_RELEASE_SWITCH_IS_REVERSIBLE
    - MCP_SHARED_HOST_LOAD_IS_MEASURED
    - MCP_OFFLINE_USES_VERIFIED_CACHE
    - MCP_DISTRIBUTION_PROVENANCE_IS_VERIFIABLE
    - MCP_POST_ONLY_AGENT_TRANSPORT
    - MCP_EDGE_CONNECTION_CAPACITY
    - MCP_AGENT_REQUESTS_SCALE_HORIZONTALLY
    - MCP_OVERLOAD_RETURNS_RETRYABLE_STATUS
    - MCP_WORKER_DRAIN_IS_BOUNDED
    - MCP_SNIPPET_ACCEPTED_INPUT_IS_SCANNED
    - MCP_SNIPPET_TARGETS_SURVIVE_QUERY_BUDGET
    - MCP_SNIPPET_INSTANCE_LIMIT_IS_DISCOVERABLE
    - MCP_SNIPPET_RETRIEVAL_WORK_IS_BOUNDED
    - MCP_SNIPPET_RESPONSE_STAYS_COMPACT
  replaces:
    MCP_COMBINED_PAGE_READING_COMPATIBLE: MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE
    MCP_LEGACY_VERSION_REMAINS_COMPATIBLE: MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE
  cancels:
    - MCP_RESOURCE_VERSION_PAGE_READING_USES_RESOURCES
    - MCP_RESOURCE_CATALOG_IS_PAGINATED
    - MCP_RESOURCE_LIST_USES_STABLE_SNAPSHOTS
    - MCP_RESOURCE_NOTIFICATIONS_ARE_OMITTED
    - MCP_RESOURCE_LINKS_RESOLVE_TO_LISTED_RESOURCES
    - MCP_RESOURCES_EXCLUDE_SUPPORT_PAGES
    - MCP_TEMPLATES_EXCLUDE_LANGUAGE_AND_METHOD_SOURCES
decisions:
  - adr:MCP_DISABLE_RESOURCES
  - adr:MCP_ATOMIC_SITE_SNAPSHOTS
  - adr:MCP_RECOVERABLE_CONTAINER_RELEASE
  - adr:SNIPPET_SIGNALS_OUTSIDE_TEXT_QUERY
invariants:
  - invariant:MCP_TOOLS_ONLY_SURFACE_IS_STABLE
  - invariant:MCP_ACTIVE_SNAPSHOT_IS_COMPLETE
  - invariant:MCP_SITE_OVERRIDE_HAS_NO_PUBLIC_FALLBACK
  - invariant:MCP_RELEASE_HAS_RECOVERABLE_PREDECESSOR
  - invariant:MCP_SNIPPET_SIGNALS_SURVIVE_TEXT_BUDGET
contracts:
  - contract:MCP_API@4.0
  - contract:MCP_CORPUS_SNAPSHOT@1.1
  - contract:MCP_DISTRIBUTION@1.0
  - contract:MCP_RELEASE_RUNTIME@1.0
supersedes:
  - design:mcp-container-distribution
cancels: []
---

# MCP без Resources: один runtime, пять инструментов

## Согласованная граница

Пользователь запросил «Давай отключим все ресурсы» и подтвердил предложенный
scope словами «Отлично. Это то что надо»: полное удаление MCP Resources для
HTTP и Docker/stdio без переключателя, сохранение пяти tools, кеша, фонового
обновления и опубликованных файлов сайта. Этот документ оформляет утверждённый
scope для проверки письменного пакета; runtime ещё не изменён.

Нормативно сохраняется
[пакет контейнерной поставки](2026-09-10-mcp-container-distribution-design.md),
кроме обязательств предоставлять Resources и готовить их представление в RAM.
Независимые решения по источнику, атомарности, ограничениям, происхождению
артефактов, изоляции launchers и восстановлению не пересматриваются.
Согласованный отдельно запрет публикации Pages при неизвестной истории
индексов остаётся отдельной работой по CI, не исправлением Resources.

Нет нового endpoint, сервиса, транспорта, флага конфигурации или fallback.
Сайт, статический `/indexes/`, MCP data cache и закрытые журналы не удаляются.
Публичный мониторинг не возвращается. Этот пакет не разрешает push,
публикацию образа или ручные изменения production.

## Основание и semantic impact

Проверена чистая feature-ветка на `108b91f2a86ba038c1f61d928853f420f1430a35`,
основной checkout, main `b7bef11e145a188b30e7a7b17df2be4cb1acbd0c`.
`build_server()` регистрирует `llms.txt`, `llms-full.txt` и `pages.jsonl`.
`build_generation()` дополнительно строит полный rebased JSONL и два текста
для Resources и сохраняет их в `IndexGeneration.resources`.

Закреплённый MCP Python SDK 1.27.0 регистрирует resource handlers в
`FastMCP._setup_handlers()` независимо от количества `@server.resource`.
Наличие list handler автоматически добавляет capability. Удаление только
трёх декораторов не реализует согласованное отсутствие поддержки Resources.

Все семь вопросов impact check рассмотрены. Удаляются требования и публичные
URI/методы, меняются ADR и инварианты совместимости, затрагиваются `governs`
API и snapshot contracts. Старые тесты и API 2.4 прямо сохраняют три Resources;
их нельзя оставить свидетельством нового результата. Это архитектурное
breaking-изменение ресурсной границы при сохранении tool-интерфейса.

## Требования

### MCP_RESOURCES_ARE_DISABLED

В HTTP и stdio отсутствуют capability `resources`, Resource templates,
resource notifications и все resource handlers. Корректные JSON-RPC вызовы
`resources/list`, `resources/templates/list`, `resources/read`,
`resources/subscribe` и `resources/unsubscribe` получают `-32601 Method not
found`, без содержимого корпуса, чтения cache и запуска загрузчика.
Это относится к старым трём URI и любым другим URI; доступ по известному URI
не обходит отсутствие discovery. Вызовы проверяются после корректной
инициализации и с согласованной protocol version.

`initialize.result.capabilities.resources` отсутствует, а не равен `{}` или
`null`. В `/version` остаётся `api: v2`, но `api_profiles` содержит только
`legacy-tools`. Tool content не содержит embedded Resources или ResourceLink;
обычные HTTP-ссылки внутри прежних полей ответа сохраняются. Prompts и другие
незатронутые MCP-возможности не меняются под видом отключения Resources.

### MCP_LEGACY_TOOLS_REMAIN_COMPATIBLE

Сохраняются `v8std_search`, `v8std_get_page`, `v8std_get_related`,
`v8std_explain_snippet`, `v8std_explain_diagnostics`: имена, schemas, defaults,
лимиты, формы успешных ответов и прежние ошибки tools. Поиск и snippet ranking
не меняются. Полный текст отдельной страницы читается через ограниченный
`v8std_get_page`, не новый bulk tool. Каталог не зависит от имени агента,
User-Agent, CPU architecture, транспорта, SITE_URL или готовности индекса.

API 4.0 — номер внутреннего breaking-контракта, не новая MCP protocol version
и не URL `/v4/mcp`. Исторический design-only API 3.0 не возобновляется.
Совместимость обещана tool-клиентам, но не клиентам, которым необходим
`resources/read`. Для них документация указывает переход на существующие tools;
сервер не выполняет скрытую переадресацию resource request в tool call.

### MCP_RESOURCE_PRESENTATION_IS_NOT_BUILT

Runtime не строит и не удерживает дополнительные полнокорпусные текстовые
представления, служившие только MCP Resources. Из generation facade удаляются
`resources` и `read_resource_text`; из legacy index удаляется неиспользуемый
resource-fetch/cache путь после проверки всех его потребителей.

Канонические pages/vectors и данные поиска остаются в памяти. URL presentation
tools сохраняется, включая разбор ссылок и защиту кода от переписывания.
Проверка архива вправе временно читать его файлы в пределах прежних бюджетов;
запрет относится к лишней подготовке/хранению представлений после проверки,
а не к обязательной проверке целостности snapshot.

### MCP_RESOURCE_REMOVAL_PRESERVES_CORPUS_DELIVERY

Формат snapshot major 1, состав пяти файлов, hashes и persistent cache namespace
не меняются. `llms.txt`, `llms-full.txt` и `pages.jsonl` остаются web-артефактами
и членами проверяемого архива. Старый валидный cache работает с новым runtime:
не нужен принудительный повторный download из-за удаления MCP Resources.
Warm/offline, source isolation и атомарный background refresh сохраняются.

Отключение устраняет массовую отдачу через MCP Resources, но не превращает
публичный сайт в закрытый. Последовательные tool calls и прямые web downloads
остаются возможными. Ни экономия RAM/CPU, ни поддержка 100000 агентов не
объявляются измеренными до новых проверок.

## Реализация границы и ошибки

В одном месте построения сервера отключаются SDK resource handlers и удаляются
регистрации. Взаимодействие с low-level dispatch SDK изолируется адаптером,
защищённым wire-тестами на закреплённой версии; fork SDK и замена FastMCP целиком
не нужны. Stdio и HTTP используют тот же настроенный server, без nginx-only
фильтра. Capability выводится из реально доступных handlers, а не маскируется
поверх работающего read path.

Отказы Resources не зависят от ready/refresh/ошибки источника. Tools при cold
bootstrap по-прежнему сообщают `INDEX_NOT_READY`; warm tools не ждут сети.
HTTP остаётся stateless JSON POST, GET/SSE отклоняется; stdio stdout остаётся
чистым. Private usage logging и EOF/SIGTERM/drain не изменяются.

## Проверки и влияние на незавершённую поставку

До исправления фиксируются RED для отсутствия capability/handlers и лишней
resource presentation. Затем нужны wire HTTP/stdio проверки полного lifecycle,
пяти успешных tools, всех перечисленных отказов Resources, старых и неизвестных
URI, warm/offline старого cache, cold bootstrap, slow/corrupt refresh и shutdown.
Spy-проверка подтверждает отсутствие data-path вызовов при отказе Resources;
проверка построенного поколения — отсутствие полнокорпусных представлений.

Изменятся server/runtime/index, resource-specific tests, документация и
`check_mcp_container.py`/`check_mcp_load.py`. В нагрузочном профиле удалённые
успешные Resources заменяются реальными tool requests; discovery burst и
отрицательные resource probes учитываются отдельно от успешных data calls.
Доказательство смены содержимого при refresh переводится на контролируемую
страницу через `v8std_get_page`: меняются фактические данные ответа, а не только
corpus ID. Статическая загрузка архива, active/idle/reconnect и release switch
остаются частью смешанной проверки.

Предыдущие отчёты и immutable image digests не переписываются. Старый профиль
с Resources не доказывает производительность нового runtime; нужен новый
собранный артефакт и новый отчёт. Незавершённые resource-утверждения Task 6
заменяются проверками этого пакета в следующем implementation plan, не
отмечаются выполненными автоматически. Остальные задачи поставки не отменены.

## Альтернативы и возврат

Пустой каталог уменьшил бы поломку discovery, но сохранял бы заявленную
возможность и её обработчики. Env-флаг позволил бы быстрый возврат, но создал бы
два профиля API и возможность случайно восстановить массовую выдачу. Выбрано
согласованное полное отключение для всех launchers без такого флага.

Возврат runtime возможен штатным recoverable release, но старый образ снова
предоставит Resources. Это последствие должно быть явно показано оператору
до отдельно разрешённого deployment. Само изменение не разрешает автоматическое
повторное включение Resources или изменение production сейчас.

## Пакет и состояние

Связанные документы: [решение](../adr/2026-09-15-mcp-disable-resources.md),
[инвариант](../invariants/mcp-tools-only-surface-is-stable.md),
[API](../contracts/mcp-api-v4-r0.md),
[уточнение snapshot](../contracts/mcp-corpus-snapshot-v1-r1.md).
Structured-документы из main сохранены неизменными. После проверки пользователем
этого письменного пакета создаётся plan через writing-plans; наличие пакета не
означает готовую реализацию, merge или отключение на публичном сервере.
