---
schema_version: 1
kind: plan
id: architecture-process-usability-fix
design: design:v8std-architecture-process
implements:
  - design:v8std-architecture-process
  - process:architecture-artifacts@1
---

# Architecture Process Usability Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Устранить найденные противоречия и неудобства первой, ещё не введённой в работу версии архитектурного процесса без создания process v2 и без нового языка схемы.

**Architecture:** Существующая process v1 остаётся нормативным документом и получает точные правила входа, авторинга и вычисления `IMPLEMENTED`. `spec/README.md`, `AGENTS.md` и repo skill становятся согласованными проекциями этого процесса; Python-валидатор и формат документов не меняются.

**Tech Stack:** Markdown с YAML front matter, существующий Python CLI и `unittest`-набор репозитория.

## Global Constraints

- Выполнять работу в ветке `codex/fix-architecture-process-usability`.
- Считать изменение `architecture-artifacts-v1.md` явным одноразовым bootstrap-исключением по указанию пользователя; постоянный обход Git-заморозки не добавлять.
- Не создавать process v2, JSON Schema, собственный schema DSL, генераторы или новые CLI-команды.
- Не менять branch-first workflow, типизированные ссылки, вычисляемые состояния и product/process boundary.
- Структурные коды и ссылки принадлежат front matter; Markdown объясняет смысл и не создаёт второй нормативный список.
- Push и deploy не выполнять.

---

### Task 1: Зафиксировать исходные противоречия

**Files:**
- Inspect: `AGENTS.md`
- Inspect: `.agents/skills/v8std-architecture/SKILL.md`
- Inspect: `spec/process/architecture-artifacts-v1.md`
- Inspect: `spec/README.md`

**Interfaces:**
- Consumes: согласованный минимальный дизайн исправления.
- Produces: проверяемый список расхождений, которые должны исчезнуть.

- [x] **Step 1: Подтвердить расхождение порядка работы**

Run:

```bash
rg -n "Перед изменением|For a nontrivial change" AGENTS.md .agents/skills/v8std-architecture/SKILL.md
```

Expected: `AGENTS.md` требует brainstorming перед любым изменением, а skill — только для нетривиального.

- [x] **Step 2: Подтвердить неполную точку входа**

Run:

```bash
rg -n "impact|status|Тривиал|Как работать|Какой документ" spec/README.md
```

Expected: команда `rg` не находит описания рабочего сценария, выбора документов и CLI-команд `impact`/`status`.

- [x] **Step 3: Подтвердить расхождение merge-ready формулировки**

Run:

```bash
sed -n '89,97p' spec/process/architecture-artifacts-v1.md
sed -n '678,702p' scripts/v8std_architecture_validation.py
```

Expected: спецификация требует plan для каждого «реализуемого» артефакта, а validator допускает принятый design без plan и использует завершённый plan для вычисления реализации.

### Task 2: Согласовать нормативный процесс и его точки входа

**Files:**
- Modify: `spec/process/architecture-artifacts-v1.md`
- Modify: `spec/README.md`
- Modify: `AGENTS.md`
- Modify: `.agents/skills/v8std-architecture/SKILL.md`

**Interfaces:**
- Consumes: текущую process schema и существующие команды `impact`, `status`, `validate`.
- Produces: один последовательный impact-first workflow и однозначные правила `ACCEPTED`/`IMPLEMENTED`.

- [x] **Step 1: Исправить process v1**

Уточнить, что process specification нормативна, а Python является её исполняемой реализацией. Зафиксировать ownership front matter, допустимость `ACCEPTED` без plan и точный критерий `IMPLEMENTED` через завершённый принятый plan.

- [x] **Step 2: Сделать `spec/README.md` точкой входа**

Добавить последовательность работы, таблицу причин создания документов, команды `impact`/`status`/`validate` и ссылки на существующие примеры.

- [x] **Step 3: Устранить противоречие AGENTS/skill**

В обоих местах закрепить: сначала repo skill и impact check; brainstorming обязателен после обнаружения нетривиального или неразрешённого архитектурного влияния.

- [x] **Step 4: Проверить согласованность вручную**

Перечитать четыре изменённых файла как единый пользовательский маршрут и исключить повторные нормативные списки.

### Task 3: Подготовить ветку к integration gate

**Files:**
- Modify: `spec/plans/2026-08-14-architecture-process-usability-fix-plan.md`

**Interfaces:**
- Consumes: согласованный корпус process-документации.
- Produces: завершённый plan и готовую к integration gate ветку.

- [x] **Step 1: Запустить целевые проверки**

Run:

```bash
.venv/bin/python -m unittest tests.test_v8std_architecture_process tests.test_v8std_architecture_repository -v
```

Expected: все тесты проходят.

- [x] **Step 2: Запустить полный test suite и strict build**

Run:

```bash
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
```

Expected: полный test suite не содержит failures/errors, strict build завершается с exit code 0.

- [x] **Step 3: Проверить итоговый diff и завершить plan**

Run:

```bash
git diff --check
git status --short
```

Expected: diff не содержит whitespace errors; изменены только файлы текущей задачи. После проверки отметить этот checkbox и завершить plan.

## Integration after plan completion

После завершения всех checkbox выполнить вне plan:

```bash
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready
```

Для этого bootstrap-исправления ожидаемы только две ошибки заморозки изменяемой
process v1, явно разрешённые пользователем. Затем закоммитить файлы задачи,
локально слить ветку в `main` и повторить проверки на merged tree. Push и deploy
не выполнять.
