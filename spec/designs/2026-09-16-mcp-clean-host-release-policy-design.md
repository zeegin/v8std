---
schema_version: 1
kind: design
id: mcp-clean-host-release-policy
scope: process
requirements:
  introduces:
    - MCP_REBUILD_STOP_REQUIRES_NOTICE_ACK
    - MCP_DOCKER_CATALOG_IS_RELEASE_DELIVERABLE
  uses:
    - MCP_SERVER_DEPLOYS_AUTOMATICALLY_FROM_VERIFIED_MAIN
    - MCP_AUTODEPLOY_ACTIVATION_IS_CONTROLLED
    - ALL_CHANGES_USE_BRANCHES
    - MAIN_ACCEPTS_ONLY_VALIDATED_MERGES
    - TRIVIALITY_IS_ASSESSED_NOT_ASSUMED
    - ARCHITECTURE_IMPACT_IS_RECHECKED
    - REQUIREMENTS_ARE_TRACEABLE
    - ARCHITECTURE_DECISIONS_ARE_ATOMIC
    - ADR_IDENTITIES_ARE_SEMANTIC
    - ARCHITECTURE_INVARIANTS_ARE_SEMANTIC
    - OBSERVABLE_BOUNDARIES_ARE_CONTRACTED
    - ARCHITECTURE_DOCUMENTS_ARE_IMMUTABLE
    - PROJECT_ERRORS_TRIGGER_COMPREHENSIVE_REVIEW
    - DESIGN_APPROVAL_PRECEDES_IMPLEMENTATION
    - ARCHITECTURE_PROCESS_IS_MACHINE_VALIDATED
    - INTERNAL_SPECIFICATIONS_STAY_UNPUBLISHED
    - SITE_DEPLOYS_AUTOMATICALLY_FROM_MAIN
    - EXISTING_SPECIFICATIONS_USE_ONE_MODEL
    - SUPERPOWERS_DRIVES_DESIGN_AND_PLANNING
    - PRODUCT_ARCHITECTURE_EXCLUDES_DEVELOPMENT_PROCESS
  replaces: {}
  cancels: []
decisions: []
invariants: []
contracts: []
supersedes: [design:mcp-ci-deployment-policy]
cancels: []
---

# Политика чистой переустановки и завершения поставки в Docker Catalog

## Граница процесса

Последовательность поставки: подготовка clean installation и артефактов,
подготовка Catalog entry, отдельное разрешение на остановку, установка,
приёмка/CI, затем подача и доведение Catalog PR. Режим чистой установки не
требует полного восстановления старой VM или предварительной эксплуатационной
репетиции. Частные договорённости и параметры конкретного запуска не входят
в публичную спецификацию.

Требования controlled activation и verified-main delivery сохраняются.
Меняется операционный prerequisite для выбранного clean-host режима: legacy
backup/restore и окно с возвратом из предыдущего policy design не обязательны.
Вместо них нужны подготовленные артефакты вне стираемой машины и отдельное
подтверждение перед остановкой. Это не waiver проверки кода, происхождения,
готовности нового сервиса или rollback последующих обновлений.

Все прежние Git/architecture/CI правила наследуются. Нормативный преемник —
[process v3](../process/architecture-artifacts-v3.md); машинная schema неизменна.
До согласованной реализации repo pointers и tools остаются на process v2;
сама запись v3 не активирует автоматизацию и не даёт полномочий стереть host.

## Требования

### MCP_REBUILD_STOP_REQUIRES_NOTICE_ACK

Согласование подготовки разрешает разработку и подготовку поставки, но не
позволяет агенту остановить nginx/MCP, переустановить ОС, удалить старую VM
или переключить публичный runtime до отдельного подтверждения ответственного
оператора после уведомления потребителей. Прошлое окно обслуживания не считается
актуальным разрешением; по готовности запрашивается продолжение. Канал уведомления
и время остановки относятся к закрытой операторской записи, а не к архитектуре.

