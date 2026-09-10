---
schema_version: 1
kind: contract
id: MCP_CORPUS_SNAPSHOT
scope: product
version: 1
revision: 0
compatibility: backward-compatible
design: design:mcp-container-distribution
producer: site artifact builder and static index publisher
consumers:
  - MCP background snapshot loader
  - local static-site image builder
  - release verifier and operators
requirements:
  - MCP_RUNTIME_AND_CORPUS_RELEASE_INDEPENDENTLY
  - MCP_SITE_SETTING_CONTROLS_SOURCE_AND_LINKS
  - MCP_SNAPSHOT_LOAD_IS_ATOMIC
  - MCP_REFRESH_STAYS_OUTSIDE_TOOL_CALLS
  - MCP_SNAPSHOT_IO_IS_BOUNDED
  - MCP_INDEX_DELIVERY_SURVIVES_RUNTIME_RESTART
  - MCP_LOCAL_SITE_HAS_NO_BACKGROUND_PUBLIC_EGRESS
  - MCP_OFFLINE_USES_VERIFIED_CACHE
governs:
  - scripts/generate_ai_artifacts.py
  - scripts/generate_search_vectors.py
  - scripts/v8std_mcp_index.py
  - scripts/v8std_mcp_snapshots.py
  - scripts/generate_mcp_snapshot.py
  - deploy/nginx
  - .github/workflows
  - tests/test_v8std_mcp_snapshots.py
conformance:
  module: tests.test_v8std_mcp_snapshots
  command: .venv/bin/python -m unittest tests.test_v8std_mcp_snapshots -v
required_when: implemented
supersedes: []
deprecates: []
---

# Corpus snapshot 1.0

## Источник и адреса

Единственная публичная настройка — `V8STD_MCP_SITE_URL`, по умолчанию
`https://v8std.ru/`. CLI `--site-url` имеет приоритет над env; пустое явно
заданное значение является ошибкой конфигурации. Удаляются внешние пробелы,
схема/host нормализуются, default port убирается, base path сохраняется и
завершается `/`. Запрещены userinfo, query, fragment, неподдерживаемые схемы,
неоднозначные encoded separators и выход из base path через dot segments.
HTTP допускается только при явно заданном site URL для локальной установки;
HTTPS не понижается при redirect. TLS certificate verification обязательна.

Bootstrap — `<SITE_URL>ai/mcp/v1/manifest.json`. Так, base `/knowledge/`
даёт `/knowledge/ai/mcp/v1/manifest.json`, а не URL от корня host. Для любой
нестандартной установки manifest, archive и redirects остаются в том же
origin и base path. Ни manifest, ни его redirect не выбирают новый base URL
ответов. Запросы не используют credentials из URL и не пересылают secrets.

Только для нормализованного стандартного `https://v8std.ru/` допускается
явный archive URL manifest на `https://ai.v8std.ru/indexes/v1/`. Этот фиксированный
delivery origin не является пользовательским вторым source setting. Redirect
из него допускается только внутри того же origin/path. Для local-site даже
такой public archive URL отклоняется. Не более трёх redirects с проверкой
каждого перехода; `//foreign-host`, traversal и смена схемы не обходят правила.
Отсутствующий manifest даёт ошибку обновления, не fallback к старым public URLs.

SITE_URL должен быть доступен и контейнеру, и пользователю, открывающему ссылки.
Адрес `http://site:8080/`, видимый только Docker DNS, для браузера не подходит.
Compose-документация предоставляет проверенный общий адрес и сетевое разрешение
для host/контейнера, не вводит скрытый второй URL. Если такая маршрутизация
отсутствует, setup должен сообщить об этом, а не выдавать неработающие ссылки.

## Manifest

UTF-8 JSON object, schema major 1; обязательные поля:

| Поле | Значение |
|---|---|
| `schema_version` | Целое `1`. |
| `source_sha` | Полный Git SHA входов публикации. |
| `corpus_id` | SHA-256 content descriptor, определённый ниже. |
| `archive.path` | Относительный URL от directory manifest либо разрешённый абсолютный URL. |
| `archive.sha256` | SHA-256 точных сжатых байтов архива. |
| `archive.bytes` | Точное число сжатых байтов. |
| `archive.unpacked_bytes` | Сумма размеров пяти обычных файлов без tar padding. |
| `vector_model` | `v8std-hash-embeddings-v1`. |
| `vector_dim` | Целое `256`. |

