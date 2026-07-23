# Autoformat Fixes Family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить подтверждённое по актуальной EPF семейство исправлений `autoformat`, отдельные карточки правил, связи с пунктами стандартов и руководство по всем режимам запуска.

**Architecture:** Данные исправлений и их связи хранятся в отдельном реестре, а существующий генератор строит карточки, семейный индекс, общий реестр и обратные ссылки. Семейство исправлений имеет отдельную семантику и счётчики, но использует общую модель стандартов и пунктов.

**Tech Stack:** Python 3.12, JSON, Markdown, Zensical, unittest, JavaScript/CSS существующего реестра.

## Global Constraints

- Семейство называется «Автоформатирование кода и локализация», технический ключ — `autoformat`.
- Идентификатор карточки образуется как `autoformat:` плюс номер стандарта,
  например `autoformat:std765`.
- Исправления нельзя прибавлять к счётчику диагностик.
- Связь с пунктом стандарта добавляется только по проверяемому первичному источнику.
- Параметры запуска и `Config.xml` документируются только после проверки встроенной справки или фактического поведения.
- Работа выполняется в основном checkout без worktree.

---

### Task 1: Извлечь и зафиксировать первичные данные обработки

**Files:**
- Create: `data/autoformat-fixes.json`
- Create: `docs/diagnostics/autoformat/research.md`
- Test: `tests/test_autoformat_fixes.py`

**Interfaces:**
- Consumes: EPF из каталога пользователя и архив ИТС.
- Produces: `load_autoformat_catalog(path: Path) -> AutoformatCatalog` с правилами, режимами и доказательствами.

- [ ] **Step 1: Выгрузить актуальную EPF во временный XML source-set**

Использовать `unica.runtime.execute` с отдельной временной файловой базой и
external source-set. Не добавлять выгрузку EPF в Git. Сохранить контрольную
сумму исходного файла:

```bash
shasum -a 256 '/Users/ingvarvilkman/Downloads/АвтоформатированиеКодаИЛокализация/АвтоформатированиеКодаИЛокализация.epf'
```

Ожидается одна SHA-256 и отсутствие изменений в checkout.

- [ ] **Step 2: Извлечь встроенную справку, объектный модуль и формы**

Найти в XML-выгрузке:

```bash
rg -n "АвтоформатироватьКод|Config.xml|Хранилищ|Файлов|Сервер|XML|EDT|437|441|453|455|456|458|467|474|478|644|680|702|765|767" "$AUTOFORMAT_DUMP"
```

Составить в `docs/diagnostics/autoformat/research.md` таблицу:

```markdown
| Правило | Преобразование | Объекты | Режимы | Первичное доказательство |
|---|---|---|---|---|
| std765 | Расстановка локализуемых заголовков | Формы | XML/ИБ/хранилище | Файл и процедура или раздел справки |
```

В итоговой таблице не должно быть строк без первичного доказательства.

- [ ] **Step 3: Написать тест схемы каталога**

```python
def test_autoformat_catalog_has_unique_standard_ids():
    catalog = load_autoformat_catalog(REPO_ROOT / "data/autoformat-fixes.json")
    ids = [fix.id for fix in catalog.fixes]
    assert ids
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"std\d+", item) for item in ids)


def test_every_fix_has_immutable_evidence_and_existing_standard():
    catalog = load_autoformat_catalog(REPO_ROOT / "data/autoformat-fixes.json")
    for fix in catalog.fixes:
        assert fix.evidence
        assert (REPO_ROOT / "docs/std" / f"{fix.id[3:]}.md").is_file()
```

- [ ] **Step 4: Запустить тест и убедиться, что загрузчика ещё нет**

Run:

```bash
.venv/bin/python -m unittest tests.test_autoformat_fixes -v
```

Expected: FAIL из-за отсутствия `load_autoformat_catalog`.

- [ ] **Step 5: Реализовать типизированную загрузку каталога**

