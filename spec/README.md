# Внутренние архитектурные документы

`spec/` — непубликуемый корпус требований, решений, контрактов и планов v8std.
Он не входит в сайт, навигацию и AI-артефакты из `docs/`.

Нормативный процесс: [`process:architecture-artifacts@1`](process/architecture-artifacts-v1.md).
Обязательный рабочий маршрут агента: [repo skill](../.agents/skills/v8std-architecture/SKILL.md).

## Как работать

1. Прочитать `AGENTS.md`, эту страницу и нормативную process specification.
2. Создать отдельную ветку до первой записи.
3. Изучить фактические файлы и вручную оценить намерение и предполагаемые пути
   по вопросам semantic impact check. Пустой Git diff на этом этапе ничего не
   доказывает.
4. Если влияние на требования, ADR, инварианты или контракты исключено,
   использовать тривиальный путь с теми же Git- и merge-gates.
5. Если влияние найдено или не исключено, остановить изменения, выполнить
   brainstorming и выбрать необходимые документы.
6. После письменного согласования design создать plan до начала реализации.
7. Если реализация опровергла design или impact check, вернуться к комплексному
   проектированию, а не ослаблять gate.
8. После появления diff и перед локальным merge запустить CLI `impact`, проверить
   все изменённые пути, повторить semantic impact check и выполнить все gates.

## Какой документ создавать

| Причина | Документ |
|---|---|
| Новое или изменённое обязательство | `design` с кодом требования |
| Выбор между архитектурными альтернативами | Один атомарный `ADR` |
| Проверяемое долговечное свойство продукта | `invariant` и fitness declaration |
| Наблюдаемая граница producer/consumer | Версионированный `contract` |
| Связанный пакет требований и решений | `design`, соединяющий граф |
| Согласованное нетривиальное изменение нужно реализовать | `plan` с явным `implements` |
| Меняется сам процесс репозитория | `process`, skill или `AGENTS.md`, но не product invariant |

Принятый design может не иметь plan и остаётся только `ACCEPTED`.
`IMPLEMENTED` появляется лишь после завершённого принятого plan, который явно
указывает артефакт в `implements`.
Plan заканчивается до integration gate: commit, merge, push и deploy не являются
его checkbox-задачами.

## Каталоги и примеры структуры

- [`spec/designs/`](designs/) — требования и связанные решения; [пример](designs/2026-08-14-mcp-v3-resource-contract-design.md);
- [`spec/adr/`](adr/) — атомарные решения; [пример](adr/2026-08-14-page-reading-via-resources.md);
- [`spec/invariants/`](invariants/) — свойства продукта; [пример](invariants/mcp-resource-version-page-reading-via-resources.md);
- [`spec/contracts/`](contracts/) — наблюдаемые границы; [пример](contracts/mcp-api-v3-r0.md);
- [`spec/plans/`](plans/) — планы реализации; [пример](plans/2026-08-14-architecture-process-usability-fix-plan.md);
- [`spec/process/`](process/) — версии архитектурного процесса.

Front matter хранит нормативные коды, ссылки и отношения. Markdown объясняет
контекст, причины и последствия и не должен создавать второй нормативный список.
Принятый structured-документ не редактируется: создаётся преемник, новая версия
или ревизия.

## Команды

```bash
# Кандидаты архитектурного влияния текущего diff
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main

# Пустой вывод impact не доказывает тривиальность: проверить все пути вручную

# Вычисленные состояния документов
.venv/bin/python scripts/v8std_architecture.py status --root . --main-ref main

# Обычная проверка во время работы
.venv/bin/python scripts/v8std_architecture.py validate --root .

# Обязательная проверка перед локальным merge
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready

# Полный test suite
.venv/bin/python -m unittest discover -s tests -v

# Strict build
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
```
