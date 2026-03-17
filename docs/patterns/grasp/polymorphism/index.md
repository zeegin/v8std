---
title: Polymorphism
---

# Полиморфизм (`Polymorphism`)

`Polymorphism` в `GRASP` говорит: если поведение зависит от варианта, лучше распределить его по реализациям, а не держать в длинной цепочке условий.

Важно: это не то же самое, что [полиморфизм как принцип ООП](../../principles/index.md). В `GRASP` это уже архитектурное правило распределения ответственности, которое построено на полиморфизме как механизме языка и объектной модели.

## Опора на ООП

`Polymorphism` напрямую опирается на [полиморфизм и интерфейсы](../../principles/index.md): разные реализации отвечают на один и тот же запрос по-своему.

## Что показывает пример на 1С

- `DiscountCalculator` работает с политикой скидки через общий контракт.
- `RetailDiscountPolicy` и `WholesaleDiscountPolicy` реализуют разные правила.
- Контекст не содержит длинного `Если ... ИначеЕсли` по типу клиента.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Calculator = DataProcessors.DiscountCalculator.Create();

    If Counterparty.IsWholesale Then
        Calculator.SetPolicy(DataProcessors.WholesaleDiscountPolicy.Create());
    Else
        Calculator.SetPolicy(DataProcessors.RetailDiscountPolicy.Create());
    EndIf;

    DiscountAmount = Calculator.Calculate(SalesOrder);
    ```

=== "DataProcessors.DiscountCalculator"
    ```bsl
    Var Policy;

    #Region Public

    Procedure SetPolicy(Policy_) Export

        Policy = Policy_;

    EndProcedure

    Function Calculate(SalesOrder) Export

        Return Policy.Calculate(SalesOrder);

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.RetailDiscountPolicy"
    ```bsl
    Function Calculate(SalesOrder) Export

        Return SalesOrder.TotalAmount * 0.03;

    EndFunction
    ```

=== "DataProcessors.WholesaleDiscountPolicy"
    ```bsl
    Function Calculate(SalesOrder) Export

        If SalesOrder.TotalAmount >= 100000 Then
            Return SalesOrder.TotalAmount * 0.10;
        EndIf;

        Return SalesOrder.TotalAmount * 0.05;

    EndFunction
    ```

## Где полезен в 1С

- для разных правил расчета, обмена, печати и маршрутизации;
- когда ветвления по типам уже начинают дублироваться;
- как принцип, на котором потом строятся `Strategy`, `State` и похожие паттерны.

## Когда принцип применяют неправильно

- если вариантов один-два и они почти не меняются;
- если полиморфизм вводится без ясного общего контракта;
- если внешняя система все равно требует большого условного диспетчера.
