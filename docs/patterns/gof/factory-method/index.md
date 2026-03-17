---
title: Factory Method
---

# Фабричный метод (`Factory Method`)

`Factory Method` делегирует создание конкретного объекта специальному методу.

## Опора на ООП

`Factory Method` классически построен прежде всего на [полиморфизме](../../principles/index.md): клиент вызывает общий способ создания, а конкретная реализация сама решает, какой объект вернуть. В этом смысле паттерн напрямую вырастает из идеи полиморфизма.

## Что показывает пример на 1С

- `CommonModules.ClientSpecific` экспортирует `CreateWrapper()` и возвращает `DataProcessors.COMWrapper.Create()`.
- Идея в том, что другой создатель, например для веб-клиента, может вернуть другую обертку при том же клиентском контракте.
- Внешний код просит "создай подходящий wrapper", а не выбирает конкретный `DataProcessor` сам.

## Пример

=== "CommonModules.ClientSpecific"
    ```bsl
    #Region Public

    Function CreateWrapper() Export

        Return DataProcessors.COMWrapper.Create();

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.COMWrapper"
    ```bsl
    #Region Public

    Function Init(COMObject) Export

        Return "Transformation";

    EndFunction

    #EndRegion
    ```

## Где полезен в 1С

- когда создание зависит от типа клиента или канала интеграции;
- когда нужно изолировать логику выбора конкретной реализации;
- когда важен единый вход для создания однотипных оберток и адаптеров.

## Когда паттерн лишний

- если тип реализации не меняется;
- если выбор делается один раз и проще описывается простым условием;
- если фабричный метод превращается в склад разрозненных `Если`.

## Источник примера

- [zeegin/DesignPatterns: FactoryMethod](https://github.com/zeegin/DesignPatterns/tree/master/FactoryMethod)
