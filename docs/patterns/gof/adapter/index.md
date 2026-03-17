---
title: Adapter
---

# Адаптер (`Adapter`)

`Adapter` переводит неудобный или устаревший интерфейс в тот контракт, который нужен клиентскому коду.

## Опора на ООП

`Adapter` в первую очередь опирается на [интерфейсы и инкапсуляцию](../../principles/index.md): несовместимый контракт прячется внутри адаптера, а наружу отдается ожидаемый API. Полиморфизм появляется, когда адаптер подменяет обычную реализацию по тому же контракту.

## Что показывает пример на 1С

- `CommonModules.Adapter` экспортирует понятный клиенту метод `BeautyMethod2WTF(Parameters)`.
- Внутри адаптер преобразует входные данные через `Convert()`, вызывает `Legacy.WTFMethod(Input, Output)` и потом собирает ответ через `Extract(Output)`.
- Код, который использует адаптер, не знает деталей старого контракта и не размазывает их по системе.

## Пример

=== "CommonModules.Adapter"
    ```bsl
    #Region Public

    Function BeautyMethod2WTF(Parameters) Export

        Input = Convert(Parameters);
        Output = Undefined;

        Legacy.WTFMethod(Input, Output);

        Result = Extract(Output);
        Return Result;

    EndFunction

    #EndRegion

    #Region Private

    Function Convert(Parameters)

        Return Parameters;

    EndFunction

    Function Extract(Output)

        Return Output;

    EndFunction

    #EndRegion
    ```

=== "CommonModules.Legacy"
    ```bsl
    #Region Public

    Procedure WTFMethod(Input, Output) Export

        Output = "Shit";

    EndProcedure

    #EndRegion
    ```

## Где полезен в 1С

- при оборачивании старых общих модулей с неудачным API;
- при интеграции с внешними компонентами, COM или HTTP-клиентами;
- когда нужно перейти на новый интерфейс без массовой переписи прикладного кода.

## Когда паттерн лишний

- если старый код можно безопасно переделать без слоя совместимости;
- если различия между интерфейсами минимальны;
- если адаптер начинает содержать слишком много бизнес-логики и превращается в фасад или сервис.

## Источник примера

- [zeegin/DesignPatterns: Adapter](https://github.com/zeegin/DesignPatterns/tree/master/Adapter)
