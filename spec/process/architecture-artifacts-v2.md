---
schema_version: 1
kind: process
id: architecture-artifacts
version: 2
supersedes:
  - process:architecture-artifacts@1
schema:
  semantic_id_pattern: '^[A-Z][A-Z_]*$'
  document_id_pattern: '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'
  typed_reference_pattern: '^(design|adr|invariant|contract|plan|process):'
  contract_reference_pattern: '^contract:[A-Z][A-Z_]*@\d+\.\d+$'
  adr_filename_pattern: '^\d{4}-\d{2}-\d{2}-[a-z]+(?:-[a-z]+)*\.md$'
  directories:
    design: spec/designs
    adr: spec/adr
    invariant: spec/invariants
    contract: spec/contracts
    plan: spec/plans
    process: spec/process
  frozen_kinds: [design, adr, invariant, contract, plan, process]
  forbidden_fields: [status]
---

# Архитектурные артефакты v8std, версия 2

## Область изменения

Версия 2 является нормативным преемником версии 1 с неизменной машинной схемой.
Она принимается вместе с `design:mcp-ci-deployment-policy`. Из
[неизменяемой версии 1](architecture-artifacts-v1.md) нормативно сохраняются
разделы «Виды документов», «Структурные данные и поясняющий текст»,
«Типизированные ссылки», «Требования», «Решения, инварианты и контракты»,
«Даты, состояния и заморозка», «Безопасность деклараций».
Правила остальных разделов заменены ниже, а не применяются одновременно.

## Последовательность работы

1. До первой записи создать отдельную ветку в основном checkout. PR/worktree
   применять только по явному запросу пользователя.
2. Выполнить ручной semantic impact check по намерению и предполагаемым путям.
   Пустой diff или отсутствие совпадений `governs` не доказывают тривиальность.
3. Если влияние найдено или не исключено — использовать brainstorming,
   письменно согласовать design-пакет и создать implementation plan.
4. При опровержении design остановить реализацию и пересмотреть граф целиком.
5. Перед локальным merge повторить ручной impact по фактическому diff, CLI
   `impact`, `validate --merge-ready`, fitness, полный suite и strict build.
   Прямые коммиты в main и push feature напрямую в remote main запрещены.
6. Push локального main выполнять только по явному запросу. Разрешённый push
   запускает проверку/публикацию сайта, corpus и runtime по затронутым входам.
7. После первичной активации MCP автоматически обновляется из CI только
   проверенным SHA main и опубликованным digest, с собственной post-deploy
   проверкой и rollback. До активации обновление требует отдельного запроса.

## Plan и готовность к merge

Plan содержит хотя бы один Markdown checkbox. Для merge-ready все checkboxes
candidate plans должны быть завершены. Незавершённый plan допустим при обычной
validate. Design/ADR/invariant/contract без plan могут быть ACCEPTED; только
завершённый принятый plan с явным `implements` добавляет IMPLEMENTED.

Checkboxes описывают реализацию и доказательства, доступные до merge. Merge,
разрешённый push, внешняя публикация, первичная активация и последующие
автоматические production deployments — отдельные результаты интеграции,
а не условие завершённости такого plan. Факт включения автоматизации и факт
успешного rollout записываются раздельно.

Fitness evidence обязательно в момент `required_when: accepted|implemented`.
Декларация будущего теста не является выполненным тестом. Наличие design без
plan допустимо; запись design не означает готовый продукт.

## Границы публикации и MCP deployment

Первичная активация требует согласованного операционного этапа: safety inventory
и backup host, защита main и production environment, изолированные credentials,
проверенный recovery и явное включение. Она не выводится из merge design-файлов.
Указатель schema loader, repo instructions, skill, tests и CI обновляются
согласованно в реализации; до этого действующие инструменты остаются на v1.

После активации разрешённый push проверенного main означает разрешение
автоматической доставки соответствующих артефактов этим настроенным CI.
Отдельное разрешение на каждый обычный MCP rollout не требуется. CI не даёт
агенту полномочий вручную менять production вне этого пути, удалять чужие
приложения или выдавать новые доступы.

Контентная поставка сначала размещает immutable snapshot, затем публикует
ссылающийся на него Pages manifest. Runtime поставляется из опубликованного
image digest. Некорректный или устаревший release не активируется; неуспешный
smoke возвращает предыдущую работоспособную комбинацию image/config/data.

Отключение автоматизации прекращает новые production jobs, но не останавливает
работающий MCP. Аварийное ручное вмешательство требует отдельного запроса,
фиксации SHA/digest и последующего возвращения host к управляемому состоянию.