В `scripts/diagnostic_standard_links.py` добавить:

```python
@dataclass(frozen=True)
class AutoformatFix:
    id: str
    title: str
    standard: str
    clause: str
    anchor: str
    effect: str
    scope: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class AutoformatCatalog:
    version: int
    tool_url: str
    fixes: tuple[AutoformatFix, ...]


def load_autoformat_catalog(path: Path) -> AutoformatCatalog:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if set(payload) != {"version", "tool_url", "fixes"}:
        raise ValueError("autoformat catalog has unexpected fields")
    if payload["version"] != 1:
        raise ValueError("unsupported autoformat catalog version")
    fixes = tuple(AutoformatFix.from_dict(item) for item in payload["fixes"])
    if len({item.id for item in fixes}) != len(fixes):
        raise ValueError("duplicate autoformat fix id")
    return AutoformatCatalog(
        version=payload["version"],
        tool_url=payload["tool_url"],
        fixes=fixes,
    )
```

`AutoformatFix.from_dict` реализовать с fail-closed валидацией по образцу
`LinkReview.from_dict`; неизвестные поля должны приводить к `ValueError`.

- [ ] **Step 6: Заполнить реестр только подтверждёнными правилами**

Форма `data/autoformat-fixes.json`:

```json
{
  "version": 1,
  "tool_url": "https://its.1c.ru/db/v8std#content:456:hdoc",
  "fixes": [
    {
      "id": "std765",
      "title": "Локализация заголовков элементов форм",
      "standard": "std765",
      "clause": "2",
      "anchor": "2",
      "effect": "Задаёт локализуемые заголовки таблиц и групп формы",
      "scope": ["Форма"],
      "evidence": ["local:docs/diagnostics/autoformat/research.md#правило-std765"]
    }
  ]
}
```

Проверить кандидатов `std437`, `std441`, `std453`, `std455`, `std456`,
`std458`, `std467`, `std474`, `std478`, `std644`, `std680`, `std702`,
`std765`, `std767`; строки, которые нельзя подтвердить, не включать.

- [ ] **Step 7: Запустить тесты и закоммитить исследовательский слой**

```bash
.venv/bin/python -m unittest tests.test_autoformat_fixes -v
git add data/autoformat-fixes.json docs/diagnostics/autoformat/research.md scripts/diagnostic_standard_links.py tests/test_autoformat_fixes.py
git commit -m "feat: add verified autoformat fixes catalog"
```

Expected: все тесты `test_autoformat_fixes` проходят.

### Task 2: Расширить генератор до семейства исправлений

**Files:**
- Modify: `scripts/diagnostic_standard_links.py`
- Modify: `scripts/generate_diagnostic_standard_links.py`
- Modify: `tests/test_diagnostic_standard_links.py`
- Modify: `tests/test_autoformat_fixes.py`

**Interfaces:**
- Consumes: `AutoformatCatalog`.
- Produces: раздельные `checks` и `fixes` в реестре и обратных ссылках.

- [ ] **Step 1: Добавить падающие тесты представления исправлений**

```python
def test_registry_separates_checks_and_fixes():
    rendered = render_registry_index(reviews, standard_pages, autoformat_catalog)
    assert "1 проверка · 1 исправление" in rendered
    assert 'class="diagnostic-chip diagnostic-chip--fix"' in rendered
    assert "Нет проверок и исправлений" in rendered


def test_standard_page_renders_separate_fix_block():
    rendered = rewrite_standard_page(source, "std765", reviews, autoformat_catalog)
    assert 'aria-label="Исправления"' in rendered
    assert "autoformat:std765" in rendered
```

- [ ] **Step 2: Проверить ожидаемое падение**

```bash
.venv/bin/python -m unittest tests.test_diagnostic_standard_links tests.test_autoformat_fixes -v
```

Expected: FAIL из-за отсутствующего параметра каталога и CSS-класса.

- [ ] **Step 3: Обобщить внутреннюю модель связей**

