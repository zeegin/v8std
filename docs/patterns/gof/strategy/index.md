---
title: Strategy
---

# Стратегия (`Strategy`)

`Strategy` прячет несколько взаимозаменяемых алгоритмов за единым контрактом.

## Опора на ООП

`Strategy` — один из самых прямых паттернов на [полиморфизм и интерфейсы](../../principles/index.md): контекст вызывает общий контракт стратегии и не знает, какой конкретный алгоритм сейчас подставлен.

## Что показывает пример на 1С

- `DataProcessors.Context` умеет `SetStrategy(Strategy_)` и затем в `SendMessage(Message)` делегирует вызовы объекту стратегии.
- `EmailStrategy`, `SMSStrategy` и `TelegramStrategy` реализуют общий набор действий: `SetRecipient()` и `SendMessage()`.
- Это прямой и очень узнаваемый для 1С пример выбора канала без условий в клиентском коде.

## Пример

=== "DataProcessors.Context"
    ```bsl
    Var Strategy;

    #Region Public

    Procedure SetStrategy(Strategy_) Export

        Strategy = Strategy_;

    EndProcedure

    Function SendMessage(Message) Export

        Strategy.SetRecipient(Partner);
        Strategy.SendMessage(Message);

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.EmailStrategy"
    ```bsl
    Var EmailAdress;

    #Region Public

    Function SetRecipient(Recipient) Export

        EmailAdress = Recipient.GetEmailAdressr(); // Implement it!

    EndFunction

    Function SendMessage(Message) Export

        // Implement it!
        Return True;

    EndFunction

    #EndRegion
    ```

## Где полезен в 1С

- для выбора канала уведомлений;
- для разных алгоритмов расчета, экспорта или подбора данных;
- когда бизнес-сценарий стабилен, а способы его выполнения меняются.

## Когда паттерн лишний

- если вариантов алгоритма мало и они почти не отличаются;
- если стратегии знают слишком много о контексте;
- если обычная функция с параметром читается проще.

## Источник примера

- [zeegin/DesignPatterns: Strategy](https://github.com/zeegin/DesignPatterns/tree/master/Strategy)
