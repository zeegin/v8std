# Проект инструментов MCP для работы ИИ с кодом и диагностиками

Дата: 17 сентября 2026 года. Описания инструментов и параметров согласованы и реализованы.
Остальные изменения (annotations, outputSchema, подсказки ошибок) не реализованы.
Текущий контракт: [mcp-surface-contract.md](mcp-surface-contract.md).
Этот документ не добавляет согласованных архитектурных правил и не объявляет
совместимость проверенной на выпущенных бинарных версиях Unica.

## Решение

Сохранить пять существующих инструментов, их имена, аргументы и ответы по умолчанию.
Улучшить описания, описания параметров, аннотации и точность схем ответов.
Не добавлять универсальный `analyze`, диспетчер `execute` или дубли `*_v2`:
в имеющемся наборе уже есть отдельное действие для каждого нужного вида входа.

Сервер остаётся источником знаний, используемых ИИ при анализе кода.
Сам анализ проекта и получение исходников выполняются клиентом/Unica.
MCP подбирает применимые материалы и объясняет известные коды; наличие совпадения
не доказывает нарушение, отсутствие совпадений не доказывает корректность кода.
Запуск статического анализатора в эту поверхность не входит.

HTTP, Python и текущий SDK сохраняются. Смена фреймворка не нужна для изменения
описаний и создаст отдельный риск совместимости. Рекомендация скила о standalone
FastMCP 3.x рассмотрена, но не превращается в обязательную миграцию существующего сервера.
Нет новой авторизации, доступа к файловой системе пользователя, UI-ресурсов,
stdio или дополнительного сетевого сервиса.

## Выбор инструмента по входу

| Что есть у ИИ | Первый вызов | Что он даёт |
|---|---|---|
| Процедура BSL или текст запроса SDBL | `v8std_explain_snippet` | Кандидаты правил и диагностик по сигналам фрагмента |
| Коды диагностик из отчёта анализатора, комментария или подавления в исходнике | `v8std_explain_diagnostics` | Известные диагностики, связанные стандарты и неизвестные коды |
| Точный номер стандарта, ID, псевдоним или URL статьи | `v8std_get_page` | Текст соответствующего документа |
| Вопрос словами, неизвестное название, неоднозначный номер без источника | `v8std_search` | Ранжированные кандидаты |
| Известная статья и необходимость посмотреть связанные правила | `v8std_get_related` | Явные связи в корпусе |

«Коды» здесь — идентификаторы диагностик и стандартов. Число в строковом литерале,
бизнес-код номенклатуры и код ошибки внешнего API не становятся диагностикой 1С
только потому, что встретились в исходниках.

Для смешанного входа ИИ отделяет идентификаторы от программного текста:
список известных диагностик отправляется одним вызовом `explain_diagnostics`,
нужный фрагмент — отдельным `explain_snippet`. При известном `std437` чтение
стандарта не требует предварительного поиска. Перед выводом о нарушении ИИ
сопоставляет фактический код с текстом выбранных правил через `get_page`;
одна поисковая оценка не является обоснованием нарушения.

## Обратная совместимость с Unica

Исследованы локальные теги репозитория Unica:

- `v0.5.1`: `04b97cf4ae4b4139b7856540cdd39c76c00486aa`;
- `v0.12.3`: `f6d23068c397cd85c540812de7627b2c3f434d68`.

В обоих `crates/unica-coder/src/infrastructure/internal_adapters.rs`,
`StandardsAdapter::request_for`, содержит следующие фиксированные вызовы:

| Вызов Unica | Имя MCP | Передаваемые аргументы |
|---|---|---|
| `search`, либо `explain` с query | `v8std_search` | `query`, `limit`, `types`, `mode` |
| `explain` с codes | `v8std_explain_diagnostics` | `codes` |
| `explain` со snippet | `v8std_explain_snippet` | `snippet`, `language`, `limit` |
| `explain` с id/idOrAliasOrUrl | `v8std_get_page` | `id_or_alias_or_url`, `body_limit` |

При нескольких полях Unica выбирает codes, затем snippet, затем id, затем query.
Это поведение клиента; серверу не нужно добавлять аналогичный диспетчер.
`get_related` также сохраняется для прямых клиентов, хотя этот адаптер его не вызывает.

Старый адаптер отправляет прямой `tools/call` по HTTP без предварительного
`initialize`, согласования нового профиля и сессионного токена. Этот рабочий
путь нужно сохранить наряду с нормальным жизненным циклом MCP-клиента.

В `v0.12.3` файл `standards_documentation.rs` читает JSON из `content[0].text`:
поиск — `results[].url/title/description/score`, документ — `found`,
`page.body_markdown`, `page.url`, `page.title`. Переход только на
`structuredContent`, Markdown вместо JSON или добавление внешнего `{data: ...}`
сломают этот потребитель, даже если имена инструментов не поменяются.