Добавить к генератору отдельную коллекцию исправлений. Не расширять
`DIAGNOSTIC_RE` значением `autoformat`: исправление не является диагностикой.
`render_registry_index` принимает необязательный `autoformat_catalog` и для
каждого пункта формирует две группы:

```python
checks = tuple(sorted(by_clause_checks.get((standard, clause), ())))
fixes = tuple(sorted(by_clause_fixes.get((standard, clause), ())))
```

Счётчики выводятся раздельно, а `data-empty="true"` устанавливается только при
`not checks and not fixes`.

- [ ] **Step 4: Добавить отдельные управляемые блоки обратных ссылок**

Использовать независимые маркеры:

```html
<!-- fix-backlinks:start clause=2 -->
<div class="fix-links" aria-label="Исправления">
<a class="diagnostic-chip diagnostic-chip--fix" href="../diagnostics/autoformat/std765.md">autoformat:std765</a>
</div>
<!-- fix-backlinks:end clause=2 -->
```

Повторная генерация должна быть идемпотентной и не менять существующие
`diagnostic-backlinks`.

- [ ] **Step 5: Запустить тесты и закоммитить генератор**

```bash
.venv/bin/python -m unittest tests.test_diagnostic_standard_links tests.test_autoformat_fixes tests.test_diagnostics_registry_js -v
git add scripts/diagnostic_standard_links.py scripts/generate_diagnostic_standard_links.py tests/test_diagnostic_standard_links.py tests/test_autoformat_fixes.py
git commit -m "feat: generate autoformat fix relationships"
```

Expected: выбранные тестовые модули проходят.

### Task 3: Сгенерировать карточки и написать руководство по обработке

**Files:**
- Create: `docs/diagnostics/autoformat/index.md`
- Create: `docs/diagnostics/autoformat/tool.md`
- Create: `docs/diagnostics/autoformat/std437.md`, `std441.md`, `std453.md`,
  `std455.md`, `std456.md`, `std458.md`, `std467.md`, `std474.md`,
  `std478.md`, `std644.md`, `std680.md`, `std702.md`, `std765.md`,
  `std767.md` — только для подтверждённых правил
- Modify: `zensical.toml`
- Modify: `docs/assets/stylesheets/extra.css`
- Modify: `docs/assets/javascripts/diagnostics-registry.js`
- Modify: `scripts/generate_diagnostic_standard_links.py`
- Test: `tests/test_autoformat_fixes.py`

**Interfaces:**
- Consumes: подтверждённый каталог и извлечённые режимы.
- Produces: опубликованные страницы семейства и доступную навигацию.

- [ ] **Step 1: Добавить падающий snapshot-тест карточек**

```python
def test_generated_fix_pages_cover_catalog():
    catalog = load_autoformat_catalog(REPO_ROOT / "data/autoformat-fixes.json")
    for fix in catalog.fixes:
        page = REPO_ROOT / "docs/diagnostics/autoformat" / f"{fix.id}.md"
        text = page.read_text(encoding="utf-8")
        assert f"# autoformat:{fix.id}" in text
        assert fix.effect in text
        assert "../../std/" in text
        assert "[Обработка и режимы запуска](tool.md)" in text
```

- [ ] **Step 2: Реализовать генерацию карточек и индекса**

Каждая карточка имеет структуру:

```markdown
# autoformat:std765

## Что исправляет

<подтверждённое преобразование>

## Область применения

<объекты и режимы>

## Связанный стандарт

[#std765, п. 2](../../std/765.md#2)

## Инструмент

[Обработка и режимы запуска](tool.md)
```

Индекс перечисляет карточки, преобразования и точные пункты стандартов.

- [ ] **Step 3: Написать страницу инструмента**

`tool.md` должен содержать проверенные разделы:

