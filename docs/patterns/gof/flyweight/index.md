---
title: Flyweight
---

# Приспособленец (`Flyweight`)

`Flyweight` выносит общую часть состояния, чтобы не хранить одинаковые данные в большом количестве однотипных объектов.

## Опора на ООП

`Flyweight` опирается на [инкапсуляцию и композицию](../../principles/index.md): неизменяемая общая часть состояния живет в разделяемом объекте, а внешний контекст передается отдельно в момент использования.

## Что показывает пример на 1С

- `CommonModules.CellStyleFactory` кэширует небольшое число объектов стиля по коду.
- `ReportCellPainter` получает стиль как разделяемую часть, а конкретный текст и ячейку как внешнее состояние.
- Один и тот же объект стиля можно переиспользовать для множества строк отчета или табличного документа.

## Пример

=== "DataProcessors.Application"
    ```bsl
    ErrorStyle = CommonModules.CellStyleFactory.GetStyle("Error");
    WarningStyle = CommonModules.CellStyleFactory.GetStyle("Warning");

    Painter = DataProcessors.ReportCellPainter.Create();
    Painter.DrawCell(Cell1, ErrorStyle, "Over limit");
    Painter.DrawCell(Cell2, ErrorStyle, "Missing data");
    Painter.DrawCell(Cell3, WarningStyle, "Close to threshold");
    ```

=== "CommonModules.CellStyleFactory"
    ```bsl
    Var Cache;

    #Region Public

    Function GetStyle(Code) Export

        If Cache.ContainsKey(Code) Then
            Return Cache.Get(Code);
        EndIf;

        Style = CreateStyle(Code);
        Cache.Insert(Code, Style);
        Return Style;

    EndFunction

    #EndRegion

    #Region Private

    Function CreateStyle(Code)

        If Code = "Error" Then
            Return New Structure("Color,Bold", "Red", True);
        EndIf;

        Return New Structure("Color,Bold", "Orange", False);

    EndFunction

    #EndRegion

    Cache = New Map;
    ```

=== "DataProcessors.ReportCellPainter"
    ```bsl
    Procedure DrawCell(Cell, Style, Text) Export

        Cell.Text = Text;
        Cell.TextColor = Style.Color;
        Cell.FontBold = Style.Bold;

    EndProcedure
    ```

## Где полезен в 1С

- при большом количестве однотипных настроек оформления;
- в кэшах метаданных, описаний колонок, шаблонов и справочных структур;
- когда общих комбинаций мало, а объектов применения много.

## Когда паттерн лишний

- если объектов немного и экономия несущественна;
- если разделяемое состояние часто меняется;
- если внешнее состояние становится слишком сложным и неудобным для передачи.
