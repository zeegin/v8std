---
title: Builder
---

# Строитель (`Builder`)

`Builder` отделяет сценарий сборки объекта от конкретного представления результата.

## Опора на ООП

`Builder` опирается на [инкапсуляцию](../../principles/index.md): процесс сборки и промежуточное состояние объекта прячутся внутри строителя. Когда у строителей есть общий контракт шагов, подключается и полиморфизм.

## Что показывает пример на 1С

- `DataProcessors.Director` хранит ссылку на строителя и в `Make(Type, Manager)` выполняет общий сценарий: `Reset()`, `SetTelephone()`, `SetManager()`, при необходимости `SetDebt()`.
- `LeadsBuilder` и `PartnersBuilder` реализуют одинаковые шаги, но собирают разные объекты метаданных.
- В результате один и тот же алгоритм сборки порождает разные прикладные объекты без `Если ... Тогда` по типам во внешнем коде.

## Пример

=== "DataProcessors.Director"
    ```bsl
    Var Builder;

    #Region Public

    Procedure Init(Builder_) Export

        Builder = Builder_;

    EndProcedure

    Function Make(Type, Manager) Export

        Builder.Reset();
        Builder.SetTelephone();
        Builder.SetManager(Manager);

        If Type = "CleanDebt" Then
            Builder.SetDebt(0);
        EndIf;

        Return Builder.GetResult();

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.LeadsBuilder"
    ```bsl
    Var Object;

    #Region Public

    Procedure Reset() Export

        Object = Catalogs.Leads.CreateItem();

    EndProcedure

    Procedure SetTelephone(Tel) Export

        Object.Telephone = Tel;
        Object.CountryCode = ExtractCountryCode(Tel);

    EndProcedure

    Procedure SetManager(Manager) Export

        Object.ResponsiblePerson = Manager;

    EndProcedure

    Function GetResult()

        Return Object;

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.PartnersBuilder"
    ```bsl
    Var Object;

    #Region Public

    Procedure Reset() Export

        Object = Catalogs.Partners.CreateItem();

    EndProcedure

    Procedure SetTelephone(Tel) Export

        Object.Tel = Tel;

    EndProcedure

    Procedure SetManager(Manager) Export

        Object.Manager = Manager;

    EndProcedure

    Procedure SetDebt(Debt) Export

        Object.Debt = Debt;

    EndProcedure

    Function GetResult()

        Return Object;

    EndFunction

    #EndRegion
    ```

## Вариации

У `Builder` есть несколько распространенных форм.

### С директором и без директора

- `С директором`:
  отдельный объект управляет шагами сборки и знает правильный порядок вызовов. Именно такой вариант показан в примере через `DataProcessors.Director`.
- `Без директора`:
  клиент сам вызывает шаги строителя в нужном порядке. Это проще по структуре, если сценарий сборки короткий и не требует отдельной оркестрации.

### Классический и fluent-builder

- `Классический builder`:
  методы вроде `Reset()`, `SetTelephone()` и `SetManager()` ничего не возвращают, а результат забирается отдельным `GetResult()`.
- `Fluent builder`:
  каждый шаг возвращает самого строителя, чтобы можно было писать цепочки вызовов.

Пример fluent-подхода на 1С:

```bsl
Builder
    .Reset()
    .SetTelephone(Телефон)
    .SetManager(Менеджер)
    .SetDebt(0);

Result = Builder.GetResult();
```

В 1С fluent-вариант удобен для компактных сценариев, но классический builder обычно проще читать и отлаживать, особенно если шаги сборки связаны с побочными эффектами или клиент-серверным разделением.

## Где полезен в 1С

- когда объект собирается в несколько этапов из разных источников данных;
- когда есть несколько вариантов итогового результата при общем сценарии подготовки;
- когда важно централизовать обязательные шаги создания объекта.

## Когда паттерн лишний

- если объект создается одной строкой;
- если различия между вариантами минимальны;
- если строители только проксируют присваивания и не дают архитектурной пользы.

## Источник примера

- [zeegin/DesignPatterns: Builder](https://github.com/zeegin/DesignPatterns/tree/master/Builder)
