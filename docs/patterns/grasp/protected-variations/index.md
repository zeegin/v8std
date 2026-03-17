---
title: Protected Variations
---

# Защищенные вариации (`Protected Variations`)

`Protected Variations` рекомендует изолировать точки изменений стабильным контрактом, чтобы изменения не расходились по всей системе.

## Опора на ООП

`Protected Variations` опирается на [интерфейсы, инкапсуляцию и полиморфизм](../../principles/index.md): внешние клиенты знают стабильный контракт, а изменяющиеся реализации прячутся за ним.

## Что показывает пример на 1С

- `CurrencyRateService` зависит от контракта поставщика курсов.
- конкретный `ExternalRateProvider` можно заменить без переписывания сервиса.
- нестабильная часть системы изолирована в одном месте.

## Пример

=== "DataProcessors.Application"
    ```bsl
    RateService = DataProcessors.CurrencyRateService.Create();
    RateService.SetProvider(CommonModules.ExternalRateProvider);

    Rate = RateService.GetRate("USD", CurrentDate());
    ```

=== "DataProcessors.CurrencyRateService"
    ```bsl
    Var Provider;

    #Region Public

    Procedure SetProvider(Provider_) Export

        Provider = Provider_;

    EndProcedure

    Function GetRate(CurrencyCode, RateDate) Export

        Return Provider.GetRate(CurrencyCode, RateDate);

    EndFunction

    #EndRegion
    ```

=== "CommonModules.ExternalRateProvider"
    ```bsl
    Function GetRate(CurrencyCode, RateDate) Export

        Return 100;

    EndFunction
    ```

## Частый вариант в 1С

`Protected Variations` в 1С часто выражается не только через интерфейс или модуль-обертку, но и через справочники и регистры настроек, в которых варианты поведения задаются параметрами.

Идея такая:

- возможные способы работы алгоритма заранее описываются как допустимые варианты;
- прикладной код не переписывают под каждый новый сценарий, а читает параметры выбранного варианта;
- точка изменения переносится из кода в управляемую настройку.

Хороший пример - учетная политика.

В ней бизнес заранее фиксирует допустимые варианты расчета и отражения операций:

- способ оценки запасов;
- порядок признания расходов;
- варианты распределения затрат;
- правила налогового учета.

Тогда прикладной алгоритм работает не с россыпью `Если ... ИначеЕсли ...` по всей системе, а с параметризуемым элементом настройки:

```bsl
Policy = AccountingPolicyService.GetPolicy(Organization, Period);

If Policy.InventoryWriteOffMethod = Enums.InventoryWriteOffMethods.FIFO Then
    Return CalculateFifoCost(DocumentItems);
EndIf;

If Policy.InventoryWriteOffMethod = Enums.InventoryWriteOffMethods.AverageCost Then
    Return CalculateAverageCost(DocumentItems);
EndIf;
```

Здесь защищенной вариацией становится не только контракт сервиса `GetPolicy(...)`, но и сам набор допустимых настроек: система знает, какие варианты разрешены, и новые изменения старается вносить через расширение параметров, а не через хаотичную перепись всех клиентов.

## Где полезен в 1С

- для внешних API, платежных систем, обменов и провайдеров данных;
- для учетной политики, справочников настроек и параметризуемых алгоритмов;
- в зонах, где ожидаются смена реализации или разные поставщики;
- как архитектурная страховка от каскадных изменений.

## Когда принцип применяют неправильно

- если защищать просто нечего и точка изменения не просматривается;
- если ради гипотетической гибкости плодятся лишние абстракции;
- если стабильный контракт сам оказывается нестабильным и часто меняется.
