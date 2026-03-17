---
title: Separation of Concerns
---

# Separation of Concerns

`Separation of Concerns` требует разделять разные типы задач по отдельным слоям и контекстам.

## Что означает в 1С

В 1С это обычно означает, что стоит различать:

- форму и UI;
- orchestration сценария;
- доменную логику;
- интеграцию;
- инфраструктурные детали.

Если все это смешано в одном модуле формы или в одном общем модуле, код быстро перестает быть управляемым.

## Пример на 1С

=== "CommonForms.SalesOrderForm"
    ```bsl
    &AtClient
    Procedure PostCommand(Command)

        CommonModules.SalesOrderController.Post(Object.Ref);

    EndProcedure
    ```

=== "CommonModules.SalesOrderController"
    ```bsl
    Procedure Post(SalesOrderRef) Export

        SalesOrder = SalesOrderRef.GetObject();
        SalesOrderValidation.CheckBeforePosting(SalesOrder);
        SalesOrder.Write(DocumentWriteMode.Posting);

    EndProcedure
    ```

Здесь форма отвечает за UI, контроллер за orchestration, а объект документа и сервисы проверки — за свою часть доменной логики.

## Когда полезен

- в формах с большим количеством действий;
- в интеграционных сценариях;
- в больших прикладных модулях, где все перемешалось.

## Когда применяют неправильно

- когда разделение слоев становится формальным и бесполезным;
- когда между слоями появляется слишком много пустых прокладок;
- когда из-за "чистоты" теряется понимание сквозного сценария.
