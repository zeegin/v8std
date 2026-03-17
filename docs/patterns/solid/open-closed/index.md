---
title: Open/Closed Principle
---

# Open/Closed Principle (`OCP`)

`OCP` говорит: модуль должен быть открыт для расширения, но закрыт для постоянной правки базового кода.

## Что означает в 1С

Если новый вариант поведения появляется регулярно, лучше подготовить точку расширения, чем каждый раз дописывать еще одну ветку `Если ... ИначеЕсли`.

## Пример на 1С

=== "DataProcessors.ExportService"
    ```bsl
    Var Provider;

    Procedure SetProvider(Provider_) Export

        Provider = Provider_;

    EndProcedure

    Function Export(DocumentRef) Export

        Return Provider.Export(DocumentRef);

    EndFunction
    ```

=== "CommonModules.PdfExportProvider"
    ```bsl
    Function Export(DocumentRef) Export

        Return "PDF";

    EndFunction
    ```

=== "CommonModules.ExcelExportProvider"
    ```bsl
    Function Export(DocumentRef) Export

        Return "XLSX";

    EndFunction
    ```

## Где полезен

- для вариантов печати, обмена, расчета и интеграции;
- когда список реализаций растет;
- в устойчивых прикладных сервисах, куда часто добавляют новые режимы.

## Когда применяют неправильно

- когда точку расширения строят заранее без реальной потребности;
- когда ради гипотетической гибкости вводят лишние абстракции;
- когда проще и понятнее оставить обычное условие.
