---
title: Диагностики EDT v8-code-style и стандарты
llms:
  ignore: true
---

# Диагностики EDT v8-code-style и стандарты

| Диагностика | Категория | Стандарты |
|---|---|---|
| [begin-transaction](begin-transaction.md) | `bsl` | [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) |
| [bsl-canonical-pragma](bsl-canonical-pragma.md) | `bsl` | [#std441, п. 1: Общие требования к построению конструкций встроенного языка](../../std/441.md#1) |
| [bsl-nstr-string-literal-format](bsl-nstr-string-literal-format.md) | `bsl` | [#std761, п. 1: Интерфейсные тексты в коде: требования по локализации](../../std/761.md#1)<br>[#std761, п. 4: Интерфейсные тексты в коде: требования по локализации](../../std/761.md#4)<br>[#std761, п. 8: Интерфейсные тексты в коде: требования по локализации](../../std/761.md#8) |
| [bsl-variable-name-invalid](bsl-variable-name-invalid.md) | `bsl` | [#std454, п. 3: Правила образования имен переменных](../../std/454.md#3) |
| [change-and-validate-instead-of-around](change-and-validate-instead-of-around.md) | `bsl` | — |
| [code-after-async-call](code-after-async-call.md) | `bsl` | — |
| [commit-transaction](commit-transaction.md) | `bsl` | [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) |
| [common-module-missing-api](common-module-missing-api.md) | `bsl` | — |
| [common-module-name-cached](common-module-name-cached.md) | `md` | [#std469, п. 3.2.3: Правила создания общих модулей](../../std/469.md#323) |
| [common-module-name-client](common-module-name-client.md) | `md` | [#std469, п. 2.3: Правила создания общих модулей](../../std/469.md#23) |
| [common-module-name-client-cached](common-module-name-client-cached.md) | `md` | [#std469, п. 3.2.3: Правила создания общих модулей](../../std/469.md#323) |
| [common-module-name-client-server](common-module-name-client-server.md) | `md` | [#std469, п. 2.4: Правила создания общих модулей](../../std/469.md#24) |
| [common-module-name-full-access](common-module-name-full-access.md) | `md` | [#std469, п. 3.2.2: Правила создания общих модулей](../../std/469.md#322) |
| [common-module-name-global](common-module-name-global.md) | `md` | [#std469, п. 3.2.1: Правила создания общих модулей](../../std/469.md#321) |
| [common-module-name-global-client](common-module-name-global-client.md) | `md` | [#std469, п. 3.2.1: Правила создания общих модулей](../../std/469.md#321) |
| [common-module-name-server-call](common-module-name-server-call.md) | `md` | [#std469, п. 2.2: Правила создания общих модулей](../../std/469.md#22) |
| [common-module-name-server-call-cached](common-module-name-server-call-cached.md) | `md` | [#std469, п. 3.2.3: Правила создания общих модулей](../../std/469.md#323) |
| [common-module-named-self-reference](common-module-named-self-reference.md) | `bsl` | — |
| [common-module-server-call](common-module-server-call.md) | `bsl` | [#std679, п. 1: Ограничение на установку признака «Вызов сервера» у общих модулей](../../std/679.md#1) |
| [common-module-type](common-module-type.md) | `md` | — |
| [configuration-data-lock-mode](configuration-data-lock-mode.md) | `md` | [#std460: Использование управляемого режима блокировки](../../std/460.md#std460) |
| [constructor-function-return-section](constructor-function-return-section.md) | `bsl` | — |
| [data-composition-conditional-appearance-use](data-composition-conditional-appearance-use.md) | `form` | [#std710, п. 2.1: Условное оформление в формах](../../std/710.md#21) |
| [data-composition-variant-name-default](data-composition-variant-name-default.md) | `form` | [#std674, п. 4: Заголовок отчета](../../std/674.md#4) |
| [data-exchange-load](data-exchange-load.md) | `bsl` | [#std464, п. 2: Обработчик события ПередЗаписью](../../std/464.md#2)<br>[#std465, п. 2: Обработчик события ПриЗаписи](../../std/465.md#2)<br>[#std752, п. 2: Обработчик события ПередУдалением](../../std/752.md#2)<br>[#std773, п. 1: Использование признака ОбменДанными.Загрузка в обработчиках событий объекта](../../std/773.md#1) |
| [db-object-anyref-type](db-object-anyref-type.md) | `md` | [#std728, п. 2.1: Ограничения на использование реквизитов составного типа](../../std/728.md#21) |
| [db-object-max-number-length](db-object-max-number-length.md) | `md` | [#std467, п. 1.2: Общие требования к конфигурации](../../std/467.md#12) |
| [db-object-ref-non-ref-type](db-object-ref-non-ref-type.md) | `md` | [#std728, п. 1.1: Ограничения на использование реквизитов составного типа](../../std/728.md#11) |
| [deprecated-procedure-outside-deprecated-region](deprecated-procedure-outside-deprecated-region.md) | `bsl` | [#std644, п. 3.1: Обеспечение совместимости библиотек](../../std/644.md#31) |
| [doc-comment-collection-item-type](doc-comment-collection-item-type.md) | `bsl` | — |
| [doc-comment-complex-type-with-link](doc-comment-complex-type-with-link.md) | `bsl` | — |
| [doc-comment-description-ends-on-dot](doc-comment-description-ends-on-dot.md) | `bsl` | — |
| [doc-comment-export-function-return-section](doc-comment-export-function-return-section.md) | `bsl` | — |
| [doc-comment-export-procedure-description-section](doc-comment-export-procedure-description-section.md) | `bsl` | [#std453, п. 2: Описание процедур и функций](../../std/453.md#2) |
| [doc-comment-field-in-description-suggestion](doc-comment-field-in-description-suggestion.md) | `bsl` | — |
| [doc-comment-field-name](doc-comment-field-name.md) | `bsl` | — |
| [doc-comment-field-type](doc-comment-field-type.md) | `bsl` | — |
| [doc-comment-field-type-strict](doc-comment-field-type-strict.md) | `bsl` | — |
| [doc-comment-parameter-in-description-suggestion](doc-comment-parameter-in-description-suggestion.md) | `bsl` | — |
| [doc-comment-parameter-section](doc-comment-parameter-section.md) | `bsl` | — |
| [doc-comment-procedure-return-section](doc-comment-procedure-return-section.md) | `bsl` | — |
| [doc-comment-redundant-parameter-section](doc-comment-redundant-parameter-section.md) | `bsl` | — |
| [doc-comment-ref-link](doc-comment-ref-link.md) | `bsl` | — |
| [doc-comment-return-section-type](doc-comment-return-section-type.md) | `bsl` | — |
| [doc-comment-type](doc-comment-type.md) | `bsl` | — |
| [doc-comment-use-minus](doc-comment-use-minus.md) | `bsl` | — |
| [document-post-in-privileged-mode](document-post-in-privileged-mode.md) | `md` | [#std689, п. 1.7: Настройка ролей и прав доступа](../../std/689.md#17) |
| [dont-use-modality-mode](dont-use-modality-mode.md) | `bsl` | [#std703, п. 1: Ограничение на использование модальных окон и синхронных вызовов](../../std/703.md#1) |
| [dynamic-access-method-not-found](dynamic-access-method-not-found.md) | `bsl` | — |
| [empty-except-statement](empty-except-statement.md) | `bsl` | [#std499, п. 3.2: Перехват исключений в коде](../../std/499.md#32) |
| [event-handler-boolean-param](event-handler-boolean-param.md) | `bsl` | [#std686, п. 1: Работа с параметром "Отказ" в обработчиках событий](../../std/686.md#1) |
| [export-method-in-command-form-module](export-method-in-command-form-module.md) | `bsl` | [#std544: Ограничения на использование экспортных процедур и функций](../../std/544.md#std544)<br>[#std630, п. 1.1: Правила создания модулей форм](../../std/630.md#11) |
| [export-procedure-missing-comment](export-procedure-missing-comment.md) | `bsl` | [#std453, п. 2: Описание процедур и функций](../../std/453.md#2) |
| [extension-md-object-prefix](extension-md-object-prefix.md) | `md` | — |
| [extension-method-prefix](extension-method-prefix.md) | `bsl` | — |
| [extension-method-visible-mode](extension-method-visible-mode.md) | `bsl` | — |
| [extension-variable-prefix](extension-variable-prefix.md) | `bsl` | — |
| [form-commands-single-action-handler](form-commands-single-action-handler.md) | `form` | [#std455, п. 2.4.3: Структура модуля](../../std/455.md#243) |
| [form-dynamic-list-item-title](form-dynamic-list-item-title.md) | `form` | [#std765, п. 4: Элементы форм: требования по локализации](../../std/765.md#4) |
| [form-item-visible-settings-by-roles](form-item-visible-settings-by-roles.md) | `form` | [#std737, п. 1: Проверка прав доступа](../../std/737.md#1) |
| [form-items-single-event-handler](form-items-single-event-handler.md) | `form` | [#std455, п. 2.4.3: Структура модуля](../../std/455.md#243) |
| [form-list-field-ref-not-added](form-list-field-ref-not-added.md) | `form` | [#std702, п. 1: Реквизит Ссылка и признак "Использовать всегда" в динамических списках объектов](../../std/702.md#1) |
| [form-list-ref-use-always-flag-disabled](form-list-ref-use-always-flag-disabled.md) | `form` | [#std702, п. 1: Реквизит Ссылка и признак "Использовать всегда" в динамических списках объектов](../../std/702.md#1) |
| [form-list-ref-user-visibility-enabled](form-list-ref-user-visibility-enabled.md) | `form` | [#std702, п. 1: Реквизит Ссылка и признак "Использовать всегда" в динамических списках объектов](../../std/702.md#1) |
| [form-module-missing-pragma](form-module-missing-pragma.md) | `bsl` | [#std439, п. 1: Использование директив компиляции и инструкций препроцессора](../../std/439.md#1)<br>[#std467, п. 1.1: Общие требования к конфигурации](../../std/467.md#11) |
| [form-module-pragma](form-module-pragma.md) | `bsl` | [#std439, п. 1: Использование директив компиляции и инструкций препроцессора](../../std/439.md#1) |
| [form-self-reference](form-self-reference.md) | `bsl` | — |
| [function-return-value-type](function-return-value-type.md) | `bsl` | — |
| [functional-option-privileged-get-mode](functional-option-privileged-get-mode.md) | `md` | [#std689, п. 1.8: Настройка ролей и прав доступа](../../std/689.md#18) |
| [input-field-list-choice-mode](input-field-list-choice-mode.md) | `form` | [#std765, п. 5: Элементы форм: требования по локализации](../../std/765.md#5) |
| [invocation-form-event-handler](invocation-form-event-handler.md) | `bsl` | [#std455, п. 2.4.3: Структура модуля](../../std/455.md#243) |
| [invocation-parameter-type-intersect](invocation-parameter-type-intersect.md) | `bsl` | — |
| [link-part-comment-space](link-part-comment-space.md) | `bsl` | — |
| [lock-out-of-try](lock-out-of-try.md) | `bsl` | [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) |
| [manager-module-named-self-reference](manager-module-named-self-reference.md) | `bsl` | — |
| [md-list-object-presentation](md-list-object-presentation.md) | `md` | [#std468, п. 4: Пользовательские представления объектов](../../std/468.md#4) |
| [md-object-attribute-comment-incorrect-type](md-object-attribute-comment-incorrect-type.md) | `md` | [#std531, п. 1: Реквизит «Комментарий» у документов](../../std/531.md#1) |
| [md-object-attribute-comment-not-exist](md-object-attribute-comment-not-exist.md) | `md` | [#std531, п. 1: Реквизит «Комментарий» у документов](../../std/531.md#1) |
| [md-standard-attribute-synonym-empty](md-standard-attribute-synonym-empty.md) | `md` | [#std474, п. 1.5: Имя, синоним, комментарий](../../std/474.md#15) |
| [mdo-name-length](mdo-name-length.md) | `md` | [#std474, п. 2.3: Имя, синоним, комментарий](../../std/474.md#23) |
| [mdo-ru-name-unallowed-letter](mdo-ru-name-unallowed-letter.md) | `md` | [#std474, п. 4: Имя, синоним, комментарий](../../std/474.md#4) |
| [mdo-scheduled-job-description](mdo-scheduled-job-description.md) | `md` | [#std767, п. 1: Регламентные задания: требования по локализации](../../std/767.md#1) |
| [method-isinrole-role-exist](method-isinrole-role-exist.md) | `bsl` | — |
| [method-optional-parameter-before-required](method-optional-parameter-before-required.md) | `bsl` | [#std640, п. 4: Параметры процедур и функций](../../std/640.md#4) |
| [method-param-value-type](method-param-value-type.md) | `bsl` | — |
| [method-semicolon-extra](method-semicolon-extra.md) | `bsl` | — |
| [method-too-many-params](method-too-many-params.md) | `bsl` | [#std640, п. 5: Параметры процедур и функций](../../std/640.md#5) |
| [missing-temporary-file-deletion](missing-temporary-file-deletion.md) | `bsl` | [#std542, п. 4: Доступ к файловой системе из кода конфигурации](../../std/542.md#4) |
| [module-accessibility-at-client](module-accessibility-at-client.md) | `bsl` | [#std680, п. 2: Поддержка толстого клиента, управляемое приложение, клиент-сервер](../../std/680.md#2) |
| [module-attachable-event-handler-name](module-attachable-event-handler-name.md) | `bsl` | [#std492, п. 1: Обработчики событий модуля формы, подключаемые из кода](../../std/492.md#1) |
| [module-consecutive-blank-lines](module-consecutive-blank-lines.md) | `bsl` | — |
| [module-empty-method](module-empty-method.md) | `bsl` | — |
| [module-region-empty](module-region-empty.md) | `bsl` | [#std455, п. 1.8: Структура модуля](../../std/455.md#18) |
| [module-self-reference](module-self-reference.md) | `bsl` | — |
| [module-structure-event-regions](module-structure-event-regions.md) | `bsl` | [#std455, п. 1.5: Структура модуля](../../std/455.md#15) |
| [module-structure-form-event-regions](module-structure-form-event-regions.md) | `bsl` | [#std455, п. 1.6: Структура модуля](../../std/455.md#16) |
| [module-structure-init-code-in-region](module-structure-init-code-in-region.md) | `bsl` | [#std455, п. 1.1: Структура модуля](../../std/455.md#11) |
| [module-structure-method-in-regions](module-structure-method-in-regions.md) | `bsl` | [#std455, п. 1.1: Структура модуля](../../std/455.md#11) |
| [module-structure-top-region](module-structure-top-region.md) | `bsl` | [#std455, п. 1.1: Структура модуля](../../std/455.md#11) |
| [module-structure-var-in-region](module-structure-var-in-region.md) | `bsl` | [#std455, п. 1.1: Структура модуля](../../std/455.md#11) |
| [module-undefined-function](module-undefined-function.md) | `bsl` | — |
| [module-undefined-method](module-undefined-method.md) | `bsl` | — |
| [module-undefined-variable](module-undefined-variable.md) | `bsl` | — |
| [module-unused-local-variable](module-unused-local-variable.md) | `bsl` | — |
| [module-unused-method](module-unused-method.md) | `bsl` | — |
| [new-color](new-color.md) | `bsl` | [#std667, п. 1: Элементы стиля](../../std/667.md#1) |
| [new-font](new-font.md) | `bsl` | [#std667, п. 1: Элементы стиля](../../std/667.md#1) |
| [not-support-goto-operator-webclient](not-support-goto-operator-webclient.md) | `bsl` | [#std547, п. 2: Ограничение на использование оператора Перейти](../../std/547.md#2) |
| [notify-description-to-server-procedure](notify-description-to-server-procedure.md) | `bsl` | — |
| [object-module-export-variable](object-module-export-variable.md) | `bsl` | [#std639, п. 2.1: Использование переменных в программных модулях](../../std/639.md#21) |
| [optional-form-parameter-access](optional-form-parameter-access.md) | `bsl` | [#std741, п. 3: Открытие параметризированных форм](../../std/741.md#3) |
| [property-return-type](property-return-type.md) | `bsl` | — |
| [public-method-caching](public-method-caching.md) | `bsl` | [#std644, п. 3.6: Обеспечение совместимости библиотек](../../std/644.md#36) |
| [ql-camel-case-string-literal](ql-camel-case-string-literal.md) | `ql` | — |
| [ql-cast-to-max-number](ql-cast-to-max-number.md) | `ql` | — |
| [ql-constants-in-binary-operation](ql-constants-in-binary-operation.md) | `ql` | [#std726, п. 1: Особенности использования в запросах оператора ПОДОБНО](../../std/726.md#1) |
| [ql-join-to-sub-query](ql-join-to-sub-query.md) | `ql` | [#std655, п. 1.1: Ограничения на соединения с вложенными запросами и виртуальными таблицами](../../std/655.md#11) |
| [ql-like-expression-with-field](ql-like-expression-with-field.md) | `ql` | [#std467, п. 1.2: Общие требования к конфигурации](../../std/467.md#12) |
| [ql-temp-table-index](ql-temp-table-index.md) | `ql` | [#std777, п. 3: Использование временных таблиц](../../std/777.md#3) |
| [ql-using-for-update](ql-using-for-update.md) | `ql` | [#std460: Использование управляемого режима блокировки](../../std/460.md#std460) |
| [ql-virtual-table-filters](ql-virtual-table-filters.md) | `ql` | [#std657, п. 1: Обращения к виртуальным таблицам](../../std/657.md#1) |
| [query-in-loop](query-in-loop.md) | `bsl` | [#std436, п. 1: Многократное выполнение однотипных запросов](../../std/436.md#1) |
| [reading-attribute-from-database](reading-attribute-from-database.md) | `bsl` | [#std496: Чтение отдельных реквизитов объекта из базы данных](../../std/496.md#std496) |
| [redundant-export-method](redundant-export-method.md) | `bsl` | [#std467, п. 2.2: Общие требования к конфигурации](../../std/467.md#22) |
| [register-resource-precision](register-resource-precision.md) | `md` | — |
| [restriction-execute-external-code](restriction-execute-external-code.md) | `bsl` | [#std669, п. 7: Ограничение на выполнение внешнего кода](../../std/669.md#7) |
| [restriction-execute-external-component-code](restriction-execute-external-component-code.md) | `bsl` | [#std669, п. 6.4: Ограничение на выполнение внешнего кода](../../std/669.md#64) |
| [right-active-users](right-active-users.md) | `right` | [#std488, п. 3.1: Стандартные роли](../../std/488.md#31) |
| [right-administration](right-administration.md) | `right` | [#std488, п. 3.1: Стандартные роли](../../std/488.md#31) |
| [right-all-functions-mode](right-all-functions-mode.md) | `right` | — |
| [right-configuration-extensions-administration](right-configuration-extensions-administration.md) | `right` | [#std488, п. 3.1: Стандартные роли](../../std/488.md#31) |
| [right-data-administration](right-data-administration.md) | `right` | [#std488, п. 3.1: Стандартные роли](../../std/488.md#31) |
| [right-delete](right-delete.md) | `right` | [#std488, п. 5: Стандартные роли](../../std/488.md#5) |
| [right-exclusive-mode](right-exclusive-mode.md) | `right` | [#std488, п. 2.1: Стандартные роли](../../std/488.md#21) |
| [right-interactive-clear-deletion-mark-predefined-data](right-interactive-clear-deletion-mark-predefined-data.md) | `right` | [#std488, п. 5: Стандартные роли](../../std/488.md#5) |
| [right-interactive-delete](right-interactive-delete.md) | `right` | [#std488, п. 5: Стандартные роли](../../std/488.md#5) |
| [right-interactive-delete-marked-predefined-data](right-interactive-delete-marked-predefined-data.md) | `right` | [#std488, п. 5: Стандартные роли](../../std/488.md#5) |
| [right-interactive-delete-predefined-data](right-interactive-delete-predefined-data.md) | `right` | [#std488, п. 5: Стандартные роли](../../std/488.md#5) |
| [right-interactive-open-external-data-processors](right-interactive-open-external-data-processors.md) | `right` | [#std488, п. 2.3: Стандартные роли](../../std/488.md#23) |
| [right-interactive-open-external-reports](right-interactive-open-external-reports.md) | `right` | [#std488, п. 2.3: Стандартные роли](../../std/488.md#23) |
| [right-interactive-set-deletion-mark-predefined-data](right-interactive-set-deletion-mark-predefined-data.md) | `right` | [#std488, п. 5: Стандартные роли](../../std/488.md#5) |
| [right-output-to-printer-file-clipboard](right-output-to-printer-file-clipboard.md) | `right` | [#std488, п. 3.2: Стандартные роли](../../std/488.md#32) |
| [right-save-user-data](right-save-user-data.md) | `right` | [#std488, п. 3.12: Стандартные роли](../../std/488.md#312) |
| [right-start-automation](right-start-automation.md) | `right` | [#std488, п. 3.3: Стандартные роли](../../std/488.md#33) |
| [right-start-external-connection](right-start-external-connection.md) | `right` | [#std488, п. 3.5: Стандартные роли](../../std/488.md#35) |
| [right-start-thick-client](right-start-thick-client.md) | `right` | [#std488, п. 3.6: Стандартные роли](../../std/488.md#36) |
| [right-start-thin-client](right-start-thin-client.md) | `right` | [#std488, п. 3.7: Стандартные роли](../../std/488.md#37) |
| [right-start-web-client](right-start-web-client.md) | `right` | [#std488, п. 3.4: Стандартные роли](../../std/488.md#34) |
| [right-update-database-configuration](right-update-database-configuration.md) | `right` | [#std488, п. 3.9: Стандартные роли](../../std/488.md#39) |
| [right-view-event-log](right-view-event-log.md) | `right` | [#std488, п. 3.10: Стандартные роли](../../std/488.md#310) |
| [role-right-has-rls](role-right-has-rls.md) | `right` | — |
| [rollback-transaction](rollback-transaction.md) | `bsl` | [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) |
| [scheduled-job-periodicity-too-short](scheduled-job-periodicity-too-short.md) | `md` | [#std402: Настройка расписания регламентных заданий](../../std/402.md#std402) |
| [secure-password-storage](secure-password-storage.md) | `bsl` | [#std740, п. 3.3: Безопасное хранение паролей](../../std/740.md#33) |
| [security-software-call](security-software-call.md) | `bsl` | [#std775, п. 1: Безопасность программного обеспечения, вызываемого через открытые интерфейсы](../../std/775.md#1) |
| [self-assign](self-assign.md) | `bsl` | — |
| [semicolon-missing](semicolon-missing.md) | `bsl` | — |
| [server-execution-safe-mode](server-execution-safe-mode.md) | `bsl` | [#std770, п. 2: Ограничения на использование Выполнить и Вычислить на сервере](../../std/770.md#2) |
| [statement-type-change](statement-type-change.md) | `bsl` | — |
| [string-literal-type-annotation-invalid-place](string-literal-type-annotation-invalid-place.md) | `bsl` | — |
| [structure-constructor-too-many-keys](structure-constructor-too-many-keys.md) | `bsl` | [#std640, п. 6.2: Параметры процедур и функций](../../std/640.md#62)<br>[#std693, п. 1: Использование объектов типа Структура](../../std/693.md#1) |
| [structure-constructor-value-type](structure-constructor-value-type.md) | `bsl` | — |
| [structure-key-modification](structure-key-modification.md) | `bsl` | [#std693, п. 4.1: Использование объектов типа Структура](../../std/693.md#41) |
| [subsystem-synonym-too-long](subsystem-synonym-too-long.md) | `md` | [#std712, п. 2.1: Панель разделов](../../std/712.md#21) |
| [typed-value-adding-to-untyped-collection](typed-value-adding-to-untyped-collection.md) | `bsl` | — |
| [unknown-form-parameter-access](unknown-form-parameter-access.md) | `bsl` | [#std741, п. 3: Открытие параметризированных форм](../../std/741.md#3) |
| [unsafe-password-ib-storage](unsafe-password-ib-storage.md) | `md` | [#std740, п. 2: Безопасное хранение паролей](../../std/740.md#2) |
| [use-goto-operator](use-goto-operator.md) | `bsl` | [#std547, п. 1: Ограничение на использование оператора Перейти](../../std/547.md#1) |
| [use-non-recommended-method](use-non-recommended-method.md) | `bsl` | [#std404, п. 1: Открытие форм](../../std/404.md#1)<br>[#std418: Ограничение на использование метода Сообщить](../../std/418.md#std418)<br>[#std643, п. 2.1: Работа в разных часовых поясах](../../std/643.md#21) |
| [using-form-data-to-value](using-form-data-to-value.md) | `bsl` | [#std409, п. 1: Использование РеквизитФормыВЗначение и ДанныеФормыВЗначение](../../std/409.md#1) |
| [using-isinrole](using-isinrole.md) | `bsl` | [#std737, п. 3: Проверка прав доступа](../../std/737.md#3) |
| [variable-value-type](variable-value-type.md) | `bsl` | — |
