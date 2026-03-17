---
title: Template Method
---

# Шаблонный метод (`Template Method`)

`Template Method` фиксирует общий каркас алгоритма и оставляет отдельные шаги на конкретную реализацию.

## Опора на ООП

Классический `Template Method` строится на [наследовании и полиморфизме](../../principles/index.md): базовый алгоритм задается один раз, а отдельные шаги переопределяются в потомках. В 1С эту идею часто имитируют несколькими модулями с одинаковым публичным контрактом.

## Что показывает пример на 1С

- В репозитории рядом лежат `CommonModules.COMConnector` и `CommonModules.RASConnector` с одинаковым публичным контрактом `GetSessions()` и `GetLocks()`.
- Пример компактный, но он хорошо показывает направление: есть общий сценарий работы с коннектором, а конкретные детали скрыты в специализированном модуле.
- Для 1С это типичная основа для унификации разных поставщиков или транспортов под одним API.

## Пример

=== "CommonModules.COMConnector"
    ```bsl
    #Region Public

    Function GetSessions() Export

        Return "Specific"; // Implement it!

    EndFunction

    Function GetLocks() Export

        Return "Specific"; // Implement it!

    EndFunction

    #EndRegion
    ```

=== "CommonModules.RASConnector"
    ```bsl
    #Region Public

    Function GetSessions() Export

        Return "Specific"; // Implement it!

    EndFunction

    Function GetLocks() Export

        Return "Specific"; // Implement it!

    EndFunction

    #EndRegion
    ```

## Где полезен в 1С

- когда несколько интеграций проходят одинаковую последовательность шагов;
- когда хочется выровнять контракт для нескольких коннекторов;
- когда общая часть алгоритма стабильна, а детали различаются.

## Когда паттерн лишний

- если общего каркаса фактически нет;
- если отличий между реализациями больше, чем общего;
- если проще использовать `Strategy`.

## Источник примера

- [zeegin/DesignPatterns: TemplateMethod](https://github.com/zeegin/DesignPatterns/tree/master/TemplateMethod)
