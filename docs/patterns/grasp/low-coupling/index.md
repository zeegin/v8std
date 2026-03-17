---
title: Low Coupling
---

# Низкая связанность (`Low Coupling`)

`Low Coupling` требует уменьшать количество и жесткость зависимостей между частями системы.

## Опора на ООП

`Low Coupling` опирается на [интерфейсы, композицию и инкапсуляцию](../../principles/index.md): модуль зависит от контракта, а не от устройства конкретной реализации.

## Что показывает пример на 1С

- `PaymentService` зависит от абстрактного шлюза оплаты.
- Конкретный `BankGateway` подставляется снаружи.
- Сервис не вшивает внутрь себя детали конкретного банка или API.

## Пример

=== "DataProcessors.Application"
    ```bsl
    PaymentService = DataProcessors.PaymentService.Create();
    PaymentService.SetGateway(CommonModules.BankGateway);

    PaymentService.Pay(InvoiceRef, 1000);
    ```

=== "DataProcessors.PaymentService"
    ```bsl
    Var Gateway;

    #Region Public

    Procedure SetGateway(Gateway_) Export

        Gateway = Gateway_;

    EndProcedure

    Procedure Pay(InvoiceRef, Amount) Export

        Gateway.Pay(InvoiceRef, Amount);

    EndProcedure

    #EndRegion
    ```

=== "CommonModules.BankGateway"
    ```bsl
    Procedure Pay(InvoiceRef, Amount) Export

        // Bank-specific integration.

    EndProcedure
    ```

## Где полезен в 1С

- при интеграции с банками, API, внешними сервисами и обменами;
- когда реализация инфраструктуры может меняться;
- когда модуль хочется тестировать и заменять без каскадных правок.

## Когда принцип применяют неправильно

- когда интерфейсы вводятся "на всякий случай" без реальной точки изменения;
- когда низкая связанность покупается ценой чрезмерной фрагментации;
- когда ради отвязки скрывается важный смысл предметной области.
