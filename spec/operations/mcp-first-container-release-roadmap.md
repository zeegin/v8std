# MCP: план первого выпуска Docker и перехода публичного сервера

Дата: 2026-09-10. Это план дальнейших работ на согласование, не отчёт о выпуске.
Он связывает локальный implementation plan с последующими операциями публикации
и первой миграции. Внешние операции ниже намеренно не являются checkboxes
structured plan: их нельзя требовать до merge-ready и одновременно выполнять
только после проверенного main.

Уточнение15сентября: публичный мониторинг отдельно отключён по явному
согласованию, см. [проверки и архив](2026-09-15-public-monitoring-retirement.md).
Сохранение dashboard и private sampler больше не входят в выпуск. Закрытые
логи/rotation и health/readiness остаются; подключение persistent usage log
нового контейнера всё ещё требует реализации и проверки в Task6.

**Goal:** опубликовать рабочий `ghcr.io/zeegin/v8std-mcp`, обеспечить публичный
источник индексов и перевести `ai.v8std.ru/mcp` на тот же опубликованный образ.

**Architecture:** один runtime image для локального stdio/HTTP и production;
независимые выпуски corpus; nginx раздаёт immutable архивы вне MCP. Первый
переход — отдельная операторская операция с возвратом к Python deployment;
обычные автоматические обновления используют проверенный container predecessor.

**Tech Stack:** текущие Python/MCP, Docker/Compose, nginx/systemd, GitHub Actions
и GHCR. Новый поисковый движок или новый формат быстрого дискового индекса
в первый выпуск не добавляются.

**Spec:** [design](../designs/2026-09-10-mcp-container-distribution-design.md),
[release contract](../contracts/mcp-release-runtime-v1-r0.md),
[implementation plan](../plans/2026-09-10-mcp-container-distribution-plan.md),
[CI policy plan](../plans/2026-09-10-mcp-ci-deployment-policy-plan.md).

## Global Constraints

- Один `/mcp`, один опубликованный runtime image на версию; без отдельного v3.
- `V8STD_MCP_SITE_URL` выбирает и данные, и адреса ответов; второй URL-setting нет.
- Persistent cache volume сохраняется при замене контейнера. Рабочие запросы
  используют готовый индекс в памяти и не инициируют скачивание.
- Новый процесс читает/проверяет cache и готовит поисковые структуры. Это ещё
  не быстрый старт из полностью материализованного индекса. Измерять отдельно
  download, cache verification, preparation, readiness и query latency.
- Первая поставка — Docker image и публичный endpoint; Catalog пока отложен.
  Потеря `longLived` в локальном тестовом генераторе Docker не блокирует выпуск.
- Нельзя объявлять 100000 подключений подтверждёнными без соответствующего
  смешанного нагрузочного теста. Числа CPU/RAM/FD сами по себе такого права не дают.
- Основной checkout, ветка `codex/mcp-container-distribution-design`.
  Structured files из main не изменяются. Код в работе не удаляется и не теряется.
- До live-операций нужны отдельные разрешения на точные host/settings targets;
  до остановки MCP — назначенное окно и проверенный SHA main/digest.
- Окно первой миграции до120минут не увеличивает 360s loader /20s read,
  300s transaction /90s readiness /30s smoke /45s stop.

## Зафиксированная исходная точка

| Часть | Доказанное состояние на момент планирования |
|---|---|
| Формат snapshot, cache, runtime, образы | Tasks1–4 прошли локальные scoped reviews; повторять реализацию не нужно |
| Текущая ветка | Последний signed commit `3165cc7e6ef2afcf12cdeca66c8070ab0737ba5b`; изменения Task5 не закоммичены |
| Task5 release/controller | Приостановлен. Последние29 release-тестов GREEN; hold и snapshot/runtime после последних исправлений требуют повторного прогона и review |
| Первый переход | Обычный `deploy` уже требует `active.json` и container predecessor; bootstrap со старого Python service ещё нужно реализовать и проверить |
| CI | Task6 не реализован; существует прежний Pages workflow |
| Публичный bootstrap | `https://v8std.ru/ai/mcp/v1/manifest.json` в осмотре10сентября отвечал404 |
| Целевой сервер | Ресурсы и зависимости проверяются в закрытом preflight; прежние наблюдения не доказывают готовность к миграции |
| GitHub setup | Защита main, production environment и ограниченные credentials требуют отдельной проверки перед активацией |
| Окно | Stop/start ограничен двумя часами; конкретное окно требует отдельного согласования до остановки сервиса |

