---
title: Facade
---

# Фасад (`Facade`)

`Facade` дает простой внешний вход к сложной подсистеме.

## Опора на ООП

`Facade` опирается прежде всего на [инкапсуляцию](../../principles/index.md): сложная координация нескольких модулей и объектов прячется за компактным внешним API.

## Что показывает пример на 1С

- `CommonModules.SalesOrderFacade` собирает в одной точке создание документа, заполнение, контроль остатков и проведение.
- Клиентский код вызывает один понятный метод вместо серии обращений к разным подсистемам.
- При этом фасад не отменяет внутренние сервисы, а только упрощает типовой сценарий работы с ними.

## Пример

=== "DataProcessors.Application"
    ```bsl
    SalesOrder = CommonModules.SalesOrderFacade.CreateAndPost(Partner, Items);
    ```

=== "CommonModules.SalesOrderFacade"
    ```bsl
    Function CreateAndPost(Partner, Items) Export

        SalesOrder = Documents.SalesOrder.CreateDocument();

        SalesOrderFilling.FillHeader(SalesOrder, Partner);
        SalesOrderFilling.FillItems(SalesOrder, Items);

        StockControl.CheckAvailability(SalesOrder);

        SalesOrder.Write(DocumentWriteMode.Posting);
        Return SalesOrder;

    EndFunction
    ```

=== "CommonModules.StockControl"
    ```bsl
    Procedure CheckAvailability(SalesOrder) Export

        // Check stock balances.

    EndProcedure
    ```

## Где полезен в 1С

- для типовых сценариев работы с документами, обменами и расчетами;
- когда внутренняя подсистема состоит из нескольких сервисов и объектов;
- когда внешнему коду нужен короткий и устойчивый API.

## Когда паттерн лишний

- если фасад просто переименовывает один вызов;
- если под фасадом начинает скапливаться вся бизнес-логика системы;
- если разным клиентам нужны слишком разные сценарии и один вход их только запутывает.
