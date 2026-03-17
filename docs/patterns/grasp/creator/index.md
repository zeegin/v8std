---
title: Creator
---

# Создатель (`Creator`)

`Creator` рекомендует поручать создание объекта тому, кто тесно связан с ним по данным, композиции или жизненному циклу.

## Опора на ООП

`Creator` опирается на [инкапсуляцию и низкую связанность](../../principles/index.md): объект создается там, где уже есть все данные для корректной инициализации.

## Что показывает пример на 1С

- `Documents.SalesOrder` сам создает `PostingContext`.
- Документ уже содержит организацию, склад и строки товаров, поэтому именно он может корректно подготовить контекст проведения.
- Клиент не собирает этот объект вручную из разрозненных полей.

## Пример

=== "DataProcessors.Application"
    ```bsl
    SalesOrder = Documents.SalesOrder.GetRef("...").GetObject();
    PostingContext = SalesOrder.CreatePostingContext();
    ```

=== "Documents.SalesOrder"
    ```bsl
    Function CreatePostingContext() Export

        PostingContext = DataProcessors.PostingContext.Create();
        PostingContext.Organization = Organization;
        PostingContext.Warehouse = Warehouse;
        PostingContext.Items = Items.Unload();

        Return PostingContext;

    EndFunction
    ```

=== "DataProcessors.PostingContext"
    ```bsl
    Var Organization Export;
    Var Warehouse Export;
    Var Items Export;
    ```

## Где полезен в 1С

- при создании контекстов проведения, печати, обмена и расчета;
- когда один объект агрегирует данные, нужные для инициализации другого;
- когда хочется убрать внешнюю ручную сборку служебных структур.

## Когда принцип применяют неправильно

- когда создатель ничего не знает о создаваемом объекте и просто "назначен" случайно;
- когда создание требует зависимостей из другой подсистемы;
- когда объект начинает производить слишком много чужих сущностей и превращается в фабрику всего подряд.
