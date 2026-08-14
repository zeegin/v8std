---
schema_version: 1
kind: process
id: architecture-artifacts
version: 1
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

# Архитектурные артефакты v8std, версия 1

Этот документ — единственный нормативный источник схемы внутренних
архитектурных артефактов v8std. Он определяет структуру документов, связи
между ними, вычисляемые состояния и правила заморозки. Сам процесс является
политикой разработки и не входит в продуктовую архитектуру v8std.

## Виды документов

| Kind | ID | Обязательные поля | Имя файла |
|---|---|---|---|
| `design` | lower-kebab-case | `scope`, `requirements`, `decisions`, `invariants`, `contracts`, `plans`, `supersedes`, `cancels` | `YYYY-MM-DD-<id>-design.md` |
| `adr` | смысловой `UPPER_SNAKE_CASE` | `scope: product`, `design`, `requirements`, `aliases`, `supersedes`, `cancels`, `invariants`, `contracts` | `YYYY-MM-DD-<id-as-kebab>.md` |
| `invariant` | смысловой `UPPER_SNAKE_CASE` | `scope: product`, `introduced_by`, `requirements`, `check` | `<id-as-kebab>.md` |
| `contract` | смысловой `UPPER_SNAKE_CASE` | `scope`, `version`, `revision`, `compatibility`, `design`, `producer`, `consumers`, `requirements`, `governs`, `conformance`, `supersedes`, `deprecates` | `<id-as-kebab>-vN-rN.md` |
| `plan` | lower-kebab-case | `design`, `implements` | `YYYY-MM-DD-<id>-plan.md` |
| `process` | lower-kebab-case | `version`, `schema` | `<id>-vN.md` |

У каждого документа также обязательны `schema_version`, `kind` и `id`.
Поле `status` запрещено: состояние всегда вычисляется из Git, связей и
завершённости plan.

## Типизированные ссылки

Допустимы ссылки следующих форм:

- `design:<id>`;
- `adr:<SEMANTIC_ID>`;
- `invariant:<SEMANTIC_ID>`;
- `contract:<SEMANTIC_ID>@<version>.<revision>`;
- `plan:<id>`;
- `process:<id>@<version>`.

Текущие ссылки на ADR используют только смысловой идентификатор. Числовые
aliases допустимы исключительно при миграции `ADR-0001`–`ADR-0004` и не
используются как актуальные типизированные ссылки.

## Требования

Design объявляет требования в отображении `requirements`:

- `introduces` — вводит смысловые коды требований;
- `uses` — использует требования, введённые другим design;
- `replaces` — заменяет требования с явным отображением старого кода в новый;
- `cancels` — отменяет требования без замены.

Один код требования имеет ровно один источник `introduces`. Ссылки из ADR,
инвариантов, контрактов и plan должны разрешаться в активное требование.
Process requirements не могут использоваться продуктовым ADR, продуктовым
инвариантом или продуктовым контрактом.

## Решения, инварианты и контракты

Каждый ADR атомарен: он фиксирует одно решение и явно описывает влияние на
связанные сущности через `introduces`, `preserves`, `replaces` и `cancels`.
Отмена или замена ADR не отменяет автоматически связанные инварианты и
контракты — их дальнейшая судьба должна быть объявлена явно.

Инвариант описывает проверяемое свойство работающего продукта. Правила Git,
оформления документов и процесса разработки инвариантами продукта не являются.

Контракт фиксирует наблюдаемую границу. `compatibility` принимает только
`backward-compatible` или `breaking`. Совместимое уточнение увеличивает
`revision`; несовместимое изменение увеличивает `version` и явно связывает
новый контракт с заменяемым или устаревающим контрактом.

## Plan и готовность к merge

Plan содержит хотя бы один Markdown checkbox. Он считается завершённым, когда
все его checkboxes отмечены. Незавершённый candidate plan допустим во время
реализации при обычной `validate`, но отклоняется gate
`validate --merge-ready`. В merge-ready состоянии каждый реализуемый design,
ADR, инвариант и контракт должен быть покрыт завершённым plan и объявленными
fitness-проверками.

## Даты, состояния и заморозка

Дата создания ADR существует только в имени файла. Она не хранится отдельным
полем и не меняется на дату merge, поэтому параллельные ветки не требуют
перенумерации или переименования ADR.

После попадания structured-документа в базовую ветку его содержимое и путь
заморожены. Последующее изменение оформляется новым артефактом через
`supersedes`, `replaces`, `cancels` или новую версию контракта/process.
Документ базовой ветки считается structured и подлежит заморозке, только если
его базовая ревизия содержит корректный front matter этой модели. Благодаря
этому существующие unstructured-документы можно однократно переписать во время
bootstrap без постоянного legacy-флага или обхода валидатора.

Состояния ADR, требований, инвариантов, контрактов, design и plan вычисляются
по типизированному графу, истории Git и checkbox-состоянию. Хранимое поле
`status` не используется.

## Безопасность деклараций

Поля `check` и `conformance` содержат только декларации проверок. Валидатор не
передаёт текст из Markdown в shell и не исполняет объявленные команды
динамически. Разрешённые проверки запускаются явно зафиксированными командами
CI или оператором.
