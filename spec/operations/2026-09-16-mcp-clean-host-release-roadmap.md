# MCP: чистая переустановка и публикация в Docker Catalog

Общая последовательность выпуска в режиме чистой установки без восстановления
прежней ОС. Этот документ не содержит параметров конкретной инфраструктуры,
сведений о доступах и разрешений на фактические действия. Они хранятся вне
репозитория в закрытой операторской записи. Наличие runbook не означает,
что его этапы выполнены или что остановка уже разрешена.

Пакет: [продуктовый design](../designs/2026-09-16-mcp-clean-host-installation-design.md),
[policy design](../designs/2026-09-16-mcp-clean-host-release-policy-design.md).
Эта последовательность применяется к чистой установке, а не к миграции
существующего deployment с сохранением предшественника.

## Входные проверки

- Проверенный исходный SHA и реализованный initial-install: legacy bootstrap
  не подходит для пустой машины.
- Фактические branch/environment protections и раздельные переключатели
  image/corpus publication и runtime deployment.
- Изолированные service credentials и работоспособность provenance verifier;
  личный token разработчика не используется как сервисный доступ.
- Точные опубликованные image/corpus identities и пригодный off-host handoff.
- Отдельная операторская запись о target и дисках, правах на действия и готовности
  к остановке; перед необратимой операцией цель повторно сверяется у провайдера.

## 1. Реализовать clean-host установку

После просмотра письменного пакета создать implementation plan через writing-plans:
root-only initial-install/recovery; повторяемое provisioning и handoff; process-v3
и tests; комплект подготовки Catalog. Работать в отдельной ветке основного checkout.
Старые deploy/bootstrap regressions и новые negative/fault cases обязательны.

Локальная приёмка: semantic impact и CLI impact, architecture merge-ready,
fitness, strict build, затем полный suite. Build и suite не запускать одновременно.
После gates — локальный merge. Этот этап не останавливает MCP, не переустанавливает
ОС, не меняет тариф и не отправляет Catalog PR.

## 2. Подготовить и опубликовать поставку до остановки

Зафиксировать проверенный main SHA; получить явное разрешение на push main
и нужные внешние settings/credentials, если их нет. Проверить отдельный GitHub
service credential, existing publisher SSH и pinned host key. Разрешить только
image/corpus publication; runtime deployment остаётся выключенным.

CI публикует multiarch MCP/site images, SBOM/provenance и snapshot. На ещё живом
host проверяет archive извне; лишь затем Pages получает соответствующий manifest.
Проверяются anonymous pull точного digest, default/public source, локальный сайт
и warm cache. Точные image index/platform/config/corpus identities записываются
в evidence. Это не нагрузочная репетиция production migration.

Сохранить новую поставку вне target host: сами OCI-артефакты либо проверенный
локальный OCI export, signed snapshot/manifest, verification material,
publication journals/reference state/sequence. Secrets отдельно, права0700/0600.
Перед финальным handoff остановить новые publication jobs и дождаться завершения
in-flight, сохранив подтверждения. Пустой current-index или потеря reference
acknowledgement не разрешают удалить ранее опубликованный archive.

В старом сервере не хранится единственная копия чего-либо, нужного новой установке.
Полный образ старой ОС и проверка восстановления legacy не выполняются.

## 3. Подготовить Docker Catalog entry

Заполнить `deploy/docker-catalog/server.yaml` фактическим digest/source SHA,
описанием, five-tools metadata, SITE_URL, snippet setting и persistent volume.
Согласовать source schema с актуальным docker/mcp-registry.

На опубликованном образе выполнить реальный Gateway/Toolkit lifecycle:
initialize/tools/list, все пять tools, серия вызовов без контейнера на каждый
вызов, повторные сессии, warm/offline с тем же cache и заданный локальный сайт.
Проверить фактический launcher profile; не добавлять несуществующие readonly/
cap-drop поля, не подменять per-entry longLived глобальным флагом Gateway.

