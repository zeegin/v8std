---
title: Interpreter
---

# Интерпретатор (`Interpreter`)

`Interpreter` описывает грамматику небольшого языка и выполняет выражения этого языка над заданным контекстом.

## Опора на ООП

`Interpreter` опирается на [полиморфизм и композицию](../../principles/index.md): каждое выражение реализует общий контракт интерпретации, а сложные выражения собираются из более простых.

## Что показывает пример на 1С

- `EqualsStatusExpression` и `AmountGreaterExpression` интерпретируют простые правила над одним и тем же контекстом.
- `AndExpression` собирает из них составное выражение.
- Клиент работает уже не с длинным `Если`, а с объектным представлением простого DSL.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Context = New Structure;
    Context.Insert("Status", "Ready");
    Context.Insert("Amount", 1500);

    StatusExpression = DataProcessors.EqualsStatusExpression.Create();
    StatusExpression.Init("Ready");

    AmountExpression = DataProcessors.AmountGreaterExpression.Create();
    AmountExpression.Init(1000);

    Rule = DataProcessors.AndExpression.Create();
    Rule.Init(StatusExpression, AmountExpression);

    If Rule.Interpret(Context) Then
        Message("Rule matched");
    EndIf;
    ```

=== "DataProcessors.EqualsStatusExpression"
    ```bsl
    Var ExpectedStatus;

    #Region Public

    Procedure Init(ExpectedStatus_) Export

        ExpectedStatus = ExpectedStatus_;

    EndProcedure

    Function Interpret(Context) Export

        Return Context.Get("Status") = ExpectedStatus;

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.AmountGreaterExpression"
    ```bsl
    Var Limit;

    #Region Public

    Procedure Init(Limit_) Export

        Limit = Limit_;

    EndProcedure

    Function Interpret(Context) Export

        Return Context.Get("Amount") > Limit;

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.AndExpression"
    ```bsl
    Var LeftExpression;
    Var RightExpression;

    #Region Public

    Procedure Init(LeftExpression_, RightExpression_) Export

        LeftExpression = LeftExpression_;
        RightExpression = RightExpression_;

    EndProcedure

    Function Interpret(Context) Export

        Return LeftExpression.Interpret(Context)
            And RightExpression.Interpret(Context);

    EndFunction

    #EndRegion
    ```

## Где полезен в 1С

- для небольших DSL правил, фильтров и формул;
- для интерпретации настроек маршрутов, условий скидок и выражений отбора;
- когда предметная область уже оперирует собственным маленьким языком.

## Когда паттерн лишний

- если правило проще записать обычным кодом;
- если язык быстро становится слишком большим и требует полноценного парсера;
- если объектная модель выражений сложнее самой задачи.
