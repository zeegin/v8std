---
title: Visitor
---

# Посетитель (`Visitor`)

`Visitor` выносит операции над набором объектов в отдельный объект-посетитель, чтобы не распихивать новые операции по самим элементам.

## Опора на ООП

`Visitor` опирается на [полиморфизм и интерфейсы](../../principles/index.md), а в классическом виде еще и на двойную диспетчеризацию: элемент принимает посетителя по общему контракту, а конкретная операция выбирается по типу элемента.

## Что показывает пример на 1С

- `CommonModules.ProductsTableVisitor.GetTable(DocumentObject)` вызывает `DocumentObject.Accept(ThisObject)`, а конкретные действия живут в `DoForSalesOrder()` и `DoForPicklist()`.
- `DataProcessors.ManagerVisitor` по тому же принципу назначает менеджера разным типам документов.
- Один и тот же набор документов можно обходить разными посетителями, не меняя код самих операций в каждом месте заново.

## Пример

=== "CommonModules.ProductsTableVisitor"
    ```bsl
    #Region Public

    Function GetTable(DocumentObject) Export

        Return DocumentObject.Accept(ThisObject);

    EndFunction

    #EndRegion

    #Region Internal

    Function DoForSalesOrder(DocumentObject) Export

        Table = New ValueTable;
        Table.Columns.Add("Products");
        Table.Columns.Add("Quantity");

        For Each Row In DocumentObject.Products Do

            TableRow = Table.Add();
            TableRow.Products = Row.Products;
            TableRow.Quantity = Row.Quantity;

        EndDo;

        Return Table;

    EndFunction

    #EndRegion
    ```

=== "DataProcessors.ManagerVisitor"
    ```bsl
    Var Manager;

    #Region Public

    Function SetManager(DocumentObject, Manager_) Export

        Manager = Manager_;
        Return DocumentObject.Accept(ThisObject);

    EndFunction

    #EndRegion

    #Region Internal

    Function DoForSalesOrder(DocumentObject) Export

        DocumentObject.ResponsiblePerson = Manager;
        Return True;

    EndFunction

    Function DoForPicklist(DocumentObject) Export

        DocumentObject.Manager = Manager;
        Return True;

    EndFunction

    #EndRegion
    ```

## Где полезен в 1С

- когда есть стабильный набор типов документов или объектов;
- когда над ними нужно регулярно добавлять новые операции;
- когда хочется собрать логику преобразований и выгрузок в отдельные объекты.

## Когда паттерн лишний

- если типов элементов много и они часто меняются;
- если операция всего одна;
- если двойная диспетчеризация делает код сложнее, чем простой условный разбор.

## Источник примера

- [zeegin/DesignPatterns: Visitor](https://github.com/zeegin/DesignPatterns/tree/master/Visitor)