Результат — проверенная заявка для локального контейнера. Она ещё не отправлена
и не объявляется записью официального каталога. Если выявлен новый blocker,
он разбирается здесь; рабочий production не ждёт произвольного upstream review.

## 4. Получить разрешение на остановку — обязательный gate

Предъявить пользователю target, проверенный SHA/digests и готовность новой
поставки. Сообщить: будут временно недоступны публичный MCP и загрузка индексов;
сайт на Pages не переустанавливается. Полный возврат старой машины не предусмотрен.
Не обещать двухчасовой или иной срок как измеренную гарантию.

Ждать отдельного сообщения пользователя, что предупреждение опубликовано и
можно начинать. До него нельзя stop/restart MCP/nginx, wipe/reinstall или
переключать public runtime. Уведомление потребителей выполняется ответственным
оператором; согласованный канал не фиксируется в публичном runbook.

## 5. Переустановить и запустить

После подтверждения и сверки exact target остановить legacy MCP. Сохранить
последний хвост private usage history вне машины, не резервную копию ОС.
Переустановить выбранную VM через провайдера, не удалять её и не заказывать новый
сервер/тариф без отдельного согласования. Перед операцией проверить текущие
условия сохранения IP у провайдера; не обещать его сохранение по предположению.

Проверить доступ через доверенную консоль, новую SSH identity, сеть/DNS и время.
Развернуть ОС/пакеты и root-owned конфигурацию из подготовленного SHA. Отдельно
подготовить TLS и renewal публичного MCP. Не возвращать сторонние vhosts,
legacy Python service, public monitoring, старые общие доступы или лишние агенты.
Сначала maintenance/static store и проверенный handoff, затем first runtime.

Восстановить изолированный publisher и GitHub verifier credential, перепроверить
restricted commands и обновить CI known-hosts после доверенной сверки. Runtime
CI не включать. Выполнить initial-install с точными проверенными identities;
принять первый контейнер только после public smoke и durable journal.

При ошибке исправлять новую установку: maintenance и ограниченная новая попытка
после cleanup. Нет попыток поднять старую ОС и нет фиктивного rollback success.
Недостаток RAM/disk или доступа требует сообщения пользователю; тариф не меняется
автоматически и health не объявляется успешным без фактической готовности.

## 6. Принять production и автоматизацию

Проверить TLS, initialize, пять tools, отказ Resources/SSE, статические hashes,
SITE_URL/links, cache и отсутствие network I/O в warm tool call, private logging,
410 public monitoring. Проверить recovery нового принятого контейнера после
перезапуска, не обещая восстановления удалённого старого сервера.

На работающей машине снять реальные показатели без разрушительного стресс-теста.
Проверить content-only update без runtime restart. Runtime automation принимается
отдельно: old/new capacity, bounded rollout, post-switch smoke и rollback должны
работать. До этого runtime CI остаётся выключенным; image/corpus delivery может
работать независимо. Обнаруженное ограничение сообщается, а не скрывается.
100000 подключений остаются недоказанной целью.

## 7. Отправить и довести Docker Catalog

После готовности сервиса и проверки entry создать PR в docker/mcp-registry.
Пройти checks/review, отвечать по делу и вносить необходимые изменения. Не менять
runtime architecture ради замечания без impact/design review. Проверить фактическое
появление записи после принятия и установку из официального Toolkit Catalog.

Отмечать раздельно: submitted, review/CI, merged, visible, installed-and-tested.
До последних двух результатов не говорить «опубликовано в каталоге». Review
сроки Docker не включены в длительность простоя public MCP. Для каждой версии
Catalog и production используют ту же сборку; versions могут временно различаться.

После подтверждения локального/production пути закрыть PR33 с благодарностью
и точным описанием альтернативы. Issue32 не закрывать автоматически. Итоговые
ссылки: public MCP, registry image, инструкция локальной установки, Catalog entry
и PR. Ни один из этих внешних результатов не получен одной записью этого плана.