Эти наблюдения не заменяют свежий preflight перед публикацией/миграцией.
Успешные тесты ранних задач не означают, что текущий dirty checkout готов к merge.

## Этап 1. Завершить код поставки и первичной миграции

Владелец: исполнитель Task5, затем независимый scoped reviewer. Сначала
продолжить сохранённую работу; после стабильного обычного контроллера выполнить
отдельный first-migration slice из обновлённого implementation plan.

Файлы: `scripts/v8std_mcp_release.py`, `scripts/v8std_mcp_hold.py`, затронутые
runtime/snapshot modules, `deploy/container/`, release/hold tests и
`spec/operations/mcp-container-activation.md`.

Порядок:

1. Перепроверить исправленные3 сбоя snapshot/runtime; сверить hold, ingress,
   recovery и завершающие операции после COMMITTED. Не считать прошлый GREEN
   доказательством ещё не проверенных изменений.
2. Закончить static store и ограниченный upload ingress. Проверить реальным
   nginx GET/HEAD, SHA/длину, cache headers, отсутствие immutable404 и доступность
   файла при остановленном MCP.
3. Реализовать first-bootstrap без фиктивного `active.json`: операторское окно,
   резервная копия legacy, host-owned recovery, smoke и запись первого accepted
   container. CI не получает команду bootstrap или право выключить legacy.
4. Проверить stop/start и возврат на реальных одноразовых процессах, включая
   потерю SSH, SIGKILL/reboot, сбой nginx, неготовый индекс и сбой сохранения state.
5. Завершить activation runbook, signed commit и scoped review каждого среза.

Команда focused regression:

```sh
.venv/bin/python -m unittest tests.test_v8std_mcp_release tests.test_v8std_mcp_release_hold tests.test_v8std_mcp_snapshots tests.test_v8std_mcp_runtime -v
```

**Выход:** повторяемый локально механизм обновления и первой миграции с
проверенным восстановлением; ни установки на целевом сервере, ни release в registry ещё нет.

## Этап 2. Подключить CI и закрыть локальную приёмку

Владелец: исполнитель Task6 после Task5; процессный plan исполняется внутри
этой же задачи, не вторым параллельным владельцем тех же файлов.

Файлы: `.github/workflows/ci.yml`, `scripts/publish_mcp_artifacts.py`,
`tests/test_mcp_publication.py`, current architecture-policy instructions/tests,
public installation docs и verification record.

1. Разделить разрешения на публикацию образа, upload corpus и runtime rollout.
   Отключённый runtime deployment не должен блокировать первые два действия.
2. Реализовать цепочку archive upload → внешняя проверка → Pages manifest.
   До готовности storage сохранить прежнюю рабочую Pages-публикацию без нового
   manifest, указывающего на отсутствующий архив.
3. Собрать runtime `linux/amd64`/`linux/arm64`, SBOM/provenance и local-site image.
   Различать runtime SHA, corpus SHA и trigger SHA; не перелицовывать старый образ
   source SHA нового контентного commit. Классификацию делать относительно
   последней успешно опубликованной версии, учитывая пропущенные/упавшие runs.
4. Проверить PR/fork/tag/stale/failed gates без host effects. До runtime activation
   ни первый bootstrap, ни успешная публикация не включают автодеплой.
5. Исправить известный image-alt/`<code>` дефект presentation перед выпуском;
   отдельным тестом защитить переписывание следующих видимых ссылок. Текущие
   предупреждения зависимостей классифицировать, не скрывать ради зелёного отчёта.
