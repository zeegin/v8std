---
title: Bridge
---

# Мост (`Bridge`)

`Bridge` разделяет абстракцию и реализацию так, чтобы их можно было развивать независимо.

## Опора на ООП

`Bridge` опирается на [композицию, интерфейсы и полиморфизм](../../principles/index.md): абстракция не вшивает реализацию внутрь себя, а держит ссылку на отдельный объект с общим контрактом.

## Что показывает пример на 1С

- `DataProcessors.DocumentExporter` отвечает за прикладной сценарий экспорта, но не знает деталей конкретного формата.
- `CommonModules.PdfRenderer` и `CommonModules.HtmlRenderer` реализуют единый контракт `Render(Data)`.
- Клиент может менять реализацию рендера независимо от того, какой именно объект он экспортирует.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Exporter = DataProcessors.DocumentExporter.Create();
    Exporter.SetRenderer(CommonModules.PdfRenderer);

    PdfResult = Exporter.Export(SalesOrderRef);

    Exporter.SetRenderer(CommonModules.HtmlRenderer);
    HtmlResult = Exporter.Export(SalesOrderRef);
    ```

=== "DataProcessors.DocumentExporter"
    ```bsl
    Var Renderer;

    #Region Public

    Procedure SetRenderer(Renderer_) Export

        Renderer = Renderer_;

    EndProcedure

    Function Export(DocumentRef) Export

        Data = PrepareData(DocumentRef);
        Return Renderer.Render(Data);

    EndFunction

    #EndRegion

    #Region Private

    Function PrepareData(DocumentRef)

        Data = New Structure;
        Data.Insert("Number", DocumentRef.Number);
        Data.Insert("Date", DocumentRef.Date);
        Return Data;

    EndFunction

    #EndRegion
    ```

=== "CommonModules.PdfRenderer"
    ```bsl
    Function Render(Data) Export

        Return "PDF:" + Data.Number;

    EndFunction
    ```

=== "CommonModules.HtmlRenderer"
    ```bsl
    Function Render(Data) Export

        Return "<html><body>" + Data.Number + "</body></html>";

    EndFunction
    ```

## Где полезен в 1С

- когда прикладной объект и способ его представления меняются по разным причинам;
- когда один и тот же сценарий должен работать с несколькими форматами вывода;
- когда не хочется размножать комбинации вида `SalesOrderPdfExporter`, `SalesOrderHtmlExporter`, `InvoicePdfExporter`.

## Когда паттерн лишний

- если реализация одна и не будет меняться;
- если второй оси вариативности пока нет;
- если композиция добавляет больше абстракции, чем дает реальной гибкости.