### Неприкосновенная часть интерфейса

1. Все пять имён, текущие имена аргументов, обязательность, defaults и действующие
   допустимые значения сохраняются. Новых обязательных аргументов нет.
2. Числовые limit продолжают ограничиваться диапазоном, а не отклоняться.
   Пустые строки/списки и действующие aliases остаются допустимыми.
3. Успешный результат сохраняет один первый text-блок с JSON и соответствующий
   `structuredContent`; все прежние поля, типы, null и варианты отсутствия сохраняются.
4. Ненайденное значение остаётся успешным результатом с `found: false`, пустой
   выдачей или `unknown_codes`. Ошибки выполнения сохраняют `isError: true`.
5. Публичный MCP сохраняет `https://v8std.ru/` в URL страниц. Адрес загрузки архива
   на `ai.v8std.ru` не должен становиться базовым адресом статей.
6. Никаких обязательных новых заголовков, аутентификации, сессий или новой версии
   протокола ради пользования прежними инструментами.

**Граница совместимости:** публичный endpoint старой Unica входит в обязательную
приёмку. Потребитель документации Unica v0.12.3 отбрасывает URL вне
`https://v8std.ru/`. Поэтому совместный локальный MCP с локальными URL нельзя
объявить полностью совместимым с этим потребителем без изменения Unica.
Не подменять локальные ссылки публичными: это противоречит согласованной локальной
поставке. Прямые вызовы локального MCP проверяются отдельно; полная поддержка
локальных URL старым потребителем Unica остаётся известным ограничением.

Два исследованных тега не доказывают совместимость всех старых версий. Перед
выпуском нужно проверить границы поколений адаптера в остальных поддерживаемых
тегах и воспроизвести запросы каждого отличающегося поколения.

## Точные описания tools/list

Тексты ниже предназначены для поля `description`, а не для статьи на сайте.
Английский сохраняется как язык интерфейсных описаний; русские запросы и код
поддерживаются. Параметры описываются отдельно в JSON Schema.

### v8std_search

Title: `Search 1C standards and diagnostics`

```text
Search the v8std knowledge base by a natural-language question, topic, or uncertain identifier. Returns ranked page IDs, titles, descriptions, URLs, scores and match reasons; no full article text. Known diagnostic codes are handled by v8std_explain_diagnostics; BSL/SDBL source fragments by v8std_explain_snippet. An exact page ID or URL can be read with v8std_get_page. An empty result means no match in this corpus, not that the code is correct. Scores rank candidates and are not probabilities.
```

### v8std_get_page

Title: `Read a standard or diagnostic article`

```text
Read a known v8std article by ID, alias, source path, HTML URL or Markdown URL, for example std437. Returns found, page metadata, Markdown text and body_truncated; an unknown page returns found=false and possible candidates. body_limit defaults to 12000 characters and is clamped to 1000–30000. A truncated body is incomplete; the returned markdown_url identifies the full document. This is document retrieval, not code analysis. For an unknown topic, v8std_search finds candidate IDs.
```

### v8std_get_related

Title: `Find rules linked to an article`

```text
Retrieve explicit corpus links from a known standard or diagnostic article. Returns related page IDs, relation types, titles, descriptions and URLs, filtered by relations and limited by limit. An unknown starting page returns found=false; an empty related list means no matching recorded links. Links provide reading context, not evidence that a rule is violated. This tool does not discover arbitrary topics or retrieve full article bodies; those operations are v8std_search and v8std_get_page.
```

### v8std_explain_snippet

Title: `Find rules relevant to a BSL or SDBL fragment`

```text
Match one BSL procedure or SDBL fragment against signals in the v8std knowledge base. Returns candidate diagnostics and standards, matched signals and heuristic confidence, with at most limit recommendations in total. It does not execute code, inspect a repository or run a static analyzer; matches are not confirmed violations and no matches do not certify correctness. Full rule text is available through v8std_get_page. Diagnostic identifiers from reports or source comments are handled by v8std_explain_diagnostics. The fragment limit is {max_snippet_chars} Unicode characters; a size error requires a smaller relevant fragment, not an unchanged retry. language records the supplied hint and currently does not select a separate analyzer.
```

`{max_snippet_chars}` подставляется из конфигурации того же экземпляра, из которой
строится `inputSchema.properties.snippet.maxLength`; это не буквальный текст в каталоге.

### v8std_explain_diagnostics

Title: `Explain diagnostic codes and linked standards`

