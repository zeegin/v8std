---
schema_version: 1
kind: plan
id: mcp-large-procedure-retrieval
design: design:mcp-large-procedure-retrieval
implements:
  - design:mcp-large-procedure-retrieval
  - adr:SNIPPET_SIGNALS_OUTSIDE_TEXT_QUERY
  - invariant:MCP_SNIPPET_SIGNALS_SURVIVE_TEXT_BUDGET
  - contract:MCP_API@2.3
---

# Large Procedure Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Довести PR #31 до ограниченного и релевантного анализа крупных процедур.

**Architecture:** Полный вход сканируется существующими распознавателями.
Структурные цели объединяются с одним bounded search перед общим top-K.
Лимит экземпляра одновременно управляет проверкой входа и discovery.

**Tech Stack:** Python 3.12, unittest, официальный MCP SDK 1.27.0, Pydantic,
Starlette/httpx, существующий локальный Docker Compose.

**Spec:** [Согласованный design](../designs/2026-09-10-mcp-large-procedure-retrieval-design.md).
Пользователь согласовал пакет и реализацию сообщением «согл делай» 10.09.2026.

## Global Constraints

- Default 4000 Unicode code points; явный override 4000..32000 включительно.
- CLI `--max-snippet-chars` > `V8STD_MCP_MAX_SNIPPET_CHARS` > default.
- Публичный search query ≤500; не более одного hybrid search на snippet.
- Все принятые символы сканируются; исходный ввод не обрезается.
- Preview ≤1000; tokens ≤80 и суммарно ≤4000; повторные signals не копятся.
- Первичные цели > дополнительные > обычные результаты; один общий top-K.
- Один `/mcp`, прежние tool names/result fields; нет нового bulk-доступа.
- Только текущий основной checkout в feature-ветке; frozen main-documents не менять.
- Не изменять веса общего поиска, зависимости или MCP transport.
- Push и MCP deployment не входят в разрешённую реализацию.

## Файлы и интерфейсы

- `scripts/v8std_mcp_index.py`: `V8StdIndex(..., max_snippet_chars: int = 4000)`,
  read-only `max_snippet_chars`, `validate_max_snippet_chars(value: int) -> int`,
  `_rank_snippet_results(signals: list[dict], results: list[dict], limit: int) -> list[dict]`.
  Использовать helper `truncate_for_query` из авторского commit PR.
- `scripts/v8std_retrieval_rules.py`: полный analyze_snippet, bounded token preview;
  сигналов не удаляет, поскольку их кратность участвует в обычном search.
  Дедупликация идентичных signals принадлежит ответу explain_snippet в индексе.
- `scripts/v8std_mcp_server.py`: разрешение config в parse_args; runtime-аннотация
  Field для snippet; инструкции и описание с эффективным размером.
- `docker-compose/docker-compose.yml`, `deploy/systemd/v8std-mcp.service`:
  передача локальной настройки и явный public 4000.
- `docs/mcp.md`, `docs/support.md`: поведение, env/CLI/Compose, безопасность кода.
- `tests/test_v8std_mcp_snippet.py`: новые index/config/wire fitness tests;
  `tests/test_v8std_mcp_server.py`: заменить AST-only discovery на реальное SDK
  там, где описание становится динамическим; остальные проверки сохранить.
- `tests/search_benchmark_cases.yml`: дополнительные позиционные regression cases.
- `tests/mcp_snippet_smoke.py`: loopback-only HTTP smoke для Python, wrapper,
  отдельного проверочного контейнера, обоих вариантов Unicode и пяти tools.
- `scripts/snippet_benchmark.py`, `tests/test_snippet_benchmark.py`: reproducible
  сравнение с baseline Git SHA и проверка latency gate без таймингов в unit suite.
- `spec/operations/2026-09-10-mcp-snippet-verification.md`: фактические результаты
  RED/GREEN, runtime smoke, benchmark и gates; без исходного закрытого кода.

## Task 1: Полнота целей и компактность на стандартном окне

Consumes: `RetrievalRules.analyze_snippet(snippet)`, `V8StdIndex.search(query, ...)`.
Produces: `_rank_snippet_results(...)` и прежний `explain_snippet(...)` response.

- [x] Добавить regression на std485/std740 в конце 4000-символьной процедуры,
  несколько первичных целей, высокий score посторонней страницы, отсутствующий
  target, повторные SDBL signals и длинные токены.

```python
snippet = "ВычислитьЗначение(Объект);\n" * 100 + "УстановитьПривилегированныйРежим(Истина);"
result = index.explain_snippet(snippet, limit=1)
self.assertEqual([item["id"] for item in result["standards"]], ["std485"])
```

- [x] Выполнить `.venv/bin/python -m unittest tests.test_v8std_mcp_snippet -v`:
  сначала исходная ошибка query, после авторского исправления — отсутствие std485.
  Сохранить исходный commit PR и его тест в истории локальным merge проверенного head.
- [x] Реализовать отдельное разрешение целей и один query из preview. Для каждого
  ID один бонус 4200/2200, причина `snippet_signal:<rule-or-type>`; дедупликация
  по ID и сортировка `(priority, -score, concrete_rank, type, id)` перед общим K.

```python
query = truncate_for_query(analysis["normalized_text"])
results = self.search(query, types=["diagnostic", "standard", "pattern"],
                      mode="hybrid", limit=requested_limit)["results"]
results = self._rank_snippet_results(analysis["signals"], results, requested_limit)
```

- [x] Ограничить только выдаваемый token preview (целые токены, prefix), убрать
  идентичные signals на границе explain_snippet через set ключей
  `(type, rule, value, tuple(target_ids))`, сохранив legacy query term weights.
  Сканирование полного входа сохранить. Подтвердить GREEN новых и прежних index tests.

