---
title: Pure Fabrication
---

# Чистая выдумка (`Pure Fabrication`)

`Pure Fabrication` разрешает ввести отдельный служебный объект, если это снижает связанность и не перегружает доменную модель чужой логикой.

## Опора на ООП

`Pure Fabrication` опирается на [низкую связанность и высокую связность](../../principles/index.md): иногда лучше создать специальный сервис, чем заставлять доменный объект делать неестественную для него работу.

## Что показывает пример на 1С

- сериализация документа для обмена вынесена в `ExchangePayloadSerializer`.
- логика подготовки JSON не попадает в объект документа.
- доменная модель и интеграционная логика остаются разделены.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Payload = CommonModules.ExchangePayloadSerializer.Serialize(SalesOrder);
    ```

=== "CommonModules.ExchangePayloadSerializer"
    ```bsl
    Function Serialize(SalesOrder) Export

        Payload = New Structure;
        Payload.Insert("Number", SalesOrder.Number);
        Payload.Insert("Date", SalesOrder.Date);
        Payload.Insert("Partner", SalesOrder.Partner);

        Return WriteJSON(Payload);

    EndFunction
    ```

## Где полезен в 1С

- для сериализации, маппинга, интеграций, кэширования и служебных вычислений;
- когда доменные объекты начали обрастать техническими обязанностями;
- когда нужен отдельный сервис, не отражающий бизнес-сущность напрямую.

## Когда принцип применяют неправильно

- если под видом `Pure Fabrication` создают случайные "утилиты на все случаи";
- если служебный сервис становится новой свалкой логики;
- если вынесенная обязанность на самом деле естественно принадлежала доменному объекту.
