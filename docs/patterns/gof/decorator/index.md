---
title: Decorator
---

# Декоратор (`Decorator`)

`Decorator` добавляет объекту новое поведение через обертку, не меняя исходную реализацию.

## Опора на ООП

`Decorator` опирается на [интерфейсы, композицию и полиморфизм](../../principles/index.md): декоратор реализует тот же контракт, что и оборачиваемый компонент, и делегирует ему базовую работу, добавляя свой слой поведения.

## Что показывает пример на 1С

- `CommonModules.HttpSender` реализует базовую отправку запроса.
- `LoggingSenderDecorator` и `RetrySenderDecorator` оборачивают отправителя и добавляют логирование и повторные попытки.
- Клиент собирает нужную цепочку поведения без изменения исходного отправителя.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Sender = CommonModules.HttpSender;

    SenderWithLog = DataProcessors.LoggingSenderDecorator.Create();
    SenderWithLog.Init(Sender);

    SenderWithRetry = DataProcessors.RetrySenderDecorator.Create();
    SenderWithRetry.Init(SenderWithLog);

    Response = SenderWithRetry.Send(Request);
    ```

=== "CommonModules.HttpSender"
    ```bsl
    Function Send(Request) Export

        Return Request.Body;

    EndFunction
    ```

=== "DataProcessors.LoggingSenderDecorator"
    ```bsl
    Var Component;

    #Region Public

    Procedure Init(Component_) Export

        Component = Component_;

    EndProcedure

    Function Send(Request) Export

        WriteLogEvent("Integration", EventLogLevel.Information, , , "Sending request");
        Return Component.Send(Request);

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.RetrySenderDecorator"
    ```bsl
    Var Component;

    #Region Public

    Procedure Init(Component_) Export

        Component = Component_;

    EndProcedure

    Function Send(Request) Export

        For Counter = 1 To 3 Do
            Try
                Return Component.Send(Request);
            Except
            EndTry;
        EndDo;

        Raise "Request failed";

    EndFunction

    #EndRegion
    ```

## Близость к Proxy

`Decorator` очень похож на [Proxy](../proxy/index.md), потому что оба паттерна строятся как обертка вокруг компонента с тем же контрактом.

Из-за этого их легко спутать:

- и там, и там есть внутренний компонент;
- и там, и там вызов проходит через дополнительный слой;
- и клиент часто не видит разницы по сигнатуре методов.

Но смысл различается.

- `Decorator` наращивает поведение;
- `Proxy` контролирует доступ, создание или способ обращения к объекту.

Поэтому для 1С полезно разделять их по намерению:

- если слой добавляет логирование, ретраи, метрики или кэш вокруг вызова, это обычно `Decorator`;
- если слой проверяет права, скрывает удаленный вызов или лениво создает тяжелый объект, это обычно `Proxy`.

## Где полезен в 1С

- для логирования, кэширования, ретраев и профилирования вокруг сервиса;
- для постепенного наращивания технического поведения без переписывания базовой логики;
- когда один и тот же компонент нужно оборачивать разными комбинациями технических слоев.

## Когда паттерн лишний

- если поведение проще явно вызвать рядом;
- если оберток становится слишком много и цепочка трудно читается;
- если декоратор начинает менять бизнес-смысл исходного компонента.