Неизвестные optional поля игнорируются; неизвестная major, duplicate JSON keys,
неверный тип или unsupported model/dim отклоняются. Hash имеет 64 lowercase hex
символа. Archive path публичной публикации равен
`https://ai.v8std.ru/indexes/v1/<archive.sha256>/snapshot.tar.gz`; локальной —
`<archive.sha256>/snapshot.tar.gz` относительно directory manifest.
SHA не считается цифровой подписью: доверие к manifest задаётся настроенным
сайтом и TLS, а hash обеспечивает целостность указанного им содержимого.

## Архив и воспроизводимость

Один детерминированный `tar.gz`, ровно пять regular-file members в заданном порядке:

1. `metadata.json`;
2. `pages.jsonl`;
3. `search-vectors.jsonl`;
4. `llms.txt`;
5. `llms-full.txt`.

Нет каталогов, дополнительных entries, duplicates, PAX/GNU extensions,
symlinks/hardlinks, device files, absolute paths или traversal. Metadata UID/GID,
permissions и tar mtime фиксированы; gzip mtime = 0, filename отсутствует.
Generator и compression implementation закреплены входами сборки. Распаковка
потоковая в новый private staging directory, не `extractall` в рабочий cache.
Дополнительные gzip members/trailing payload отклоняются.

`metadata.json` содержит `schema_version`, `source_sha`, `corpus_id`,
`canonical_site_url`, `vector_model`, `vector_dim` и `files`. `files` — object
с ровно четырьмя ключами остальных имён; каждое значение содержит `sha256`,
`bytes` и для JSONL `rows` (непустые строки). Canonical site — происхождение
входных ссылок, не URL локальной установки и не новый источник сети.

Content descriptor — весь metadata object **без** `corpus_id`; его canonical
JSON encoding: UTF-8, ключи sorted, separators `,` и `:`, без ASCII escaping,
без float/NaN и без завершающего newline. SHA-256 этих байтов — `corpus_id`.
Metadata не включает hash самого metadata или архива: цикла самохеширования
нет. Archive hash — отдельный delivery ID. Public/local publication одного
corpus используют одинаковые archive bytes; только manifest path отличается.

## Семантическая проверка

Pages и vectors сохраняют текущий формат строк, дополненный переносимыми
`site_path` и `markdown_path` страницы. Это относительные пути от SITE_URL без
origin, traversal или scheme. Существующие `url`/`markdown_url` канонического
сайта остаются в артефакте для совместимых потребителей. Runtime формирует
выходные URL по site paths и выбранному SITE_URL, а не доверяет этим origin.

Внутренние ссылки в Markdown/HTML body, llms и выдаваемом pages Resource
перепривязываются по разобранным ссылочным узлам и catalog canonical paths.
Сохраняются fragment/query при допустимом локальном path. Внешние
`source_urls`, текст кода, строковые литералы, inline/fenced code не меняются.
Нельзя выполнять глобальный replace домена. Publisher проверяет отсутствие
неразрешённых внутренних ссылок; reader проверяет границы путей. Старые stable
ID, aliases, relations и фильтрация support pages сохраняются.

Pages IDs уникальны; vector identity `(id, field, chunk_index)` уникальна и
ссылается на существующую страницу/чанк. Model/dim всех строк совпадают с
metadata и реализацией reader. Base64 имеет точную длину 256 float32,
компоненты конечны; `text_sha256` совпадает с соответствующим чанком по
сохранённым правилам генератора. Hash/size/count каждого файла совпадает с
metadata, а metadata — с manifest. Empty corpus, dangling vectors и частично
валидные поколения целиком отклоняются, а не подмешиваются к старому index.

Presentation URL rebasing не меняет retrieval input и text hashes:
поиск/проверка векторов работают с каноническими данными, ссылки преобразуются
только на границе ответа. Локальные и публичные установки дают одинаковые
scores/IDs для одного запроса и corpus; различаются только site URLs.

## Бюджеты загрузчика

Стартовые safety limits, уточняемые только согласованной ревизией:

| Объект | Предел |
|---|---|
| Manifest и metadata каждый | 64 KiB |
| Archive compressed | 16 MiB |
| Сумма распакованных файлов | 64 MiB |
| Pages / vectors | 16 / 32 MiB |
| llms / llms-full | 4 / 16 MiB |
| Одна JSONL строка | 1 MiB UTF-8 |
| Pages / vector rows | По 100 000 |
| Вся попытка обновления | 360 секунд monotonic deadline |
| Блокирующий сетевой read | Не более 20 секунд и остатка общего deadline |
| Cache на экземпляр volume | 256 MiB, включая staging и pinned generations |