```markdown
# Автоформатирование кода и локализация

## Где получить
## Перед запуском
## Работа с XML-выгрузкой и проектом EDT
## Работа с файловой базой
## Работа с серверной базой
## Работа с хранилищем конфигурации
## Просмотр и загрузка изменений
## Программный вызов
## Пакетный запуск
## Формат Config.xml
## Поддерживаемые исправления
## Ограничения
```

Пример `/Execute` должен использовать кавычки вокруг всех путей. Секреты и
пароли в примере `Config.xml` не публиковать.

- [ ] **Step 4: Добавить семейство в навигацию и оформление**

В `zensical.toml` добавить:

```toml
[[project.nav."Исправления"]]
"Автоформатирование кода и локализация" = [
    { "Сводная таблица" = "diagnostics/autoformat/index.md" },
    { "Обработка и запуск" = "diagnostics/autoformat/tool.md" },
]
```

В CSS выделить `.diagnostic-chip--fix` текущими цветовыми токенами темы, а
JavaScript научить учитывать `data-empty` по обеим группам без изменения
клавиатурной доступности.

- [ ] **Step 5: Сгенерировать страницы и проверить идемпотентность**

```bash
.venv/bin/python scripts/generate_diagnostic_standard_links.py --write
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check
.venv/bin/python -m unittest tests.test_autoformat_fixes tests.test_diagnostic_standard_links tests.test_diagnostics_registry_js -v
```

Expected: `--check` сообщает отсутствие изменений, все тесты проходят.

- [ ] **Step 6: Закоммитить пользовательскую документацию**

```bash
git add data/autoformat-fixes.json docs/diagnostics docs/std zensical.toml docs/assets scripts/generate_diagnostic_standard_links.py tests
git commit -m "docs: publish autoformat fixes family"
```

### Task 4: Обновить поиск, AI/MCP-артефакты и выполнить полную проверку

**Files:**
- Modify: `scripts/generate_ai_artifacts.py`
- Modify: `scripts/v8std_mcp_index.py`
- Modify: сгенерированные AI/MCP-файлы
- Modify: `docs/index.md`, если на главной перечисляются семейства
- Test: релевантные тесты `tests/`

**Interfaces:**
- Consumes: опубликованные карточки `autoformat`.
- Produces: поиск и MCP-индекс, которые различают диагностики и исправления.

- [ ] **Step 1: Добавить тест поиска исправления**

```python
def test_autoformat_fix_is_searchable_as_fix_not_diagnostic():
    item = next(item for item in index if item["id"] == "autoformat:std765")
    assert item["kind"] == "fix"
    assert item["standard"] == "std765"
```

- [ ] **Step 2: Реализовать индексирование `kind=fix`**

AI/MCP-генераторы должны включать карточки и страницу инструмента, но не
называть `autoformat` диагностикой и не увеличивать существующие счётчики
ACC/BSLLS/EDT.

- [ ] **Step 3: Перегенерировать артефакты**

```bash
.venv/bin/python scripts/generate_ai_artifacts.py
.venv/bin/python scripts/generate_diagnostic_standard_links.py --check
```

- [ ] **Step 4: Запустить полную проверку**

```bash
.venv/bin/python -m unittest discover -s tests -v
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
git diff --check
git status --short
```

Expected: все тесты и строгая сборка проходят; `git diff --check` не выводит
ошибок; в статусе только ожидаемые файлы задачи.

- [ ] **Step 5: Проверить сайт вручную**

В локальной сборке открыть:

- `/diagnostics/`;
- `/diagnostics/autoformat/`;
- `/diagnostics/autoformat/tool/`;
- минимум две карточки;
- минимум две страницы связанных стандартов.

Проверить поиск `autoformat:std765`, раздельные подписи и счётчики, мобильную
ширину и обе цветовые темы.

- [ ] **Step 6: Финальный коммит**

```bash
git add docs data scripts tests zensical.toml
git commit -m "feat: integrate autoformat fixes with search"
```

После коммита повторить полный тестовый набор и строгую сборку.
