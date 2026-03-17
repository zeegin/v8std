---
title: Abstract Factory
---

# Абстрактная фабрика (`Abstract Factory`)

`Abstract Factory` создает не один объект, а семейство совместимых объектов через общий контракт.

## Опора на ООП

Этот паттерн в первую очередь опирается на [полиморфизм, интерфейсы и инкапсуляцию](../../principles/index.md): клиент знает только общий контракт фабрики, а выбор конкретного семейства реализаций спрятан внутри.

## Что показывает пример на 1С

- `CommonModules.WindowsFactory` и `CommonModules.LinuxFactory` экспортируют одинаковые методы `CreateProcess()` и `CreateTempFile()`.
- `DataProcessors.Application` принимает фабрику в `Init()` и потом работает только через `Factory.CreateProcess()` и `Factory.CreateTempFile()`.
- Клиентский код переключает сразу целое семейство реализаций, а не выбирает каждый объект по отдельности.

## Пример

=== "CommonModules.WindowsFactory"
    ```bsl
    #Region Public

    Function CreateProcess() Export

        Return True; // TODO: Implement it! Return concreate object

    EndFunction

    Function CreateTempFile() Export

        Return False; // TODO: Implement it! Return concreate object

    EndFunction

    #EndRegion
    ```

=== "CommonModules.LinuxFactory"
    ```bsl
    #Region Public

    Function CreateProcess() Export

        Return False; // TODO: Implement it! Return concreate object

    EndFunction

    Function CreateTempFile() Export

        Return True; // TODO: Implement it! Return concreate object

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.Application"
    ```bsl
    Var Factory;

    Function Init(Factory_) Export

        Factory = Factory_;

    EndFunction

    Function RunTempProcess() Export

        Process = Factory.CreateProcess();
        TempFile = Factory.CreateTempFile();

    EndFunction
    ```

## Где полезен в 1С

- когда нужно подменять набор интеграционных объектов под разную среду;
- когда один и тот же сценарий должен работать с разными поставщиками инфраструктуры;
- когда важно держать совместимость объектов внутри одной "платформы" или режима работы.

## Когда паттерн лишний

- если семейство реализаций всего одно;
- если меняется только один объект и достаточно `Factory Method`;
- если клиенту проще прямо создать нужный объект без дополнительного слоя.

## Источник примера

- [zeegin/DesignPatterns: AbstractFactory](https://github.com/zeegin/DesignPatterns/tree/master/AbstractFactory)