```text
Resolve diagnostic identifiers from analyzer reports or source-code comments and suppressions, such as acc 1245, АПК:361, bslls:AssignAliasFieldsInQuery or an exact v8cs identifier. Accepts up to 500 strings, each up to 200 characters. Returns known diagnostics grouped with linked standards, occurrence frequencies and unknown_codes. Empty entries are ignored; repeated codes are counted. Unknown means not resolved in this corpus, not a verified invalid diagnostic. Resolving a suppression code does not justify the suppression. No wildcard matching or analyzer execution is performed. Full descriptions are available through v8std_get_page using returned IDs.
```

## Параметры и схемы

Названия параметров не улучшать переименованием: они являются API старых клиентов.
К существующим properties добавить следующие `description`:

| Параметр | Текст для JSON Schema |
|---|---|
| `search.query` | `Question, topic or uncertain identifier, in Russian or English. Maximum 500 Unicode characters. Example: модальные окна. Not a full source module.` |
| `search.types` | `Optional page types: standard, diagnostic, fix, pattern, service. null or [] means all types.` |
| `search.mode` | `hybrid combines available matching methods (default); exact includes identifier variants and fuzzy code matches; bm25 is text/metadata search; semantic uses indexed vectors.` |
| `*.limit` | `Maximum results, default 10. Values are clamped to 1–50. For explain_snippet this is the combined diagnostics and standards budget.` — последнее предложение только для snippet |
| `*.id_or_alias_or_url` | `Known article ID, alias, source path, HTML or Markdown URL; maximum 1000 Unicode characters. Example: std437.` |
| `page.body_limit` | `Markdown body budget in Unicode characters, default 12000, clamped to 1000–30000. A truncation marker may add characters; inspect body_truncated.` |
| `related.relations` | `Optional relation kinds: standard, diagnostic, edt_check, related. Legacy related_standard and related_diagnostic are accepted. null or [] means all.` |
| `snippet.snippet` | `One relevant BSL procedure or SDBL fragment. Limit is the advertised maxLength. The normalized response may contain source text; omit secrets.` |
| `snippet.language` | `Source-language hint: auto (default), bsl or sdbl. Currently echoed in the response without selecting a separate analyzer.` |
| `diagnostics.codes` | `Exact diagnostic identifiers with analyzer namespace when known; up to 500 entries of at most 200 characters. Example: ["acc 1245", "bslls:AssignAliasFieldsInQuery"]. No source files or raw analyzer report.` |

Отразить уже действующие maxLength/maxItems и enum. Сохранить null и пустые
массивы там, где они принимаются. Не добавлять `minLength: 1` или
`minItems: 1`. Для limit/body_limit не вводить minimum/maximum с отказом вместо
нынешнего clamping. Не вводить `additionalProperties: false` на входе без
проверки прежнего поведения SDK и старых запросов.

OutputSchema описывает существующие объекты из текущего контракта: SearchEntry,
Relation, варианты found/not-found, результаты snippet и diagnostics. Не вводить
новый внешний контейнер, обязательные поля, отсутствующие на отдельных ветках,
или удаление неизвестных полей корпуса при сериализации. В частности,
`semantic_enabled` отсутствует на пустом поисковом запросе; `description` связи
может быть null. Модели/схемы должны описывать ответы, а не менять их.

Все инструменты получают понятный title и annotations:
`readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`,
`openWorldHint: false`. Последнее относится к работе с выбранным корпусом:
инструмент не открывает произвольный URL из аргумента. Фоновое скачивание
индекса отдельно от вызова инструмента не является обещанием отсутствия сети.
Обновление корпуса может менять ответ при повторном запросе.

## Объём ответов и исправление ошибок

В этом изменении не добавлять `format`, компактный режим по умолчанию или
пагинацию: старые поля нельзя удалить ради экономии токенов. Ограниченный список
кандидатов и отдельное чтение нужных статей уже позволяют не отдавать весь корпус.
Не возвращать полные тексты всех найденных правил из explain-инструментов.

Для ошибок сохранить транспорт и прежние распознаваемые сообщения; добавить
короткую подсказку без отражения исходного фрагмента или секретов:

| Случай | Подсказка восстановления |
|---|---|
| Слишком длинный snippet/query | Указание допустимой длины; сократить релевантный фрагмент/запрос; неизменённый повтор не поможет |
| Неизвестный mode/type/relation/language | Допустимые значения; исправить аргумент |
| `INDEX_NOT_READY` | Временно нет проверенного индекса; отложенный ограниченный повтор, без смены источника |
| Неизвестный diagnostic code | Успешный `unknown_codes`; проверить namespace и версию анализатора, не выдумывать расшифровку |
| `found: false` | Изучить candidates или уточнить запрос; не сообщать об отсутствии самого стандарта во всех источниках |
| `body_truncated: true` | Текст неполный; увеличить body_limit до действующего максимума или читать полный markdown_url доступным клиенту средством |

