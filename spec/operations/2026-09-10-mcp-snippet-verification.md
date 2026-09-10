# Проверка крупных процедур в MCP, 10 сентября 2026

## Граница поставки

Реализация согласованного `design:mcp-large-procedure-retrieval` выполнялась в
основном checkout, ветка `codex/mcp-large-procedure-design`, baseline
`3df5b40e773d0e7bc146ac2d9214934bb4145f73`.

Исходный commit PR #31 `6467f77661e855a9f73f571e13db4964bff9c199` включён
локальным merge `f01ab71`; автор `andy24kr` и исходный co-author сохранены.
Перед интеграцией head открытого PR повторно проверен — тот же SHA.
Внешние комментарии, push, site publication и MCP deployment не выполнялись.

## RED / GREEN и причина

- До исходного PR длинная допустимая процедура вызывала ошибку query >500.
- После исходного PR 11 из 12 позиционных проверок с K=1 возвращали
  постороннюю диагностику, а не ожидаемую первичную цель. После отдельного
  включения структурных целей все варианты начала/середины/конца проходят.
- Новые tests проверяют 4k/32k границы, независимость экземпляров, общий top-K,
  отсутствие повторного бонуса, неизвестный target, ложный вызов-идентификатор,
  число поисков ≤1, компактность preview, config precedence и MCP wire.
- Runtime-схема прежде не содержала maxLength. Сейчас обе инстанции 4000/32000
  публикуют свой предел и согласованно проверяют вызовы.
- Public unit до изменения принимал локальный env override 32000. Теперь
  проверка его реальной командной строки через parse_args даёт 4000.
- Helper усечения из PR разрывал длинное слово после короткого первого слова;
  отдельный RED/GREEN-тест закрепляет целый префикс при существующей границе.
- Саморевью выявило общий consumer `search._query_tokens`: дедупликация внутри
  analyze_snippet меняла частоту слов повторного SDBL-запроса с 7 на 6. RED/GREEN
  закрепляет прежние 7; дедупликация перенесена исключительно на границу ответа
  explain_snippet. В обычный search benchmark добавлен этот пограничный запрос.

Дополнительно обнаружен implementation defect: unanchored regex присваивания
секрета перебирал суффиксы длинного идентификатора. Для `"я" * 32000` только
`has_secret_literal` занимал 7637.585 ms, для 4000 — 117.029 ms. Пробный
проход по максимальным identifier candidates — 0.708/0.111 ms соответственно.
Полный исправленный analyze_snippet на 32k слове в отдельном замере — 8.372 ms.
Это разные измеряемые функции; их время нельзя смешивать с полной retrieval latency.

Сохранён прежний assignment regex и порядок потребления совпавшего literal;
изменён только выбор позиций его запуска. 10 000 детерминированных сравнений
со старым scanner совпали; 1000 таких сравнений и граничные литералы включены
в постоянный suite. По `failure-recovery` это implementation defect, не
проектная ошибка: значения лимитов, требования и критерии приёмки не менялись.

## Реальные локальные способы запуска

```bash
.venv/bin/python tests/mcp_snippet_smoke.py --launch python
.venv/bin/python tests/mcp_snippet_smoke.py --launch wrapper
.venv/bin/python tests/mcp_snippet_smoke.py --url http://127.0.0.1:18765/mcp
```

Третий сценарий выполнен на отдельно собранном Compose image, с отдельным
project name, временным контейнером и публикацией порта только на loopback.
Не использовались существующие пользовательские контейнеры.

Во всех трёх сценариях подтверждены initialize, tools/list, все пять tools,
maxLength=32000, K=1/std485 в конце входа и size-error без `private_marker`.
Приняты 32k сообщения в UTF-8 (128051 bytes JSON body) и escaped Unicode
(383867 bytes). GET с Accept: text/event-stream возвращает 405.
Это не проверка публичного nginx: его 256k byte-limit не изменялся.
Проверочные процессы/контейнеры остановлены после проверки.

Compose config отдельно проверен с env=32000: значение действительно передано
контейнеру. Direct Python и wrapper используют общий серверный парсер;
wrapper не изменён и не дублирует обработку env.

## Проверки репозитория

Итоговый полный suite после проверки shared consumer: 369 tests, OK, 39.195 s. Команда:

```bash
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=false \
  .venv/bin/python -m unittest discover -s tests -q
```

Override отключает подпись только временных Git commits внутри тестового
процесса. Global/repository Git config не изменён. Первый прогон был остановлен
во время ожидания GPG в тестовом temporary repo. Затем полный suite обнаружил
недостающие обязательные headings нового ADR; документ исправлен, gate сохранён.
SDK выдаёт deprecation warning о будущем переходе Starlette TestClient на
httpx2; зависимости в этой работе не менялись, conformance выполняется успешно.

