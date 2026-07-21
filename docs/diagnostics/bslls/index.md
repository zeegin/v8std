---
title: Диагностики BSL Language Server и стандарты
llms:
  ignore: true
---

# Диагностики BSL Language Server и стандарты

| Диагностика | Тип | Важность | Стандарты |
|---|---|---|---|
| [AllFunctionPathMustHaveReturn](AllFunctionPathMustHaveReturn.md) | Дефект кода | Важный | — |
| [AssignAliasFieldsInQuery](AssignAliasFieldsInQuery.md) | Дефект кода | Важный | [#std437, п. 2: Оформление текстов запросов](../../std/437.md#2)<br>[#std437, п. 2а: Оформление текстов запросов](../../std/437.md#2_1)<br>[#std437, п. 2б: Оформление текстов запросов](../../std/437.md#2_2) |
| [AssignToReadOnlyProperty](AssignToReadOnlyProperty.md) | Ошибка | Важный | — |
| [BadExceptionCategory](BadExceptionCategory.md) | Дефект кода | Информационный | — |
| [BadWords](BadWords.md) | Дефект кода | Важный | — |
| [BeginTransactionBeforeTryCatch](BeginTransactionBeforeTryCatch.md) | Ошибка | Важный | [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) |
| [CachedPublic](CachedPublic.md) | Дефект кода | Важный | [#std644, п. 3.6: Обеспечение совместимости библиотек](../../std/644.md#36) |
| [CanonicalSpellingKeywords](CanonicalSpellingKeywords.md) | Дефект кода | Информационный | [#std441, п. 1: Общие требования к построению конструкций встроенного языка](../../std/441.md#1) |
| [CodeAfterAsyncCall](CodeAfterAsyncCall.md) | Дефект кода | Важный | — |
| [CodeBlockBeforeSub](CodeBlockBeforeSub.md) | Ошибка | Блокирующий | [#std455, п. 1.1: Структура модуля](../../std/455.md#11) |
| [CodeOutOfRegion](CodeOutOfRegion.md) | Дефект кода | Информационный | [#std455, п. 1.3: Структура модуля](../../std/455.md#13) |
| [CognitiveComplexity](CognitiveComplexity.md) | Дефект кода | Критичный | — |
| [CommandModuleExportMethods](CommandModuleExportMethods.md) | Дефект кода | Информационный | [#std544: Ограничения на использование экспортных процедур и функций](../../std/544.md#std544) |
| [CommentedCode](CommentedCode.md) | Дефект кода | Незначительный | [#std456, п. 3: Тексты модулей](../../std/456.md#3) |
| [CommitTransactionOutsideTryCatch](CommitTransactionOutsideTryCatch.md) | Ошибка | Важный | [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) |
| [CommonModuleAssign](CommonModuleAssign.md) | Ошибка | Блокирующий | — |
| [CommonModuleInvalidType](CommonModuleInvalidType.md) | Ошибка | Важный | [#std469, п. 1.2: Правила создания общих модулей](../../std/469.md#12) |
| [CommonModuleMissingAPI](CommonModuleMissingAPI.md) | Дефект кода | Незначительный | [#std455, п. 1.4: Структура модуля](../../std/455.md#14) |
| [CommonModuleNameCached](CommonModuleNameCached.md) | Дефект кода | Важный | [#std469, п. 3.2.3: Правила создания общих модулей](../../std/469.md#323) |
| [CommonModuleNameClient](CommonModuleNameClient.md) | Дефект кода | Незначительный | [#std469, п. 2.3: Правила создания общих модулей](../../std/469.md#23) |
| [CommonModuleNameClientServer](CommonModuleNameClientServer.md) | Дефект кода | Важный | [#std469, п. 2.4: Правила создания общих модулей](../../std/469.md#24) |
| [CommonModuleNameFullAccess](CommonModuleNameFullAccess.md) | Потенциальная уязвимость | Важный | [#std469, п. 3.2.2: Правила создания общих модулей](../../std/469.md#322) |
| [CommonModuleNameGlobal](CommonModuleNameGlobal.md) | Дефект кода | Важный | [#std469, п. 3.2.1: Правила создания общих модулей](../../std/469.md#321) |
| [CommonModuleNameGlobalClient](CommonModuleNameGlobalClient.md) | Дефект кода | Важный | [#std469, п. 3.2.1: Правила создания общих модулей](../../std/469.md#321) |
| [CommonModuleNameServerCall](CommonModuleNameServerCall.md) | Дефект кода | Незначительный | [#std469, п. 2.2: Правила создания общих модулей](../../std/469.md#22) |
| [CommonModuleNameWords](CommonModuleNameWords.md) | Дефект кода | Информационный | [#std469, п. 3.1: Правила создания общих модулей](../../std/469.md#31) |
| [CommonModuleVariables](CommonModuleVariables.md) | Ошибка | Критичный | — |
| [CompareWithBoolean](CompareWithBoolean.md) | Дефект кода | Незначительный | [#std441, п. 4: Общие требования к построению конструкций встроенного языка](../../std/441.md#4) |
| [CompilationDirectiveLost](CompilationDirectiveLost.md) | Дефект кода | Важный | — |
| [CompilationDirectiveNeedLess](CompilationDirectiveNeedLess.md) | Дефект кода | Важный | [#std439, п. 1: Использование директив компиляции и инструкций препроцессора](../../std/439.md#1) |
| [ConsecutiveEmptyLines](ConsecutiveEmptyLines.md) | Дефект кода | Информационный | — |
| [CrazyMultilineString](CrazyMultilineString.md) | Дефект кода | Важный | — |
| [CreateQueryInCycle](CreateQueryInCycle.md) | Ошибка | Критичный | — |
| [CyclomaticComplexity](CyclomaticComplexity.md) | Дефект кода | Критичный | — |
| [DataExchangeLoading](DataExchangeLoading.md) | Ошибка | Критичный | [#std464, п. 2: Обработчик события ПередЗаписью](../../std/464.md#2)<br>[#std465, п. 2: Обработчик события ПриЗаписи](../../std/465.md#2)<br>[#std752, п. 2: Обработчик события ПередУдалением](../../std/752.md#2)<br>[#std773, п. 1: Использование признака ОбменДанными.Загрузка в обработчиках событий объекта](../../std/773.md#1) |
| [DeletingCollectionItem](DeletingCollectionItem.md) | Ошибка | Важный | — |
| [DenyIncompleteValues](DenyIncompleteValues.md) | Дефект кода | Важный | — |
| [DeprecatedAttributes8312](DeprecatedAttributes8312.md) | Дефект кода | Информационный | — |
| [DeprecatedCurrentDate](DeprecatedCurrentDate.md) | Ошибка | Важный | [#std643, п. 2.1: Работа в разных часовых поясах](../../std/643.md#21)<br>[#std643, п. 3.1: Работа в разных часовых поясах](../../std/643.md#31) |
| [DeprecatedFind](DeprecatedFind.md) | Дефект кода | Незначительный | — |
| [DeprecatedMessage](DeprecatedMessage.md) | Дефект кода | Незначительный | [#std418: Ограничение на использование метода Сообщить](../../std/418.md#std418) |
| [DeprecatedMethodCall](DeprecatedMethodCall.md) | Дефект кода | Незначительный | [#std453, п. 5.7: Описание процедур и функций](../../std/453.md#57) |
| [DeprecatedTypeManagedForm](DeprecatedTypeManagedForm.md) | Дефект кода | Информационный | — |
| [DisableSafeMode](DisableSafeMode.md) | Уязвимость | Важный | [#std669, п. 3.2: Ограничение на выполнение внешнего кода](../../std/669.md#32) |
| [DoubleNegatives](DoubleNegatives.md) | Дефект кода | Важный | — |
| [DuplicatedInsertionIntoCollection](DuplicatedInsertionIntoCollection.md) | Дефект кода | Важный | — |
| [DuplicateRegion](DuplicateRegion.md) | Дефект кода | Информационный | — |
| [DuplicateStringLiteral](DuplicateStringLiteral.md) | Дефект кода | Незначительный | — |
| [EmptyCodeBlock](EmptyCodeBlock.md) | Дефект кода | Важный | — |
| [EmptyRegion](EmptyRegion.md) | Дефект кода | Информационный | [#std455, п. 1.8: Структура модуля](../../std/455.md#18) |
| [EmptyStatement](EmptyStatement.md) | Дефект кода | Информационный | — |
| [EventHandlerInvalidSignature](EventHandlerInvalidSignature.md) | Ошибка | Важный | — |
| [EventHandlerOutsideEventRegion](EventHandlerOutsideEventRegion.md) | Дефект кода | Информационный | [#std455, п. 1.5: Структура модуля](../../std/455.md#15)<br>[#std455, п. 1.6: Структура модуля](../../std/455.md#16) |
| [ExcessiveAutoTestCheck](ExcessiveAutoTestCheck.md) | Дефект кода | Незначительный | [#std456, п. 3: Тексты модулей](../../std/456.md#3) |
| [ExecuteExternalCode](ExecuteExternalCode.md) | Уязвимость | Критичный | [#std770, п. 1: Ограничения на использование Выполнить и Вычислить на сервере](../../std/770.md#1) |
| [ExecuteExternalCodeInCommonModule](ExecuteExternalCodeInCommonModule.md) | Потенциальная уязвимость | Критичный | [#std770, п. 3: Ограничения на использование Выполнить и Вычислить на сервере](../../std/770.md#3) |
| [ExportVariables](ExportVariables.md) | Дефект кода | Важный | [#std639, п. 2.1: Использование переменных в программных модулях](../../std/639.md#21) |
| [ExternalAppStarting](ExternalAppStarting.md) | Потенциальная уязвимость | Важный | [#std774, п. 1: Безопасность запуска приложений](../../std/774.md#1) |
| [ExtraCommas](ExtraCommas.md) | Дефект кода | Важный | [#std640, п. 7: Параметры процедур и функций](../../std/640.md#7) |
| [FieldsFromJoinsWithoutIsNull](FieldsFromJoinsWithoutIsNull.md) | Ошибка | Критичный | — |
| [FileSystemAccess](FileSystemAccess.md) | Уязвимость | Важный | [#std542, п. 1: Доступ к файловой системе из кода конфигурации](../../std/542.md#1) |
| [ForbiddenMetadataName](ForbiddenMetadataName.md) | Ошибка | Блокирующий | [#std474, п. 2.5: Имя, синоним, комментарий](../../std/474.md#25) |
| [FormDataToValue](FormDataToValue.md) | Дефект кода | Информационный | [#std409, п. 1: Использование РеквизитФормыВЗначение и ДанныеФормыВЗначение](../../std/409.md#1) |
| [FullOuterJoinQuery](FullOuterJoinQuery.md) | Дефект кода | Важный | [#std435, п. 1.1: Ограничение на использование конструкции "ПОЛНОЕ ВНЕШНЕЕ СОЕДИНЕНИЕ" в запросах](../../std/435.md#11) |
| [FunctionNameStartsWithGet](FunctionNameStartsWithGet.md) | Дефект кода | Информационный | [#std647, п. 6.1: Имена процедур и функций](../../std/647.md#61) |
| [FunctionOutParameter](FunctionOutParameter.md) | Дефект кода | Важный | — |
| [FunctionReturnsSamePrimitive](FunctionReturnsSamePrimitive.md) | Ошибка | Важный | — |
| [FunctionShouldHaveReturn](FunctionShouldHaveReturn.md) | Ошибка | Важный | — |
| [GetFormMethod](GetFormMethod.md) | Ошибка | Важный | [#std404, п. 1: Открытие форм](../../std/404.md#1) |
| [GlobalContextMethodCollision8312](GlobalContextMethodCollision8312.md) | Ошибка | Блокирующий | — |
| [IdenticalExpressions](IdenticalExpressions.md) | Ошибка | Важный | — |
| [IfConditionComplexity](IfConditionComplexity.md) | Дефект кода | Незначительный | — |
| [IfElseDuplicatedCodeBlock](IfElseDuplicatedCodeBlock.md) | Дефект кода | Незначительный | — |
| [IfElseDuplicatedCondition](IfElseDuplicatedCondition.md) | Дефект кода | Важный | — |
| [IfElseIfEndsWithElse](IfElseIfEndsWithElse.md) | Дефект кода | Важный | — |
| [IncorrectLineBreak](IncorrectLineBreak.md) | Дефект кода | Информационный | [#std444, п. 6: Перенос выражений](../../std/444.md#6) |
| [IncorrectUseLikeInQuery](IncorrectUseLikeInQuery.md) | Ошибка | Важный | [#std726, п. 1: Особенности использования в запросах оператора ПОДОБНО](../../std/726.md#1) |
| [IncorrectUseOfStrTemplate](IncorrectUseOfStrTemplate.md) | Ошибка | Блокирующий | — |
| [InternetAccess](InternetAccess.md) | Уязвимость | Важный | — |
| [InvalidCharacterInFile](InvalidCharacterInFile.md) | Ошибка | Важный | [#std456, п. 1.2: Тексты модулей](../../std/456.md#12) |
| [IsInRoleMethod](IsInRoleMethod.md) | Дефект кода | Важный | [#std737, п. 3: Проверка прав доступа](../../std/737.md#3) |
| [JoinWithSubQuery](JoinWithSubQuery.md) | Дефект кода | Важный | [#std655, п. 1.1: Ограничения на соединения с вложенными запросами и виртуальными таблицами](../../std/655.md#11) |
| [JoinWithVirtualTable](JoinWithVirtualTable.md) | Дефект кода | Важный | [#std655, п. 2: Ограничения на соединения с вложенными запросами и виртуальными таблицами](../../std/655.md#2) |
| [LatinAndCyrillicSymbolInWord](LatinAndCyrillicSymbolInWord.md) | Дефект кода | Незначительный | — |
| [LineLength](LineLength.md) | Дефект кода | Незначительный | [#std456, п. 6: Тексты модулей](../../std/456.md#6) |
| [LogicalOrInJoinQuerySection](LogicalOrInJoinQuerySection.md) | Дефект кода | Важный | [#std658, п. 2.1: Эффективные условия запросов](../../std/658.md#21) |
| [LogicalOrInTheWhereSectionOfQuery](LogicalOrInTheWhereSectionOfQuery.md) | Дефект кода | Важный | [#std658, п. 2.1: Эффективные условия запросов](../../std/658.md#21) |
| [MagicDate](MagicDate.md) | Дефект кода | Незначительный | — |
| [MagicNumber](MagicNumber.md) | Дефект кода | Незначительный | — |
| [MetadataObjectNameLength](MetadataObjectNameLength.md) | Ошибка | Важный | [#std474, п. 2.3: Имя, синоним, комментарий](../../std/474.md#23) |
| [MethodSize](MethodSize.md) | Дефект кода | Важный | — |
| [MissedRequiredParameter](MissedRequiredParameter.md) | Ошибка | Важный | [#std640, п. 7: Параметры процедур и функций](../../std/640.md#7) |
| [MissingCodeTryCatchEx](MissingCodeTryCatchEx.md) | Ошибка | Важный | [#std499, п. 3.2: Перехват исключений в коде](../../std/499.md#32) |
| [MissingCommonModuleMethod](MissingCommonModuleMethod.md) | Ошибка | Блокирующий | — |
| [MissingEventSubscriptionHandler](MissingEventSubscriptionHandler.md) | Ошибка | Блокирующий | — |
| [MissingParameterDescription](MissingParameterDescription.md) | Дефект кода | Важный | [#std453, п. 5.2: Описание процедур и функций](../../std/453.md#52) |
| [MissingReturnedValueDescription](MissingReturnedValueDescription.md) | Дефект кода | Важный | [#std453, п. 5.3: Описание процедур и функций](../../std/453.md#53) |
| [MissingSpace](MissingSpace.md) | Дефект кода | Информационный | — |
| [MissingTemporaryFileDeletion](MissingTemporaryFileDeletion.md) | Ошибка | Важный | [#std542, п. 4: Доступ к файловой системе из кода конфигурации](../../std/542.md#4) |
| [MissingTempStorageDeletion](MissingTempStorageDeletion.md) | Дефект кода | Критичный | [#std487, п. 8.3: Минимизация количества серверных вызовов и трафика](../../std/487.md#83)<br>[#std642, п. 3.1: Длительные операции на сервере](../../std/642.md#31) |
| [MissingVariablesDescription](MissingVariablesDescription.md) | Дефект кода | Незначительный | [#std455, п. 2.2: Структура модуля](../../std/455.md#22) |
| [MultilineStringInQuery](MultilineStringInQuery.md) | Ошибка | Критичный | — |
| [MultilingualStringHasAllDeclaredLanguages](MultilingualStringHasAllDeclaredLanguages.md) | Ошибка | Незначительный | — |
| [MultilingualStringUsingWithTemplate](MultilingualStringUsingWithTemplate.md) | Ошибка | Важный | — |
| [NestedConstructorsInStructureDeclaration](NestedConstructorsInStructureDeclaration.md) | Дефект кода | Незначительный | — |
| [NestedFunctionInParameters](NestedFunctionInParameters.md) | Дефект кода | Незначительный | [#std640, п. 6.1: Параметры процедур и функций](../../std/640.md#61) |
| [NestedStatements](NestedStatements.md) | Дефект кода | Критичный | — |
| [NestedTernaryOperator](NestedTernaryOperator.md) | Дефект кода | Важный | — |
| [NonExportMethodsInApiRegion](NonExportMethodsInApiRegion.md) | Дефект кода | Важный | [#std455, п. 1.4: Структура модуля](../../std/455.md#14) |
| [NonStandardRegion](NonStandardRegion.md) | Дефект кода | Информационный | [#std455, п. 1.4: Структура модуля](../../std/455.md#14)<br>[#std455, п. 1.5: Структура модуля](../../std/455.md#15)<br>[#std455, п. 1.6: Структура модуля](../../std/455.md#16)<br>[#std455, п. 1.7: Структура модуля](../../std/455.md#17) |
| [NumberOfOptionalParams](NumberOfOptionalParams.md) | Дефект кода | Незначительный | [#std640, п. 5: Параметры процедур и функций](../../std/640.md#5) |
| [NumberOfParams](NumberOfParams.md) | Дефект кода | Незначительный | [#std640, п. 5: Параметры процедур и функций](../../std/640.md#5) |
| [NumberOfValuesInStructureConstructor](NumberOfValuesInStructureConstructor.md) | Дефект кода | Незначительный | [#std693, п. 1: Использование объектов типа Структура](../../std/693.md#1) |
| [OneStatementPerLine](OneStatementPerLine.md) | Дефект кода | Незначительный | [#std456, п. 4: Тексты модулей](../../std/456.md#4) |
| [OrderOfParams](OrderOfParams.md) | Дефект кода | Важный | [#std640, п. 3: Параметры процедур и функций](../../std/640.md#3) |
| [OrdinaryAppSupport](OrdinaryAppSupport.md) | Дефект кода | Важный | [#std467, п. 1.4: Общие требования к конфигурации](../../std/467.md#14) |
| [OSUsersMethod](OSUsersMethod.md) | Потенциальная уязвимость | Критичный | — |
| [PairingBrokenTransaction](PairingBrokenTransaction.md) | Ошибка | Важный | [#std783, п. 1.2: Транзакции: правила использования](../../std/783.md#12) |
| [ParseError](ParseError.md) | Ошибка | Критичный | [#std439, п. 3: Использование директив компиляции и инструкций препроцессора](../../std/439.md#3) |
| [PrivilegedModuleMethodCall](PrivilegedModuleMethodCall.md) | Потенциальная уязвимость | Важный | — |
| [ProcedureReturnsValue](ProcedureReturnsValue.md) | Ошибка | Блокирующий | — |
| [ProtectedModule](ProtectedModule.md) | Дефект кода | Важный | — |
| [PublicMethodsDescription](PublicMethodsDescription.md) | Дефект кода | Информационный | [#std453, п. 2: Описание процедур и функций](../../std/453.md#2) |
| [QueryNestedFieldsByDot](QueryNestedFieldsByDot.md) | Дефект кода | Важный | [#std654, п. 1.2: Разыменование ссылочных полей составного типа в языке запросов](../../std/654.md#12) |
| [QueryParseError](QueryParseError.md) | Дефект кода | Важный | [#std437, п. 6.2: Оформление текстов запросов](../../std/437.md#62) |
| [QueryToMissingMetadata](QueryToMissingMetadata.md) | Ошибка | Блокирующий | — |
| [RedundantAccessToObject](RedundantAccessToObject.md) | Дефект кода | Информационный | — |
| [RefOveruse](RefOveruse.md) | Дефект кода | Важный | [#std654, п. 1.1: Разыменование ссылочных полей составного типа в языке запросов](../../std/654.md#11) |
| [ReservedParameterNames](ReservedParameterNames.md) | Дефект кода | Важный | — |
| [RewriteMethodParameter](RewriteMethodParameter.md) | Дефект кода | Важный | — |
| [SameMetadataObjectAndChildNames](SameMetadataObjectAndChildNames.md) | Ошибка | Критичный | [#std474, п. 2.4: Имя, синоним, комментарий](../../std/474.md#24) |
| [ScheduledJobHandler](ScheduledJobHandler.md) | Ошибка | Критичный | — |
| [SelectTopWithoutOrderBy](SelectTopWithoutOrderBy.md) | Дефект кода | Важный | [#std412, п. 1.1: Упорядочивание результатов запроса](../../std/412.md#11) |
| [SelfAssign](SelfAssign.md) | Ошибка | Важный | — |
| [SelfInsertion](SelfInsertion.md) | Ошибка | Важный | — |
| [SemicolonPresence](SemicolonPresence.md) | Дефект кода | Незначительный | — |
| [ServerCallsInFormEvents](ServerCallsInFormEvents.md) | Ошибка | Критичный | — |
| [ServerSideExportFormMethod](ServerSideExportFormMethod.md) | Ошибка | Блокирующий | — |
| [SetPermissionsForNewObjects](SetPermissionsForNewObjects.md) | Уязвимость | Критичный | [#std532, п. 2: Установка прав для новых объектов и полей объектов](../../std/532.md#2) |
| [SetPrivilegedMode](SetPrivilegedMode.md) | Потенциальная уязвимость | Важный | [#std485, п. 3: Использование привилегированного режима](../../std/485.md#3)<br>[#std678, п. 1.3: Безопасность прикладного программного интерфейса сервера](../../std/678.md#13) |
| [SeveralCompilerDirectives](SeveralCompilerDirectives.md) | Ошибка | Критичный | — |
| [SpaceAtStartComment](SpaceAtStartComment.md) | Дефект кода | Информационный | [#std456, п. 7.3: Тексты модулей](../../std/456.md#73) |
| [StyleElementConstructors](StyleElementConstructors.md) | Ошибка | Незначительный | [#std667, п. 1: Элементы стиля](../../std/667.md#1) |
| [TempFilesDir](TempFilesDir.md) | Дефект кода | Важный | [#std542, п. 1: Доступ к файловой системе из кода конфигурации](../../std/542.md#1_1) |
| [TernaryOperatorUsage](TernaryOperatorUsage.md) | Дефект кода | Незначительный | — |
| [ThisObjectAssign](ThisObjectAssign.md) | Ошибка | Блокирующий | — |
| [TimeoutsInExternalResources](TimeoutsInExternalResources.md) | Ошибка | Критичный | [#std748, п. 1: Таймауты при работе с внешними ресурсами](../../std/748.md#1) |
| [TooManyReturns](TooManyReturns.md) | Дефект кода | Незначительный | — |
| [TransferringParametersBetweenClientAndServer](TransferringParametersBetweenClientAndServer.md) | Дефект кода | Важный | — |
| [TryNumber](TryNumber.md) | Дефект кода | Важный | [#std499, п. 1: Перехват исключений в коде](../../std/499.md#1) |
| [Typo](Typo.md) | Дефект кода | Информационный | — |
| [UnaryPlusInConcatenation](UnaryPlusInConcatenation.md) | Ошибка | Блокирующий | — |
| [UnavailableMemberCall](UnavailableMemberCall.md) | Ошибка | Важный | — |
| [UnionAll](UnionAll.md) | Дефект кода | Незначительный | [#std434: Использование ключевых слов "ОБЪЕДИНИТЬ" и "ОБЪЕДИНИТЬ ВСЕ" в запросах](../../std/434.md#std434) |
| [UnknownMember](UnknownMember.md) | Ошибка | Важный | — |
| [UnknownPreprocessorSymbol](UnknownPreprocessorSymbol.md) | Ошибка | Критичный | — |
| [UnreachableCode](UnreachableCode.md) | Ошибка | Незначительный | — |
| [UnsafeFindByCode](UnsafeFindByCode.md) | Дефект кода | Важный | — |
| [UnsafeSafeModeMethodCall](UnsafeSafeModeMethodCall.md) | Ошибка | Блокирующий | — |
| [UnusedLocalMethod](UnusedLocalMethod.md) | Дефект кода | Важный | [#std456, п. 2: Тексты модулей](../../std/456.md#2) |
| [UnusedLocalVariable](UnusedLocalVariable.md) | Дефект кода | Важный | — |
| [UnusedParameters](UnusedParameters.md) | Дефект кода | Важный | — |
| [UsageWriteLogEvent](UsageWriteLogEvent.md) | Дефект кода | Информационный | [#std498, п. 2.2: Использование Журнала регистрации](../../std/498.md#22)<br>[#std498, п. 2.3: Использование Журнала регистрации](../../std/498.md#23)<br>[#std499, п. 2.2: Перехват исключений в коде](../../std/499.md#22) |
| [UseLessForEach](UseLessForEach.md) | Ошибка | Критичный | — |
| [UselessTernaryOperator](UselessTernaryOperator.md) | Дефект кода | Информационный | — |
| [UseSystemInformation](UseSystemInformation.md) | Потенциальная уязвимость | Критичный | — |
| [UsingCancelParameter](UsingCancelParameter.md) | Дефект кода | Важный | [#std686, п. 1: Работа с параметром "Отказ" в обработчиках событий](../../std/686.md#1) |
| [UsingExternalCodeTools](UsingExternalCodeTools.md) | Потенциальная уязвимость | Критичный | [#std669, п. 1: Ограничение на выполнение внешнего кода](../../std/669.md#1) |
| [UsingFindElementByString](UsingFindElementByString.md) | Дефект кода | Важный | — |
| [UsingGoto](UsingGoto.md) | Дефект кода | Критичный | [#std547, п. 1: Ограничение на использование оператора Перейти](../../std/547.md#1) |
| [UsingHardcodeNetworkAddress](UsingHardcodeNetworkAddress.md) | Уязвимость | Критичный | — |
| [UsingHardcodePath](UsingHardcodePath.md) | Ошибка | Критичный | — |
| [UsingHardcodeSecretInformation](UsingHardcodeSecretInformation.md) | Уязвимость | Критичный | [#std740, п. 3.2: Безопасное хранение паролей](../../std/740.md#32) |
| [UsingLikeInQuery](UsingLikeInQuery.md) | Ошибка | Важный | — |
| [UsingModalWindows](UsingModalWindows.md) | Дефект кода | Важный | [#std703, п. 1: Ограничение на использование модальных окон и синхронных вызовов](../../std/703.md#1) |
| [UsingObjectNotAvailableUnix](UsingObjectNotAvailableUnix.md) | Ошибка | Критичный | — |
| [UsingServiceTag](UsingServiceTag.md) | Дефект кода | Информационный | — |
| [UsingSynchronousCalls](UsingSynchronousCalls.md) | Дефект кода | Важный | [#std703, п. 5: Ограничение на использование модальных окон и синхронных вызовов](../../std/703.md#5) |
| [UsingThisForm](UsingThisForm.md) | Дефект кода | Незначительный | — |
| [VirtualTableCallWithoutParameters](VirtualTableCallWithoutParameters.md) | Ошибка | Важный | [#std657, п. 1: Обращения к виртуальным таблицам](../../std/657.md#1) |
| [WrongDataPathForFormElements](WrongDataPathForFormElements.md) | Ошибка | Критичный | [#std467, п. 1.3: Общие требования к конфигурации](../../std/467.md#13) |
| [WrongHttpServiceHandler](WrongHttpServiceHandler.md) | Ошибка | Критичный | — |
| [WrongUseFunctionProceedWithCall](WrongUseFunctionProceedWithCall.md) | Ошибка | Блокирующий | — |
| [WrongUseOfRollbackTransactionMethod](WrongUseOfRollbackTransactionMethod.md) | Ошибка | Критичный | [#std783, п. 1.3: Транзакции: правила использования](../../std/783.md#13) |
| [WrongWebServiceHandler](WrongWebServiceHandler.md) | Ошибка | Критичный | — |
| [YoLetterUsage](YoLetterUsage.md) | Дефект кода | Информационный | [#std456, п. 1.1: Тексты модулей](../../std/456.md#11) |