6. Выполнить native Linux smoke/cold/warm/offline и смешанную нагрузку на стенде:
   MCP POST + idle/reconnect + общий NAT + refresh + static download. Записать
   измеренную, а не предполагаемую границу производительности.
7. Semantic impact, CLI impact, fitness и merge-ready; strict build **до**
   полного suite. Затем whole-branch review и исправление его конкретных findings.

```sh
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root . --base-ref main --merge-ready
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
.venv/bin/python -m unittest discover -s tests -v
```

**Выход:** проверенная release-ветка и точный SHA. Локально интегрировать после
всех gates; push main выполнять только с явным разрешением. CI до настройки
внешней активации не должен переключать MCP или публиковать битый bootstrap.

## Этап 3. Подготовить сервер и внешние разрешения — до окна простоя

Работа по согласованному activation runbook из проверенного main, не установка
скриптов из dirty feature checkout. Перед каждым изменением — свежий read-only
inventory и точный список targets. Этот документ сам по себе не выдаёт полномочия.

1. Сохранить вне сервера backup legacy code/config/data, nginx/TLS/renewal и
   закрытых операционных данных. Использовать post-retirement inventory, не
   возвращать generator/job/public files из старых backup. Проверить чтение
   backup и путь запуска старого сервиса без сети.
2. Подготовить статическое хранилище `/indexes/v1/` и restricted upload identity.
   nginx обслуживает его независимо от Docker/runtime. В первой фазе current
   upstream MCP не менять.
3. Установить Docker и root-owned release/initial-recovery units по runbook,
   проверить firewall и автозапуск. Любое потенциально прерывающее действие
   перенести в согласованное окно; не останавливать MCP ради подготовки без него.
4. Настроить GitHub protections/environment/минимальные CI credentials для
   нужных операций. Runtime activation держать выключенной.
5. Получить свежие значения memory/disk/FD и результаты native Linux теста.
   Выбрать overlap только при доказанном запасе. Для stop/start доказать запас
   под один новый runtime + preparation + nginx/службы. При нехватке не начинать
   миграцию; согласовать оптимизацию или изменение ресурсов отдельно.

Зависимости default TLS от сертификатов других vhosts требуют проверки.
Удаление сторонних vhosts/данных — отдельный согласованный cleanup,
не обязательный риск внутри первого cutover. Цель оставить на сервере только
ai сохраняется, но CI не получает права чистить посторонние сайты.

**Выход:** storage и ограниченная доставка готовы, legacy продолжает обслуживать
запросы; разрешение на прекращение сервиса ещё не использовано.

## Этап 4. Опубликовать рабочие артефакты

Для прошедшего gates SHA main запустить разрешённый CI. Кандидатный образ можно
загрузить в registry раньше данных, но стабильный тег не рекламировать и не
продвигать до проверки default source.

Порядок внешних действий:

1. Опубликовать immutable archive на
   `https://ai.v8std.ru/indexes/v1/<archive-sha256>/snapshot.tar.gz`.
2. Извне проверить GET/HEAD, размер, SHA256 и независимость от runtime.
3. Опубликовать Pages manifest
   `https://v8std.ru/ai/mcp/v1/manifest.json`, затем проверить реальную цепочку
   manifest → archive. Идентификатор в URL берётся из проверенного архива.
4. Скачать runtime по digest без авторизации, с изолированной конфигурацией
   credentials; не делать global docker logout. Проверить оба platform manifests,
   подпись/provenance, default-source cold start и warm restart без сети.
5. Проверить local-site image/Compose: один выбранный SITE_URL определяет источник
   и ссылки, локальный маршрут работает без скрытого выхода в публичный интернет.
6. Продвинуть стабильные теги на уже проверенные digests, записать команды запуска
   с persistent volume и точные версии. Нельзя пересобирать отдельный prod image.

**Выход:** пользователь может установить рабочий image; публичный MCP пока
остаётся прежним. Docker Catalog submission и принятие Docker team не требуются.

