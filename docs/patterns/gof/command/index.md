---
title: Command
---

# Команда (`Command`)

`Command` превращает действие в отдельный объект или значение, которое можно передать, сохранить и выполнить позже.

## Опора на ООП

`Command` в первую очередь опирается на [инкапсуляцию](../../principles/index.md): действие и его контекст упаковываются в отдельный объект или описание вызова. Полиморфизм появляется там, где разные команды исполняются через единый механизм.

## Что показывает пример на 1С

- `CommonModules.BackgroundWorker` выступает как `Invoker`: создает структуру работника и потом вызывает `ExecuteNotifyProcessing()` для команд завершения и прогресса.
- В `CommonModules.Initialize` команды собираются через `NotifyDescription`, причем одна из них получает дополнительный `Context`.
- В результате код фонового исполнителя не знает, что именно будет происходить по завершении или во время прогресса.

## Пример

=== "CommonModules.Initialize"
    ```bsl
    #Region Public

    Procedure Init() Export

        // Note! NotifyDescription is a command object!

        UserName = "Harry"; // Some specifics context

        Worker = BackgroundWorker.NewWorker();
        Worker.OnFinish = NewCommandOnFinish();
        Worker.OnProgress = NewCommandOnProgress(UserName);

        BackgroundWorker.Run(Worker);

    EndProcedure

    #EndRegion

    #Region Internal

    #Region CommandOnFinish

    Function NewCommandOnFinish() Export

        Return New NotifyDescription("ExecCommandOnFinish", ThisObject);

    EndFunction

    Procedure ExecCommandOnFinish(Result, Context) Export

        // Do something...

    EndProcedure

    #EndRegion

    #Region CommandOnProgress

    Function NewCommandOnProgress(UserName) Export

        Context = New Structure;
        Context.Insert("UserName", UserName);

        Return New NotifyDescription("ExecCommandOnProgress", ThisObject, Context);

    EndFunction

    Procedure ExecCommandOnProgress(Result, Context) Export

        // Do something with Context.UserName

    EndProcedure

    #EndRegion

    #EndRegion
    ```

=== "CommonModules.BackgroundWorker"
    ```bsl
    #Region Public

    Function NewWorker() Export

        Self = New Structure;
        Self.Insert("OnFinish", Undefined);
        Self.Insert("OnProgress", Undefined);

        Return Self;

    EndFunction

    Procedure Run(Worker) Export

        // Invoker!
        ExecuteNotifyProcessing(Worker.OnProgress, "Specific Args 1");
        ExecuteNotifyProcessing(Worker.OnFinish, "Specific Args 2");

    EndProcedure

    #EndRegion
    ```

## Где полезен в 1С

- в фоновых заданиях и асинхронных сценариях;
- в UI-обработчиках, где нужно передать действие вместе с контекстом;
- в очередях операций, отложенных вызовах и повторном выполнении действий.

## Когда паттерн лишний

- если можно прямо вызвать одну процедуру;
- если команды ничем не отличаются и не живут дольше одного вызова;
- если передача действий только усложняет трассировку.

## Источник примера

- [zeegin/DesignPatterns: Command](https://github.com/zeegin/DesignPatterns/tree/master/Command)