Общий бюджет уточнён прямым решением пользователя «поставь 360 секунд и
продолжай» до первого выпуска этого контракта. Он включает download,
verification, generation construction и передачу результата координатору;
это не timeout tool call. Предел одного сетевого read остаётся 20 секунд.
Close/SIGTERM отменяет worker, не ожидая исчерпания всех 360 секунд.
Более короткие readiness/transaction budgets host-controller независимы:
контроллер вправе отменить ещё не готовый candidate раньше этого предела.

Content-Length проверяется, но не заменяет счётчик фактически прочитанных
байтов. Число JSON nesting levels ограничено 32; строки, числа и arrays
проверяются до построения index. Сжатый файл отдаётся как `application/gzip`
без `Content-Encoding: gzip`, чтобы HTTP decompression не меняла hash и бюджет.

Если места недостаточно, refresh прекращается с ограниченной ошибкой. Active
и rollback-pinned файлы не удаляются ради загрузки нового; temporary/stale
unreferenced files убираются только в собственном cache namespace. Внутрипроцессное
потребление RAM staging+active измеряется отдельно: byte-limit архива не
является доказательством memory-limit Python index.

## Cache, update и readiness

Namespace = SHA-256 нормализованного SITE_URL плюс schema major. Startup
проверяет last-good generation и его файловые hashes до использования; при
повреждении пробует предыдущий валидный **того же** namespace. Проверенный
cache позволяет стать ready без доступной сети, refresh запускается фоном.

Staging → verification → index construction → durable cache commit → atomic
process pointer swap. Query lock защищает только короткий swap, не сеть/парсинг/CPU build.
Файловый commit использует fsync и atomic rename; после crash active pointer
указывает либо на старую, либо на полностью записанную новую копию. Дисковый
pointer записывается до process pointer swap, а при ошибке записи старый
active сохраняется. Отдельный refcount удерживает поколение для текущих запросов.

Один background updater на процесс; межпроцессная блокировка namespace
сериализует скачивание/commit при общем volume. Query не берёт этот lock.
Процесс, проигравший lock, повторно читает готовый cache вместо повторной
загрузки archive. Каждая копия процесса строит свой in-memory index. Блокировка
имеет timeout; crash владельца освобождает её средствами ОС.

Refresh interval по умолчанию 3600 секунд с jitter ±20%; `--refresh-seconds 0`
отключает периодические обновления после bootstrap. Bootstrap при отсутствии
данных может повторяться с backoff. Ошибки используют backoff 30…3600 секунд
с jitter ±20%, один in-flight refresh, без бесконечного tight loop. Manifest
проверяется условным GET с ETag/Last-Modified. `304` применяется только при
наличии связанного валидного cache; иначе выполняется обычный GET. При
неизменном archive hash повторно скачивать архив не нужно.

Stale last-good остаётся ready без искусственного срока годности. Exported
metadata отличает `loaded_at`, `last_checked_at`, `last_success_at` и
`refresh_error_code`. Логи не содержат raw corpus, procedure или секреты URL.
Для операционного rollback можно закрепить поколение локальным release state;
это внутренний механизм host, не второй public source variable.

## Статическая доставка и публикация

nginx читает отдельный read-only каталог immutable объектов; publisher имеет
право атомарно добавлять файлы, но runtime не может менять раздачу. GET/HEAD
поддерживают Content-Length, ETag и immutable cache headers. Directory listing
выключен. GET файла не создаёт backend connection к MCP. Префикс `/indexes/`
не проксируется в runtime и не получает его POST-only правила.

Manifest публикуется с revalidation (`max-age=0, must-revalidate` там, где
публикатор управляет headers); на Pages проверяется фактический cache profile,
краткая задержка freshness допустима. Архивы хранятся минимум семь суток после
последней ссылки опубликованного manifest и дольше при rollback pin. GC
учитывает историю публикаций и pinned releases, а не только mtime. Текущий
manifest и rollback target никогда не ссылаются на удалённый объект.

Download connection/byte budgets отделены от MCP admission, с учётом общего
NAT. Конкретные nginx/host лимиты выбираются по смешанному load test; лимит
RPS сам по себе не защищает полосу от большого файла. Публикация на том же host
переносит стоимость трафика с Pages, а не устраняет её.

## Conformance

Будущий module проверяет валидную пару source/public и source/local-prefix;
hostile manifest/redirect/archive; version/model/hash/row mismatches;
atomicity и crash на каждой cache стадии; запрет query-path network;
offline/source-switch/304 recovery; concurrent readers/updaters; URL rebasing
без порчи code/external provenance; nginx restart-independence и bounded I/O.
