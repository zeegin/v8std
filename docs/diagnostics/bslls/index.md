# Диагностики BSL Language Server и стандарты

В таблице приведены диагностики BSL Language Server, у которых в блоке `Источники` есть ссылка на стандарт `v8std`.

Всего диагностик: **78**.

| Диагностика | Тип | Важность | Стандарты |
|---|---|---|---|
| [AssignAliasFieldsInQuery](AssignAliasFieldsInQuery.md) | Дефект кода | Важный | [#std437: Оформление текстов запросов](../../std/437.md) |
| [CachedPublic](CachedPublic.md) | Дефект кода | Важный | [#std644: Обеспечение совместимости библиотек](../../std/644.md) |
| [CanonicalSpellingKeywords](CanonicalSpellingKeywords.md) | Дефект кода | Информационный | [#std441: Общие требования к построению конструкций встроенного языка](../../std/441.md) |
| [CodeOutOfRegion](CodeOutOfRegion.md) | Дефект кода | Информационный | [#std455: Структура модуля](../../std/455.md) |
| [CommonModuleInvalidType](CommonModuleInvalidType.md) | Ошибка | Важный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleMissingAPI](CommonModuleMissingAPI.md) | Дефект кода | Незначительный | [#std455: Структура модуля](../../std/455.md) |
| [CommonModuleNameCached](CommonModuleNameCached.md) | Дефект кода | Важный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleNameClient](CommonModuleNameClient.md) | Дефект кода | Незначительный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleNameClientServer](CommonModuleNameClientServer.md) | Дефект кода | Важный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleNameFullAccess](CommonModuleNameFullAccess.md) | Потенциальная уязвимость | Важный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleNameGlobal](CommonModuleNameGlobal.md) | Дефект кода | Важный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleNameGlobalClient](CommonModuleNameGlobalClient.md) | Дефект кода | Важный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleNameServerCall](CommonModuleNameServerCall.md) | Дефект кода | Незначительный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CommonModuleNameWords](CommonModuleNameWords.md) | Дефект кода | Информационный | [#std469: Правила создания общих модулей](../../std/469.md) |
| [CompilationDirectiveNeedLess](CompilationDirectiveNeedLess.md) | Дефект кода | Важный | [#std439: Использование директив компиляции и инструкций препроцессора](../../std/439.md) |
| [DataExchangeLoading](DataExchangeLoading.md) | Ошибка | Критичный | [#std464: Обработчик события ПередЗаписью](../../std/464.md)<br>[#std465: Обработчик события ПриЗаписи](../../std/465.md)<br>[#std752: Обработчик события ПередУдалением](../../std/752.md)<br>[#std773: Использование признака ОбменДанными.Загрузка в обработчиках событий объекта](../../std/773.md) |
| [DeprecatedMessage](DeprecatedMessage.md) | Дефект кода | Незначительный | [#std418: Ограничение на использование метода Сообщить](../../std/418.md) |
| [DisableSafeMode](DisableSafeMode.md) | Уязвимость | Важный | [#std770: Ограничения на использование Выполнить и Вычислить на сервере](../../std/770.md) |
| [DuplicateRegion](DuplicateRegion.md) | Дефект кода | Информационный | [#std455: Структура модуля](../../std/455.md) |
| [EmptyRegion](EmptyRegion.md) | Дефект кода | Информационный | [#std455: Структура модуля](../../std/455.md) |
| [ExcessiveAutoTestCheck](ExcessiveAutoTestCheck.md) | Дефект кода | Незначительный | [#std456: Тексты модулей](../../std/456.md) |
| [ExecuteExternalCode](ExecuteExternalCode.md) | Уязвимость | Критичный | [#std770: Ограничения на использование Выполнить и Вычислить на сервере](../../std/770.md) |
| [ExecuteExternalCodeInCommonModule](ExecuteExternalCodeInCommonModule.md) | Потенциальная уязвимость | Критичный | [#std770: Ограничения на использование Выполнить и Вычислить на сервере](../../std/770.md) |
| [ExportVariables](ExportVariables.md) | Дефект кода | Важный | [#std639: Использование переменных в программных модулях](../../std/639.md) |
| [ExtraCommas](ExtraCommas.md) | Дефект кода | Важный | [#std640: Параметры процедур и функций](../../std/640.md) |
| [FileSystemAccess](FileSystemAccess.md) | Уязвимость | Важный | [#std542: Доступ к файловой системе из кода конфигурации](../../std/542.md)<br>[#std774: Безопасность запуска приложений](../../std/774.md) |
| [ForbiddenMetadataName](ForbiddenMetadataName.md) | Ошибка | Блокирующий | [#std474: Имя, синоним, комментарий](../../std/474.md) |
| [FormDataToValue](FormDataToValue.md) | Дефект кода | Информационный | [#std409: Использование РеквизитФормыВЗначение и ДанныеФормыВЗначение](../../std/409.md) |
| [FullOuterJoinQuery](FullOuterJoinQuery.md) | Дефект кода | Важный | [#std435: Ограничение на использование конструкции "ПОЛНОЕ ВНЕШНЕЕ СОЕДИНЕНИЕ" в запросах](../../std/435.md) |
| [FunctionNameStartsWithGet](FunctionNameStartsWithGet.md) | Дефект кода | Информационный | [#std647: Имена процедур и функций](../../std/647.md) |
| [IncorrectLineBreak](IncorrectLineBreak.md) | Дефект кода | Информационный | [#std444: Перенос выражений](../../std/444.md) |
| [InvalidCharacterInFile](InvalidCharacterInFile.md) | Ошибка | Важный | [#std456: Тексты модулей](../../std/456.md) |
| [IsInRoleMethod](IsInRoleMethod.md) | Дефект кода | Важный | [#std737: Проверка прав доступа](../../std/737.md) |
| [JoinWithSubQuery](JoinWithSubQuery.md) | Дефект кода | Важный | [#std655: Ограничения на соединения с вложенными запросами и виртуальными таблицами](../../std/655.md) |
| [JoinWithVirtualTable](JoinWithVirtualTable.md) | Дефект кода | Важный | [#std655: Ограничения на соединения с вложенными запросами и виртуальными таблицами](../../std/655.md) |
| [LineLength](LineLength.md) | Дефект кода | Незначительный | [#std456: Тексты модулей](../../std/456.md) |
| [MetadataObjectNameLength](MetadataObjectNameLength.md) | Ошибка | Важный | [#std474: Имя, синоним, комментарий](../../std/474.md) |
| [MissedRequiredParameter](MissedRequiredParameter.md) | Ошибка | Важный | [#std640: Параметры процедур и функций](../../std/640.md) |
| [MissingCodeTryCatchEx](MissingCodeTryCatchEx.md) | Ошибка | Важный | [#std499: Перехват исключений в коде](../../std/499.md) |
| [MissingParameterDescription](MissingParameterDescription.md) | Дефект кода | Важный | [#std453: Описание процедур и функций](../../std/453.md) |
| [MissingReturnedValueDescription](MissingReturnedValueDescription.md) | Дефект кода | Важный | [#std453: Описание процедур и функций](../../std/453.md) |
| [MissingTempStorageDeletion](MissingTempStorageDeletion.md) | Дефект кода | Критичный | [#std487: Минимизация количества серверных вызовов и трафика](../../std/487.md)<br>[#std642: Длительные операции на сервере](../../std/642.md) |
| [MissingTemporaryFileDeletion](MissingTemporaryFileDeletion.md) | Ошибка | Важный | [#std542: Доступ к файловой системе из кода конфигурации](../../std/542.md) |
| [MissingVariablesDescription](MissingVariablesDescription.md) | Дефект кода | Незначительный | [#std455: Структура модуля](../../std/455.md) |
| [NestedFunctionInParameters](NestedFunctionInParameters.md) | Дефект кода | Незначительный | [#std640: Параметры процедур и функций](../../std/640.md) |
| [NonExportMethodsInApiRegion](NonExportMethodsInApiRegion.md) | Дефект кода | Важный | [#std455: Структура модуля](../../std/455.md) |
| [NonStandardRegion](NonStandardRegion.md) | Дефект кода | Информационный | [#std455: Структура модуля](../../std/455.md) |
| [NumberOfOptionalParams](NumberOfOptionalParams.md) | Дефект кода | Незначительный | [#std640: Параметры процедур и функций](../../std/640.md) |
| [NumberOfParams](NumberOfParams.md) | Дефект кода | Незначительный | [#std640: Параметры процедур и функций](../../std/640.md) |
| [NumberOfValuesInStructureConstructor](NumberOfValuesInStructureConstructor.md) | Дефект кода | Незначительный | [#std693: Использование объектов типа Структура](../../std/693.md) |
| [OneStatementPerLine](OneStatementPerLine.md) | Дефект кода | Незначительный | [#std456: Тексты модулей](../../std/456.md) |
| [OrderOfParams](OrderOfParams.md) | Дефект кода | Важный | [#std640: Параметры процедур и функций](../../std/640.md) |
| [OrdinaryAppSupport](OrdinaryAppSupport.md) | Дефект кода | Важный | [#std467: Общие требования к конфигурации](../../std/467.md) |
| [PairingBrokenTransaction](PairingBrokenTransaction.md) | Ошибка | Важный | [#std783: Транзакции: правила использования](../../std/783.md) |
| [ParseError](ParseError.md) | Ошибка | Критичный | [#std439: Использование директив компиляции и инструкций препроцессора](../../std/439.md) |
| [PublicMethodsDescription](PublicMethodsDescription.md) | Дефект кода | Информационный | [#std453: Описание процедур и функций](../../std/453.md) |
| [QueryParseError](QueryParseError.md) | Дефект кода | Важный | [#std437: Оформление текстов запросов](../../std/437.md) |
| [ReservedParameterNames](ReservedParameterNames.md) | Дефект кода | Важный | [#std454: Правила образования имен переменных](../../std/454.md) |
| [SameMetadataObjectAndChildNames](SameMetadataObjectAndChildNames.md) | Ошибка | Критичный | [#std474: Имя, синоним, комментарий](../../std/474.md) |
| [SelectTopWithoutOrderBy](SelectTopWithoutOrderBy.md) | Дефект кода | Важный | [#std412: Упорядочивание результатов запроса](../../std/412.md) |
| [SetPrivilegedMode](SetPrivilegedMode.md) | Потенциальная уязвимость | Важный | [#std678: Безопасность прикладного программного интерфейса сервера](../../std/678.md) |
| [SpaceAtStartComment](SpaceAtStartComment.md) | Дефект кода | Информационный | [#std456: Тексты модулей](../../std/456.md) |
| [StyleElementConstructors](StyleElementConstructors.md) | Ошибка | Незначительный | [#std667: Элементы стиля](../../std/667.md) |
| [TempFilesDir](TempFilesDir.md) | Дефект кода | Важный | [#std542: Доступ к файловой системе из кода конфигурации](../../std/542.md) |
| [TimeoutsInExternalResources](TimeoutsInExternalResources.md) | Ошибка | Критичный | [#std748: Таймауты при работе с внешними ресурсами](../../std/748.md) |
| [TryNumber](TryNumber.md) | Дефект кода | Важный | [#std499: Перехват исключений в коде](../../std/499.md) |
| [UnionAll](UnionAll.md) | Дефект кода | Незначительный | [#std434: Использование ключевых слов "ОБЪЕДИНИТЬ" и "ОБЪЕДИНИТЬ ВСЕ" в запросах](../../std/434.md) |
| [UnsafeFindByCode](UnsafeFindByCode.md) | Дефект кода | Важный | [#std456: Тексты модулей](../../std/456.md) |
| [UnusedLocalMethod](UnusedLocalMethod.md) | Дефект кода | Важный | [#std456: Тексты модулей](../../std/456.md) |
| [UsageWriteLogEvent](UsageWriteLogEvent.md) | Дефект кода | Информационный | [#std498: Использование Журнала регистрации](../../std/498.md)<br>[#std499: Перехват исключений в коде](../../std/499.md) |
| [UsingCancelParameter](UsingCancelParameter.md) | Дефект кода | Важный | [#std686: Работа с параметром "Отказ" в обработчиках событий](../../std/686.md) |
| [UsingExternalCodeTools](UsingExternalCodeTools.md) | Потенциальная уязвимость | Критичный | [#std669: Ограничение на выполнение внешнего кода](../../std/669.md) |
| [UsingHardcodeSecretInformation](UsingHardcodeSecretInformation.md) | Уязвимость | Критичный | [#std740: Безопасное хранение паролей](../../std/740.md) |
| [UsingLikeInQuery](UsingLikeInQuery.md) | Ошибка | Важный | [#std726: Особенности использования в запросах оператора ПОДОБНО](../../std/726.md) |
| [VirtualTableCallWithoutParameters](VirtualTableCallWithoutParameters.md) | Ошибка | Важный | [#std657: Обращения к виртуальным таблицам](../../std/657.md)<br>[#std733: Эффективное обращение к виртуальной таблице «Остатки»](../../std/733.md) |
| [WrongDataPathForFormElements](WrongDataPathForFormElements.md) | Ошибка | Критичный | [#std467: Общие требования к конфигурации](../../std/467.md) |
| [WrongUseOfRollbackTransactionMethod](WrongUseOfRollbackTransactionMethod.md) | Ошибка | Критичный | [#std783: Транзакции: правила использования](../../std/783.md) |
| [YoLetterUsage](YoLetterUsage.md) | Дефект кода | Информационный | [#std456: Тексты модулей](../../std/456.md) |
