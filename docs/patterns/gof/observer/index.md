---
title: Observer
---

# Наблюдатель (`Observer`)

`Observer` позволяет издателю уведомлять подписчиков об изменениях, не зная деталей их реакции.

## Опора на ООП

`Observer` опирается на [интерфейсы и полиморфизм](../../principles/index.md): издатель работает с общим контрактом подписчика, а конкретные реакции распределены по разным наблюдателям. Инкапсуляция при этом удерживает слабую связанность между сторонами.

## Что показывает пример на 1С

- `DataProcessors.EventManager` хранит подписчиков в `Map`, умеет `Subscribe()`, `Unsubscribe()` и `NotifySubscribers(Data)`.
- `DataProcessors.Subject` выполняет свою логику и затем вызывает `EventManager.NotifySubscribers("Success")`.
- `Documents.SalesOrder` и `Catalogs.Partner` реализуют метод `Update(Data)` и могут выступать подписчиками.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Subject = DataProcessors.Subject.Create();
    SalesOrder = Documents.SalesOrder.CreateDocument();
    Partner = Catalogs.Partner.CreateItem();

    Subject.EventManager.Subscribe(SalesOrder);
    Subject.EventManager.Subscribe(Partner);

    Subject.BusinessLogic();
    ```

=== "DataProcessors.EventManager"
    ```bsl
    Var Listeners;

    Procedure Subscribe(Subscriber) Export

        Listeners.Insert(Subscriber, True);

    EndProcedure

    Procedure Unsubscribe(Subscriber) Export

        Listeners.Delete(Subscriber);

    EndProcedure

    Procedure NotifySubscrbers(Data) Export

        For Each Listener In Listeners Do
            Listener.Update(Data);
        EndDo;

    EndProcedure

    Listeners = New Map;
    ```

=== "DataProcessors.Subject"
    ```bsl
    Var EventManager Export;

    #Region Public

    Function BusinessLogic() Export

        // Some logic

        EventManager.NotifySubscribers("Success");

    EndFunction

    #EndRegion

    EventManager = DataProcessors.EventManager.Create();
    ```

=== "Documents.SalesOrder"
    ```bsl
    Procedure Update(Data) Export

        Message("Sales order received event: " + Data);

    EndProcedure
    ```

=== "Catalogs.Partner"
    ```bsl
    Procedure Update(Data) Export

        Message("Partner received event: " + Data);

    EndProcedure
    ```

## Где полезен в 1С

- для реакций на доменные события;
- для отделения публикации события от действий подписчиков;
- для уведомлений, синхронизации витрин, логирования и вспомогательных процессов.

## Когда паттерн лишний

- если получатель всегда один и известен заранее;
- если цепочка подписчиков скрывает важную бизнес-логику;
- если нет дисциплины в управлении подписками и жизненным циклом объектов.

## Источник примера

- [zeegin/DesignPatterns: Observer](https://github.com/zeegin/DesignPatterns/tree/master/Observer)