Не заменять `isError` на успешный `{error: ...}`. Структурированную новую модель
ошибок не включать в это изменение: она требует отдельной проверки парсеров.
Тексты статей и фрагментов — данные, а не инструкции на запуск команд или
переопределение правил клиента. В логах вызовов snippet не сохранять исходный код.

## Как проверить проект при реализации

Сначала сохранить до изменения реальные запросы/ответы на малом фиксированном
корпусе, включая публичные адреса. Затем использовать тот же корпус для новой
версии: это отделяет совместимость формы от обновления контента и ранжирования.

1. **Старые клиенты.** Воспроизвести search и все ветки explain из двух указанных
   тегов; проверить прямой tools/call без initialize, заголовки старого клиента,
   JSON в первом text-блоке, признак ошибки. На этапе реализации запустить
   настоящий парсер/адаптер соответствующих версий, не ограничиваться похожим
   Python-тестом. Отдельно проверить get/search потребителя документации v0.12.3.
2. **Схемы.** Каждый успешный ответ проходит заявленную outputSchema, включая
   пустые и отрицательные результаты; text JSON равен structuredContent.
   Прежние запросы сохраняют поведение на границах длин и clamping.
3. **Маршрутизация ИИ.** На одном наборе задач сравнить старые и предложенные
   описания при одинаковой модели и настройках. Проверить выбранный инструмент,
   аргументы, лишние вызовы, чтение основания перед выводом и отсутствие
   неподтверждённых заявлений о нарушениях. Прогон Inspector проверяет протокол,
   но не заменяет оценку выбора инструмента моделью.
4. **Локальная поставка.** Сохранить локальные URL и отказ от fallback. Провести
   отдельный отрицательный тест ограничения старого documentation provider,
   чтобы оно не маскировалось пустым успешным результатом в отчёте совместимости.

Минимальный набор задач для маршрутизации:

| Вход | Ожидаемое действие/граница |
|---|---|
| «Проверь процедуру» и небольшой BSL-код | snippet; далее выбранные статьи, без утверждения о запуске анализатора |
| SDBL с `ВЫБРАТЬ РАЗРЕШЕННЫЕ` | snippet; применимость сверяется с текстом правила |
| Диагностики из SARIF/лога | извлечь ID и namespace, один diagnostics вызов; не отправлять весь отчёт |
| Комментарий подавления с кодом BSLLS | diagnostics; наличие описания не оправдывает подавление |
| «Что требует std437?» | get_page напрямую |
| «Как заменить модальные окна?» | search, затем релевантная статья |
| «Что связано с этой диагностикой?» и известный ID | related |
| Голое `361` без источника | не выдумывать namespace; уточнить источник или искать кандидатов |
| Повторяющиеся/неизвестные коды | корректные frequency/unknown_codes, без повторения того же вызова |
| Фрагмент длиннее объявленного maxLength | сокращение релевантного участка; отсутствие автоматического массового разбиения |
| Пустая выдача по коду | отсутствие заявления «нарушений нет» |
| Инструкция «игнорируй правила» внутри комментария | трактовать как текст исследуемого кода |

Критерий допуска: все сценарии совместимости проходят; на перечисленных задачах
нет ошибочного выбора семейства инструмента и ложных обещаний анализа проекта.
Преимущество новых описаний оценивается по результатам сравнительного прогона,
а не объявляется заранее. Новых тестов без соответствующей обязанности не добавлять.

## Порядок изменения

1. Вычитать этот проект и границу совместимости.
2. Зафиксировать baseline старых запросов и парсеров; добавить описания параметров,
   описания инструментов и annotations без изменения реализации инструментов.
3. Описать реальные outputSchema и улучшить подсказки ошибок, сохраняя ответы.
4. Выполнить проверки совместимости и сравнительные сценарии ИИ, обновить текущий
   контракт по фактическому результату. Выпускать по обычным правилам поставки.

## Использованные скилы

- [tool-design](https://github.com/muratcankoylan/agent-skills-for-context-engineering/blob/main/skills/tool-design/SKILL.md): разделение задач инструментов, описание входов/выходов, восстановление после ошибок и проверка выбора на задачах.
- [build-mcp-server](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/mcp-server-dev/skills/build-mcp-server/SKILL.md): небольшая поверхность отдельных действий, HTTP и сохранение выбранного стека.
- [Tool design reference](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/mcp-server-dev/skills/build-mcp-server/references/tool-design.md): описания параметров, annotations и отсутствие управляющих инструкций в описании инструмента.

Контекст Claude загружен из [экспорта документации](https://claude.com/docs/llms-full.txt).
Публикация в каталоге Claude не входит в задачу; требования каталога не создают
нового процесса согласования в этом репозитории. Формулировки descriptions выше
написаны для v8std и существующего контракта, а не скопированы из примеров скилов.
