---
schema_version: 1
kind: plan
id: architecture-process-review-fixes
design: design:v8std-architecture-process
implements:
  - design:v8std-architecture-process
  - process:architecture-artifacts@1
---

# Architecture Process Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Устранить оставшиеся противоречия архитектурного процесса до начала его эксплуатации.

**Architecture:** Plan становится единственным владельцем связи с реализуемым design; замороженный design больше не хранит протухающий обратный список `plans`. Предварительная архитектурная оценка выполняется вручную по намерению, а CLI `impact` используется только для фактического diff и не доказывает тривиальность пустым выводом.

**Tech Stack:** Python 3.12, `unittest`, Markdown с YAML front matter, существующий architecture CLI.

## Global Constraints

- Выполнять работу в ветке `codex/fix-architecture-process-review`.
- Считать изменения текущих process/design v1 частью явно разрешённой bootstrap-доработки ещё не введённого процесса; постоянный обход заморозки не добавлять.
- Не создавать process v2, JSON Schema, собственный schema DSL или новые CLI-команды.
- Plan владеет ссылками `design` и `implements`; design не хранит обратный список plan.
- Пустой вывод CLI `impact` не является доказательством отсутствия архитектурного влияния.
- Push и deploy не выполнять.

---

### Task 1: Удалить протухающую связь `design.plans`

**Files:**
- Modify: `tests/test_v8std_architecture_validation.py`
- Modify: `tests/test_v8std_architecture_model.py`
- Modify: `tests/test_v8std_architecture_cli.py`
- Modify: `scripts/v8std_architecture_validation.py`
- Modify: `spec/designs/*-design.md`
- Modify: `spec/process/architecture-artifacts-v1.md`

**Interfaces:**
- Consumes: `plan.design` и `plan.implements` как направленные ссылки plan → design/targets.
- Produces: design, который остаётся корректным до и после создания будущих plan без редактирования замороженного документа.

- [x] **Step 1: Написать failing behavior test**

Изменить helper `design()` так, чтобы он не создавал поле `plans`, и добавить:

```python
def test_plan_owns_design_association_without_reverse_plan_field(self) -> None:
    feature = design("feature")
    implementation = document(
        "plan",
        "feature-implementation",
        design="design:feature",
        implements=["design:feature"],
        checkbox_count=1,
        checked_count=1,
    )

    issue_codes = codes(validate_graph(build_graph([feature, implementation])))

    self.assertNotIn("MISSING_REQUIRED_FIELD", issue_codes)
```

- [x] **Step 2: Подтвердить RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_v8std_architecture_validation.ArchitectureValidationTest.test_plan_owns_design_association_without_reverse_plan_field -v
```

Expected: FAIL, потому что validator всё ещё требует `design.plans`.

- [x] **Step 3: Реализовать единственное направление связи**

Удалить `plans` из `REQUIRED_FIELDS["design"]` и `REFERENCE_FIELDS["design"]`, из design front matter корпуса и тестовых fixtures. В process v1 удалить `plans` из обязательных полей design и явно указать, что обратные plan-ссылки вычисляются по `plan.design`/`plan.implements`.

- [x] **Step 4: Подтвердить GREEN**

Run:

```bash
.venv/bin/python -m unittest tests.test_v8std_architecture_validation.ArchitectureValidationTest.test_plan_owns_design_association_without_reverse_plan_field -v
.venv/bin/python -m unittest tests.test_v8std_architecture_model tests.test_v8std_architecture_cli tests.test_v8std_architecture_repository -v
```

Expected: все тесты проходят.

### Task 2: Разделить semantic impact и CLI diff impact

**Files:**
- Modify: `AGENTS.md`
- Modify: `spec/README.md`
- Modify: `spec/process/architecture-artifacts-v1.md`
- Modify: `.agents/skills/v8std-architecture/SKILL.md`
- Modify: `.agents/skills/v8std-architecture/references/impact-check.md`
- Modify: `.agents/skills/v8std-architecture/references/pressure-scenarios.md`

**Interfaces:**
- Consumes: намерение и предполагаемые пути до mutation; фактический Git diff после mutation.
- Produces: две разные проверки без ложного вывода «пустой CLI output = trivial».

- [x] **Step 1: Исправить нормативную последовательность**

До mutation требовать ручной semantic impact check по семи вопросам. CLI `impact` запускать после появления diff и перед merge; явно написать, что он показывает только governed paths фактического diff и его пустой вывод ничего не доказывает.

- [x] **Step 2: Исправить точку входа**

В `spec/README.md` заменить plan-пример на `2026-08-14-architecture-process-usability-fix-plan.md` и добавить точные команды полного test suite и strict build.

- [x] **Step 3: Проверить согласованность проекций**

Перечитать process, README, AGENTS, skill и impact reference как один маршрут. Проверить, что до mutation нигде не требуется анализ ещё не существующего Git diff.

### Task 3: Проверить готовность ветки

**Files:**
- Modify: `spec/plans/2026-08-15-architecture-process-review-fixes-plan.md`

**Interfaces:**
- Consumes: исправленную schema, validator и процессуальную документацию.
- Produces: завершённый plan и ветку, готовую к отдельному integration gate.

- [x] **Step 1: Запустить architecture validation и целевые тесты**

```bash
.venv/bin/python scripts/v8std_architecture.py validate --root .
.venv/bin/python -m unittest tests.test_v8std_architecture_process tests.test_v8std_architecture_repository -v
```

- [x] **Step 2: Запустить полный suite и strict build**

```bash
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
```

- [x] **Step 3: Проверить diff и завершить plan**

```bash
git diff --check
git status --short
```

Expected: изменены только файлы задачи, whitespace errors отсутствуют, все checkbox plan завершены.

## Integration after plan completion

После завершения plan повторить semantic impact по фактическому diff, запустить CLI `impact` и `validate --merge-ready`. В bootstrap-ветке допустимы только заранее разрешённые freeze errors для исправляемых process/design v1; остальные ошибки блокируют merge. Затем закоммитить, локально слить в `main` и повторить gates на merge-коммите. Push и deploy не выполнять.