Перед паузой в закрытой операторской записи фиксируются exact target, проверенный
main SHA, image/platform/configuration digests и corpus ID; оператор видит, что остановятся MCP
и static index downloads. После подтверждения действия ограничены этой машиной
и этой поставкой. Другой SHA, другой host или новая схема установки требуют
повторной оценки, а не молчаливого расширения подтверждения.

До паузы можно подготовить публикацию и Catalog entry. Структурные документы,
код, GitHub-настройки и публикация остаются раздельными фактами. Push разрешён
только явно; согласие с общим планом не изображается выполненным push или
переданным доступом. Секреты передаются закрытым каналом, не в тексте чата.

Проверка: runbook имеет отдельный остановочный gate; CI/restricted commands
не содержат wipe/reinstall/initial-install; fake acceptance, обход SSH/TLS pin
и использование личного GitHub token для service identity запрещены.

### MCP_DOCKER_CATALOG_IS_RELEASE_DELIVERABLE

Результат состоит из четырёх независимо подтверждённых частей: доступный
опубликованный образ, работающий public MCP, принятые автоматические обновления
и запись в официальном Docker MCP Catalog. Выполненные первые части не позволяют
назвать последнюю завершённой.

Используется self-provided pre-built image: та же multi-platform сборка версии,
что для production, с точными digest/source SHA. Каталожная запись предназначена
для локального контейнера stdio и persistent cache, не только для подключения
к нашему HTTP endpoint. Собственный образ не называется Docker-built или
Docker Official Image. Gateway профиль отличается от direct Docker/Compose
в пределах действующего distribution contract, без выдуманных полей schema.

До отправки проверяется реальный Toolkit: discovery, five tools, cold/warm,
повторные вызовы и сессии, persistent cache и SITE_URL. Per-entry longLived
проверяется фактическим поведением, не глобальным флагом Gateway. Неудача такого
теста блокирует отправку неработающей записи, но не автоматически работающий
production и доступный образ. При новом противоречии нужен design review,
а не обещание, что проблема уже исправлена.

После production acceptance создаётся PR в docker/mcp-registry, проходят его
проверки и замечания. Срок/решение review принадлежат Docker; PR submission
не является опубликованной записью. После merge отдельно проверяются появление
в каталоге и установка оттуда. Обновления production не ждут каждой следующей
версии каталога: разные версии допустимы, разные сборки одной версии — нет.

PR #33 закрывается с благодарностью после доказательства локального и production
пути, не по одному созданному Dockerfile. Полная cold-offline установка без
сайта/cache не обещается; issue #32 автоматически не закрывается. Внешние
комментарии описывают результат, не внутренние неудачи/секреты эксплуатации.

## Реализация процесса

В implementation plan входят согласованные изменения указателя process schema,
AGENTS.md, spec/README.md, repo skill и policy tests. Путь первичного оператора
отделяется от CI deploy; публикация образа/corpus и runtime activation остаются
разными переключателями. Автоматизацию включают после actual first acceptance
и прежних проверок rollback/capacity, а не по факту установки Docker.

Запрет предварительной эксплуатационной репетиции не отменяет обязательные
локальные merge gates: semantic impact, architecture validation, fitness,
strict build и полный test suite. Merge, разрешённый push, live acceptance и
Catalog submission записываются в operations, не в checkbox completion кода.

## Проверенный внешний порядок

Docker допускает собственный образ и требует review PR команды Docker:
[CONTRIBUTING](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md),
[README](https://github.com/docker/mcp-registry#-option-b-self-provided-pre-built-image).
Проверено 2026-09-16. Перед фактической отправкой условия и schema перечитываются.

Нынешняя `deploy/docker-catalog/server.yaml` — неподанная заготовка с
release-pending и RELEASE_SOURCE_SHA. Они заменяются только реальными сведениями
публикации. Этот письменный пакет не выдаёт её за готовую внешнюю запись.
