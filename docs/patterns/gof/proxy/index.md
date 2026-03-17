---
title: Proxy
---

# Заместитель (`Proxy`)

`Proxy` подставляет специальный объект вместо реального и контролирует доступ к нему.

## Опора на ООП

`Proxy` опирается на [интерфейсы, композицию и инкапсуляцию](../../principles/index.md): клиент работает с тем же контрактом, что и с реальным объектом, а детали контроля доступа, ленивой инициализации или удаленного вызова скрыты внутри заместителя.

## Что показывает пример на 1С

- `DataProcessors.SalesReportProxy` выглядит для клиента как обычный сервис отчета.
- Внутри proxy проверяет доступ и создает тяжелый сервис только при первом реальном обращении.
- Клиент не знает, работает ли он с реальным объектом напрямую или через заместителя.

## Пример

=== "DataProcessors.Application"
    ```bsl
    ReportService = DataProcessors.SalesReportProxy.Create();
    Data = ReportService.GetData(DateFrom, DateTo);
    ```

=== "DataProcessors.SalesReportProxy"
    ```bsl
    Var RealService;

    #Region Public

    Function GetData(DateFrom, DateTo) Export

        EnsureAccess();
        EnsureInitialized();
        Return RealService.GetData(DateFrom, DateTo);

    EndFunction

    #EndRegion

    #Region Private

    Procedure EnsureAccess()

        If Not Rights.CanRead("SalesReport") Then
            Raise "Access denied";
        EndIf;

    EndProcedure

    Procedure EnsureInitialized()

        If RealService = Undefined Then
            RealService = DataProcessors.HeavySalesReportService.Create();
        EndIf;

    EndProcedure

    #EndRegion
    ```

=== "DataProcessors.HeavySalesReportService"
    ```bsl
    Function GetData(DateFrom, DateTo) Export

        Return New ValueTable;

    EndFunction
    ```

## Близость к Decorator

`Proxy` очень похож на [Decorator](../decorator/index.md), потому что снаружи оба паттерна выглядят как обертка над тем же самым контрактом.

В обоих случаях:

- клиент работает с тем же интерфейсом;
- внутри есть ссылка на другой объект;
- вызов делегируется дальше.

Но задача у них разная.

- `Decorator` отвечает на вопрос: как добавить новое поведение поверх существующего объекта?
- `Proxy` отвечает на вопрос: как контролировать доступ к объекту или отложить работу с ним?

Для 1С это различие удобно помнить так:

- логирование, ретраи и кэширование вокруг отправителя - это чаще `Decorator`;
- проверка прав, ленивая инициализация тяжелого сервиса или проксирование удаленного вызова - это чаще `Proxy`.

## Где полезен в 1С

- для ленивой инициализации тяжелых сервисов;
- для проверки прав и технического контроля доступа;
- для удаленных, внешних и потенциально дорогих по времени вызовов.

## Когда паттерн лишний

- если заместитель ничего не добавляет поверх реального объекта;
- если прямой вызов и так безопасен и дешев;
- если proxy начинает превращаться в фасад с новой бизнес-логикой.
