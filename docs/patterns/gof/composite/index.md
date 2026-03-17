---
title: Composite
---

# Компоновщик (`Composite`)

`Composite` позволяет работать с одиночными объектами и деревьями объектов через единый контракт.

## Опора на ООП

`Composite` опирается на [полиморфизм и интерфейсы](../../principles/index.md): и лист, и группа реализуют один и тот же контракт, поэтому клиенту не нужно знать, перед ним один узел или целая ветка.

## Что показывает пример на 1С

- `DataProcessors.ValidationGroup` хранит дочерние узлы и сам реализует тот же метод `Validate(Context)`, что и листья.
- `RequiredFieldRule` и `PositiveAmountRule` выступают как листья дерева правил.
- Клиент может запускать одну и ту же проверку и для одного правила, и для целой группы правил.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Rules = DataProcessors.ValidationGroup.Create();

    RequiredRule = DataProcessors.RequiredFieldRule.Create();
    RequiredRule.Init("Partner");

    AmountRule = DataProcessors.PositiveAmountRule.Create();
    AmountRule.Init("Amount");

    Rules.Add(RequiredRule);
    Rules.Add(AmountRule);

    If Rules.Validate(DocumentData) Then
        Message("Validation passed");
    EndIf;
    ```

=== "DataProcessors.ValidationGroup"
    ```bsl
    Var Children;

    #Region Public

    Procedure Add(Node) Export

        Children.Add(Node);

    EndProcedure

    Function Validate(Context) Export

        For Each Child In Children Do
            If Not Child.Validate(Context) Then
                Return False;
            EndIf;
        EndDo;

        Return True;

    EndFunction

    #EndRegion

    Children = New Array;
    ```

=== "DataProcessors.RequiredFieldRule"
    ```bsl
    Var FieldName;

    #Region Public

    Procedure Init(FieldName_) Export

        FieldName = FieldName_;

    EndProcedure

    Function Validate(Context) Export

        Return Context.Property(FieldName)
            And Context.Get(FieldName) <> Undefined;

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.PositiveAmountRule"
    ```bsl
    Var FieldName;

    #Region Public

    Procedure Init(FieldName_) Export

        FieldName = FieldName_;

    EndProcedure

    Function Validate(Context) Export

        Return Context.Get(FieldName) > 0;

    EndFunction

    #EndRegion
    ```

## Где полезен в 1С

- для деревьев проверок, фильтров и маршрутов согласования;
- для меню, настроек и иерархий команд;
- когда одинаковая операция должна работать и на листе, и на группе элементов.

## Когда паттерн лишний

- если структура не образует дерево;
- если листья и группы ведут себя слишком по-разному;
- если плоский список правил читается проще.
