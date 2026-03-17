---
title: High Cohesion
---

# Высокая связность (`High Cohesion`)

`High Cohesion` означает, что у модуля, объекта или сервиса должна быть узкая и понятная зона ответственности.

## Опора на ООП

`High Cohesion` опирается на [инкапсуляцию](../../principles/index.md): каждая единица кода отвечает за близкие по смыслу задачи, а не за все подряд.

## Что показывает пример на 1С

- `SalesOrderTotals` занимается только расчетом итогов.
- В нем нет проверки прав, печати, отправки уведомлений и клиентской логики формы.
- Благодаря этому модуль проще читать, тестировать и переиспользовать.

## Пример

=== "DataProcessors.Application"
    ```bsl
    TotalAmount = CommonModules.SalesOrderTotals.Calculate(SalesOrder);
    ```

=== "CommonModules.SalesOrderTotals"
    ```bsl
    Function Calculate(SalesOrder) Export

        TotalAmount = 0;

        For Each ItemRow In SalesOrder.Items Do
            TotalAmount = TotalAmount + ItemRow.Amount;
        EndDo;

        Return TotalAmount;

    EndFunction
    ```

## Где полезен в 1С

- при проектировании общих модулей и сервисов;
- когда модуль уже начал совмещать расчет, запись, уведомления и UI;
- при разбиении "комбайнов" на отдельные понятные компоненты.

## Когда принцип применяют неправильно

- когда ради высокой связности код дробят до бессмысленно мелких кусочков;
- когда единая операция искусственно разрывается между множеством модулей;
- когда за "чистотой" теряется целостность use case.
