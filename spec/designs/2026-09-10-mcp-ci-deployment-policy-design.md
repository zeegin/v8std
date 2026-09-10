---
schema_version: 1
kind: design
id: mcp-ci-deployment-policy
scope: process
requirements:
  introduces:
    - MCP_SERVER_DEPLOYS_AUTOMATICALLY_FROM_VERIFIED_MAIN
    - MCP_AUTODEPLOY_ACTIVATION_IS_CONTROLLED
  uses:
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
  replaces:
    MCP_SERVER_DEPLOYMENT_REQUIRES_EXPLICIT_REQUEST: MCP_SERVER_DEPLOYS_AUTOMATICALLY_FROM_VERIFIED_MAIN
  cancels: []
decisions: []
invariants: []
contracts: []
supersedes:
  - design:v8std-architecture-process
cancels: []
---

# Политика автоматической поставки MCP из CI

## Согласованное изменение

Пользователь прямо выбрал автоматическое обновление ai.v8std.ru из GitHub CI
и использование того же опубликованного образа, что для локальной поставки.
Это меняет прежнее правило отдельного ручного deploy на каждый выпуск.
Нельзя одновременно сохранить запрет автодеплоя и обещать автоматическую
поставку после push. Новый process v2 фиксирует явного преемника, не редактируя
замороженные design/process v1.

Продуктовая топология и rollback описаны в
[продуктовом design](2026-09-10-mcp-container-distribution-design.md).
Git rules, разрешения CI и approval gates не становятся продуктовыми ADR.

## Требования

### MCP_SERVER_DEPLOYS_AUTOMATICALLY_FROM_VERIFIED_MAIN

После управляемой активации разрешённый push проверенного `main` запускает
публикацию и при необходимости автоматический rollout MCP без отдельной
ручной команды на каждый SHA. CI использует только прошедший gates SHA из
защищённого `main` и точный опубликованный digest. PR, fork, tag, имя ветки
из входного параметра и mutable `latest` не являются полномочием deploy.
Контентные изменения обновляют corpus без рестарта runtime.

Проверка: интеграционная матрица main/PR/fork/tag/устаревший run; негативные
случаи не получают production credentials и не меняют host. Успешный release
проверяется на том же digest, который поступил в registry.

### MCP_AUTODEPLOY_ACTIVATION_IS_CONTROLLED

Согласование design не устанавливает Docker, не удаляет старый сайт и не
выдаёт secrets. Первичное включение требует отдельного операционного этапа:
проверить host, backup/restore, точные targets, restricted deploy identity,
protected main и production environment, затем подтвердить первый rollout
и возможность отключить автоматизацию. До выполнения этапа действует прежняя
операционная граница: не деплоить без явного запроса.

Проверка: до activation marker/секретов workflow может собрать и проверить
артефакты, но не может менять production; после активации failed gates, stale
release и не-main источники блокируются. Kill switch запрещает новые releases,
не уничтожает работающий endpoint и не прерывает host rollback.

## Нормативный преемник и активация

[Process v2](../process/architecture-artifacts-v2.md) сохраняет схему графа,
заморозку документов, отдельную ветку, основной checkout, согласование design,
plan, semantic impact, tests и strict build. Push локального main по-прежнему
требует явного запроса; PR и worktree — только по явному запросу. Здесь такой
отдельный PR для поставки был запрошен, но его создание не входит в запись
этого пакета.

Текущий CLI загружает schema из `architecture-artifacts-v1.md`. Новая версия
имеет ту же schema; только документация v2 не переключает CLI или поведение CI.
В implementation plan должны войти согласованные изменения указателя loader,
`AGENTS.md`, `spec/README.md`, repo skill, policy tests и workflows. Их единый
diff обязан исключить одновременно действующие противоречивые инструкции.
Старые structured files, включая завершённый deployment-boundary plan, остаются
историческими свидетельствами, не редактируются.

## Порядок CI и доказательства

PR gates выполняются без production secrets. Сборка из main использует
закреплённые actions и минимальные permissions; доступ к registry/deploy
выдаётся только соответствующему job. GitHub-hosted runner не исполняет
непроверенный PR на production host. Production environment ограничивает main;
защита main требует успешных обязательных checks и контролируемых bypass.

Image публикуется до deploy и проверяется по digest. Состояние host хранит SHA,
digest, config hash, corpus ID, монотонный release sequence и результат smoke.
Один deploy за раз; устаревший job не отменяет более новый. Отмена CI не
обрывает ограниченную host-транзакцию переключения/rollback.

Merge-ready plan содержит только реализуемые до merge задачи и проверяемые
на стенде доказательства. Последующие merge, разрешённый push, первичная
активация и реальные внешние deployments отмечаются операционными результатами
отдельно. Нельзя отметить host migration или принятие Docker Catalog как
сделанные по зелёным unit tests.
