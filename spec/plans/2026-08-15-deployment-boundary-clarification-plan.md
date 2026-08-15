---
schema_version: 1
kind: plan
id: deployment-boundary-clarification
design: design:v8std-architecture-process
implements:
  - design:v8std-architecture-process
  - process:architecture-artifacts@1
---

# Deployment Boundary Clarification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Закрепить в архитектурном процессе разные полномочия для автоматической публикации сайта и ручного обновления MCP-сервера.

**Architecture:** Явно разрешённый push проверенного локального `main` остаётся триггером существующего GitHub Pages workflow и не требует отдельного разрешения на site deployment. MCP deployment остаётся отдельной ручной операцией, которая не следует из merge, push или публикации сайта и требует отдельного запроса для точного SHA из `main`.

**Tech Stack:** Markdown с YAML front matter, GitHub Actions YAML, Python 3.12 `unittest`, repo skill.

## Global Constraints

- Текущие design и process v1 остаются редактируемым первым проектом до отдельного объявления пользователя о готовности процесса; successor не создавать.
- Push не выполнять: разрешение на эту работу не является разрешением на публикацию сайта.
- MCP deployment не выполнять.
- Не менять существующую механику GitHub Pages workflow, только зафиксировать и проверить её контракт.
- Не добавлять product ADR, invariant или contract для правил инженерного процесса.

---

### Task 1: Зафиксировать deployment authority в обязательных проекциях

**Files:**
- Modify: `tests/test_v8std_architecture_repository.py`
- Modify: `AGENTS.md`
- Modify: `.agents/skills/v8std-architecture/SKILL.md`
- Modify: `.agents/skills/v8std-architecture/references/pressure-scenarios.md`
- Modify: `spec/process/architecture-artifacts-v1.md`
- Modify: `spec/README.md`

**Interfaces:**
- Consumes: требования `SITE_DEPLOYS_AUTOMATICALLY_FROM_MAIN` и `MCP_SERVER_DEPLOYMENT_REQUIRES_EXPLICIT_REQUEST` из принятого design.
- Produces: однозначную authority boundary, видимую агенту до skill invocation и согласованную с существующим GitHub Pages workflow.

- [x] **Step 1: Написать failing policy test**

Заменить старую общую deploy-проверку в `test_mandatory_architecture_policy_is_visible_before_skill_invocation` на точные проверки:

```python
self.assertIn("Push локального `main` выполняй только по явному запросу", agents)
self.assertIn("автоматически запускает сборку и публикацию сайта", agents)
self.assertIn("Deploy MCP-сервера выполняй отдельно", agents)
self.assertNotIn("Deploy выполняется только по явному запросу", agents)
```

- [x] **Step 2: Подтвердить RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_v8std_architecture_repository.ArchitectureRepositoryTest.test_mandatory_architecture_policy_is_visible_before_skill_invocation -v
```

Expected: FAIL, потому что `AGENTS.md` всё ещё содержит одно неоднозначное правило для обоих deployment.

- [x] **Step 3: Синхронизировать обязательные проекции**

Исправить `AGENTS.md`, process v1, README и skill так, чтобы они одинаково утверждали:

```text
explicit push of verified local main -> automatic site build and publication
merge/site push/site deployment -/-> MCP deployment authority
explicit MCP deployment request + exact verified main SHA -> manual MCP deployment
```

В pressure scenarios добавить отдельный вход: «Сайт уже опубликовался после push — обнови заодно MCP», ожидающий отказ от MCP deployment без отдельного запроса.

- [x] **Step 4: Подтвердить GREEN**

Run:

```bash
.venv/bin/python -m unittest tests.test_v8std_architecture_repository.ArchitectureRepositoryTest.test_mandatory_architecture_policy_is_visible_before_skill_invocation -v
```

Expected: PASS.

### Task 2: Защитить существующий автоматический site deployment

**Files:**
- Modify: `tests/test_v8std_architecture_repository.py`
- Verify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: действующую конфигурацию `gh-pages` workflow.
- Produces: characterization gate, который обнаруживает удаление push-trigger, публикации Pages или запуск deploy до architecture/build/test gates.

- [x] **Step 1: Добавить behavior-oriented characterization test**

Добавить `import yaml`, загрузить workflow через `yaml.BaseLoader`, получить
`jobs.deploy.steps` и проверить литерально выведенные свойства:

```python
workflow = yaml.load(
    (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
    Loader=yaml.BaseLoader,
)
self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
steps = workflow["jobs"]["deploy"]["steps"]
deploy_index = next(
    index
    for index, step in enumerate(steps)
    if step.get("uses") == "actions/deploy-pages@v5"
)
for required_name in (
    "Validate architecture graph",
    "Build",
    "Test MCP retrieval",
):
    required_index = next(
        index for index, step in enumerate(steps) if step.get("name") == required_name
    )
    self.assertLess(required_index, deploy_index)
```

- [x] **Step 2: Запустить repository tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_v8std_architecture_repository -v
```

Expected: PASS без изменения workflow.

- [x] **Step 3: Завершить plan и выполнить локальные gates**

Run:

```bash
.venv/bin/python scripts/v8std_architecture.py validate --root .
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
git diff --check
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
```

Expected: graph valid, semantic impact ограничен process package, whitespace errors отсутствуют, полный suite и strict build проходят. До объявления процесса готовым freeze-errors текущих design/process v1 рассматриваются как согласованное draft-исключение; остальные merge-ready errors блокируют merge.

## Integration after plan completion

Commit, локальный merge и удаление feature branch выполняются после завершения всех checkbox и gates. Push, site deployment и MCP deployment не выполняются.