- [x] Исправить найденный implementation defect распознавания secret: при 32k
  одном идентификаторе unanchored regex занимает 7.64 s. Итерировать максимальные
  identifier candidates и применять прежний assignment regex через match только
  к их началам; после совпадения пропускать кандидаты внутри потреблённого literal.
  Сохранить старую семантику oracle/differential-тестом, доказать отсутствие
  квадратичного роста отдельным benchmark. Требования и пороги не меняются.

## Task 2: Настройка экземпляра и MCP discovery

Consumes: `V8StdIndex.explain_snippet`, `_rank_snippet_results` из Task 1.
Produces: проверенный `index.max_snippet_chars` и `parse_args(...).max_snippet_chars`.

- [x] Добавить RED на constructor limits, N−1/N/N+1 для 4k/32k, два независимых
  индекса, 501-символьный search, env/CLI precedence и invalid config до index.load.

```python
with patch.dict(os.environ, {"V8STD_MCP_MAX_SNIPPET_CHARS": "32000"}):
    self.assertEqual(parse_args([]).max_snippet_chars, 32000)
    self.assertEqual(parse_args(["--max-snippet-chars", "4000"]).max_snippet_chars, 4000)
```

- [x] Реализовать validator: type(value) is int, 4000 ≤ value ≤32000; private
  backing field + property без setter. В parse_args выбирать CLI до env, затем
  ASCII digits после strip; argparse.error без echo входного значения при ошибке.
  Default constructor не читает env; сервер передаёт уже разрешённое число.
- [x] Добавить RED wire-test реального FastMCP через Starlette TestClient lifespan:
  initialize, tools/list, tools/call с границами и ошибками, UTF-8/escaped Unicode,
  отсутствие кода в size-error и usage log, остальные четыре tools доступны.

```python
self.assertEqual(tool["inputSchema"]["properties"]["snippet"]["maxLength"], 32000)
self.assertFalse(call_result["isError"])
self.assertNotIn("private_marker", oversized_error_text)
```

- [x] Перед регистрацией установить вычисленную аннотацию
  `Annotated[str, Field(json_schema_extra={"maxLength": index.max_snippet_chars})]`;
  description содержит effective limit, одну процедуру и отсутствие бессмысленных
  повторов. Проверка длины остаётся в индексе. Прогнать config/wire/legacy tests.

## Task 3: Реальные способы запуска и пользовательская документация

Consumes: единый server config из Task 2.
Produces: одинаковый effective limit при Python, wrapper и Compose.

- [x] До изменения config проверить текущий public unit через shlex/parse_args и
  Compose config с env=32000: зафиксировать, что публичный лимит не закреплён,
  а Compose не передаёт новую переменную. Тесты проверяют разрешённые аргументы
  и effective config, не наличие строк в YAML/unit.
- [x] Добавить Compose `V8STD_MCP_MAX_SNIPPET_CHARS: "${V8STD_MCP_MAX_SNIPPET_CHARS-4000}"`
  (пустое значение не подменять default), public ExecStart `--max-snippet-chars 4000`.
  Wrapper не дублирует parser и наследует env.
- [x] Обновить docs: одна крупная процедура, default/local ceiling, CLI precedence,
  restart, tools/list, ограничения preview, non-retryable size-error; закрытый код
  только локально. Объяснить Unicode chars vs proxy bytes, не менять public nginx.
- [x] Smoke запущенных локальных Python и wrapper с временным свободным портом,
  затем изолированного Compose run (не затрагивать существующие containers).
  Проверить initialize/schema/32k call/N+1/POST-only; UTF-8 и escaped payloads.
  Остановить только созданные для проверки процессы/контейнеры.

## Task 4: Качество, стоимость и интеграционные доказательства

Consumes: исправленные runtime и config из Tasks 1–3.
Produces: benchmark JSON/Markdown evidence и полный проверенный diff.

- [x] Добавить позиционные случаи std485/std740/std415/UsingModalWindows в
  существующий benchmark без ослабления thresholds. Проверить query ≤500 и
  call_count ≤1 с реальным search spy на длинном коде/множестве signals.
- [x] Написать RED unit-tests для расчёта p95/median-of-series и сравнения
  latency budgets. Затем `scripts/snippet_benchmark.py`: CLI `--baseline-ref`,
  `--report`; исторические index/rules загрузить из `git show` в изолированные
  Python modules, не переключая checkout и не меняя нынешние imports.
  Сопоставить обычные search ID/order на прежних cases; record index/vector hashes.
- [x] Измерить 20 warmups +200 samples ×3 series в одном процессе для короткого
  baseline/current и пар 4k/32k с одинаковым началом/набором signals. Проверить
  short regression ≤max(20% baseline,10ms), large delta ≤max(25% p95_4k,20ms).
  Проверить отключённые vectors и pathological quotes/long token fixtures.
  Записать реальные числа, не превращать их в обещание 100k concurrency.
- [x] Саморевью diff по всем требованиям, включая конфигурацию, privacy, top-K,
  неизменность обычного search и authored commit ancestry. Зафиксировать semantic
  impact по фактическим путям в operation evidence.
- [x] Выполнить architecture impact/validate, declared fitness,
  `.venv/bin/python -m unittest discover -s tests -v`,
  `VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict` и diff --check.
  Если реализация опровергнет согласованный design, вернуться к brainstorming,
  не менять пороги и не ослаблять тесты ради прохождения.

После завершения checkboxes выполнить `validate --merge-ready`: его gate
проверяет в том числе завершённость самого plan. Commit/merge выполняются
после соответствующих проверок как интеграция, не
условия завершённости plan. После всех gates — локальный merge в main;
никаких внешних комментариев, push или MCP deployment в этом разрешении.