Strict build: `VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict`
завершён с кодом 0: 1429 articles, 0 violations, 3281 vectors, 3 canonical
license texts. Корпус стандартов и managed source blocks не менялись.

Отдельный declared fitness/conformance прогон: 65 tests, OK, 8.219 s.
После завершения всех 18 шагов plan выполнены с кодом 0:

```bash
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root .
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready
git diff --check
```

## Semantic impact по фактическому diff

Намерение остаётся нетривиальным и соответствует согласованному графу.
Новые обязанности — полнота сканирования, приоритет целей, конфигурация/discovery,
bounded work и компактная выдача — связаны с design/ADR/invariant/contract и plan.

Изменены только retrieval/snippet и config/discovery в существующем runtime,
локальная Compose env-передача, public unit pin, документация, тесты и внутренние
артефакты. Новая версия observable boundary — совместимая `MCP_API@2.3`.
Имена tools, обязательные аргументы, result shape, единственный `/mcp`, Resources
и POST-only остаются. Подписки, concurrency policy и metrics API не изменены.

CLI impact также перечисляет прежние MCP API/usage/OpenMetrics и transport/
metrics invariants из-за общих governs-путей. Их семантика сохранена: новые
usage labels/поля/исходный код в логах не появляются, listener/metrics/drain
не меняются. Старые structured документы в main не редактировались; новые
документы уточнялись только в candidate-ветке.

## Идентичность проверенного runtime

SHA-256 до завершающей интеграции:

| Файл | SHA-256 |
|---|---|
| scripts/v8std_mcp_index.py | ac9b739775ca14ae7e939ec7f3f732d147b14010b9f70bfdbc6374fffd06eb5e |
| scripts/v8std_mcp_server.py | be1e73a27ad2c2aea08a516ffeede6286feb92a70752e964a13bd8567139d713 |
| scripts/v8std_retrieval_rules.py | 34b823aafa1cc8858a4d5a93449f170da35b1ab543f4661f9a1d66d4f8f79c4b |

## Итоговый latency gate

```bash
.venv/bin/python scripts/snippet_benchmark.py \
  --baseline-ref 3df5b40e773d0e7bc146ac2d9214934bb4145f73 \
  --report .cache/snippet-benchmark-final.json
```

Для каждого сценария: 20 warmups, 200 samples, 3 серии. Таблица содержит
медиану трёх p95, миллисекунды. Измеряется вызов индекса в одном локальном
Python-процессе, а не HTTP или нагрузка одновременно подключённых клиентов.

| Сценарий | 4k / исходный короткий | 32k / новый короткий | Gate |
|---|---:|---:|---|
| Короткий snippet, baseline → исправление | 48.875 | 48.310 | PASS |
| Процедура с признаком в конце | 46.364 | 57.898 | PASS |
| Длинный идентификатор и признак в конце | 50.259 | 57.290 | PASS |
| Кавычки и признак в конце | 49.359 | 59.995 | PASS |

Порог короткого snippet: baseline + max(20%, 10 ms); остальных пар:
p95_4k + max(25%, 20 ms). Все пороги выполнены без ослабления.
231 обычный поисковый case дал полностью идентичные результаты, включая
порядок, score и reasons, на baseline и новом коде при одном и том же корпусе.

Повтор с `--without-vectors --report .cache/snippet-benchmark-no-vectors.json`
сохранил идентичность тех же 231 cases и выполнил все четыре latency gates:

| Сценарий без векторов | 4k / исходный короткий | 32k / новый короткий | Gate |
|---|---:|---:|---|
| Короткий snippet, baseline → исправление | 15.893 | 15.741 | PASS |
| Процедура с признаком в конце | 18.482 | 30.486 | PASS |
| Длинный идентификатор и признак в конце | 16.795 | 24.616 | PASS |
| Кавычки и признак в конце | 16.602 | 28.017 | PASS |

Quality gate: `.venv/bin/python scripts/search_benchmark.py --report
.cache/snippet-retrieval-quality-final.md` — MRR 0.994, p95 45.4 ms.
Пороги MRR ≥0.85 и p95 ≤500 ms не менялись. Все четыре новых длинных
позиционных случая возвращают требуемую цель первой.

Индекс SHA-256: `4876122c8f2fa3c25c49afc0c986a72a976d4466e9b654041729ab42a634f4e4`.
Vectors SHA-256: `7713439da96757be4cf786d303e1cfb4b7e336ca8ec54a28a722701f6ef6c3c8`.
JSON report находится в ignored `.cache`; воспроизводимая команда и итоговые
значения сохранены здесь. Эти результаты не доказывают поддержку 100 000
одновременных пользователей и не описывают состояние production MCP.