## Этап 5. Провести первую миграцию в назначенное окно

Входные условия: пользователь назначил дату/время по Москве; записаны UTC
границы, точный проверенный main SHA, image/platform/configuration digests,
corpus ID, backup hashes, способ восстановления и замер его длительности.
Никаких выдуманных дат или автоматического запуска «через два часа».

До окна уже скачаны образ/данные и выполнена репетиция. План распределения
времени ниже — резерв, не ожидание длительности запуска:

| От начала окна | Действия и условие продолжения |
|---|---|
| 0–10мин | Свежий preflight, подтвердить legacy health, артефакты, окно, backup и recovery guard |
| 10–25мин | Одна ограниченная попытка; если overlap не помещается — stop legacy/start candidate; при ошибке немедленный возврат, не ожидание конца окна |
| 25–60мин | Проверка результата/диагностика; повтор только после восстановленного legacy, понятной причины и с новым release ID |
| 60–90мин | Проверка стабильности принятого сервиса и bounded smoke; не экспериментальный stress test на production |
| 90–120мин | Резерв восстановления: если новый сервис не принят — возврат к старому и проверка; новых попыток нет |

Одна попытка сохраняет90s readiness и300s transaction. Ошибка первого запуска
не оправдывает ожидание360s под неготовым публичным upstream. Если замер возврата
требует больше30минут, увеличить резерв до начала окна и сократить рабочую часть.

Критерии успеха:

- публичные TLS, `/mcp`, readiness и реальные initialize/tools/list/search/
  get_page/explain_snippet работают на точном image/corpus;
- новый runtime помещается в ресурсы, нет OOM/restart loop;
- индексы раздаются независимо; persistent cache сохранён;
- первый accepted container record записан, restart/reboot запускает его,
  legacy unit не конкурирует с ним; backup legacy остаётся доступным;
- при неуспехе старый endpoint действительно отвечает с прежними данными.

Полный mixed-load предел измеряется на стенде, не выжимается из production
во время миграции. Результат `RECOVERY_REQUIRED` требует действия оператора и
никогда не маскируется заявлением «всё развернуто».

## Этап 6. Отдельно принять автоматические обновления

1. Проверить content-only выпуск: image digest и процесс не меняются, corpus
   обновляется фоном без сетевого I/O из запроса.
2. Проверить runtime-only выпуск и откат на том же опубликованном digest по
   согласованной процедуре. До live-пробы соответствующая репетиция обязательна.
3. Включить automatic runtime rollout только при доказанной old/new capacity
   и принятых protections/credentials/kill switch. Если помещается один процесс,
   оставить runtime rollout выключенным: image/corpus publication работают,
   бесшовный автодеплой на этом тарифе не объявляется готовым.
4. Зафиксировать public release, команды установки, точные SHA/digests и реальные
   результаты производительности. PR33 закрывать с благодарностью только после
   подтверждения локального и production пути; issue32 автоматически не закрывать.

Следующим отдельным улучшением может стать быстрый старт из подготовленного
дискового индекса. Каталог Docker публикуется по отдельному решению с тем же
образом; проверяется per-entry `longLived`, а не обязательный глобальный флаг.

## Готовность плана и следующая работа

Сейчас выполнено только планирование, остановка/установка/публикация не проведены.
Следующее действие после согласования — продолжить сохранённый Task5,
проверить его незавершённые регрессии и закрыть первый bootstrap slice;
затем Task6. Существующий SDD-порядок с отдельным review сохраняется.

Semantic impact: уточнены границы первой миграции и rollout conformance;
requirement/ADR IDs, публичный API и snapshot schema сохранены. Уточнения
синхронизированы в candidate design/ADR/invariant/release contract/plan, которых
нет в main. Обычные автоматические гарантии не ослаблены. Исправленный Catalog
вывод — корректировка доказательств и текущего scope, не объявление нового
канала принятым. Перед merge нужны все gates, перечисленные выше.
