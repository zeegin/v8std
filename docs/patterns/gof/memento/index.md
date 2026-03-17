---
title: Memento
---

# Снимок (`Memento`)

`Memento` сохраняет состояние объекта так, чтобы потом можно было откатиться назад, не раскрывая наружу все внутренние детали.

## Опора на ООП

`Memento` опирается прежде всего на [инкапсуляцию](../../principles/index.md): внутреннее состояние сохраняется во внешнем снимке без раскрытия всей внутренней структуры объекта.

## Что показывает пример на 1С

- `DataProcessors.Editor` в `CreateSnapshot()` сам снимает свое состояние в `Structure`: простые значения, массив сериализованных строк таблицы и остальные данные состояния.
- `DataProcessors.SnapshotSpace` хранит снимки и умеет восстанавливать объект из выбранного источника снимка.
- Снимок хранит не ссылки на внутренние структуры редактора, а отдельное представление, пригодное для восстановления.
- Для 1С это особенно полезно там, где пользователь долго редактирует объект и ожидает отката или истории изменений.

## Пример

=== "DataProcessors.Application"
    ```bsl
    Editor = DataProcessors.Editor.Create();
    SnapshotSpace = DataProcessors.SnapshotSpace.Create();

    SnapshotSpace.Save("draft-1", Editor.CreateSnapshot());

    Editor.SetValue("Changed value");
    Editor.SetData("Changed data");

    SnapshotSpace.Save("draft-2", Editor.CreateSnapshot());

    SnapshotSpace.Restore(Editor, "draft-1");
    ```

=== "DataProcessors.Editor"
    ```bsl
    #Region Public

    Procedure SetValue(NewValue) Export

        Value = NewValue;

    EndProcedure

    Procedure SetData(NewData) Export

        Data = NewData;

    EndProcedure

    Function CreateSnapshot() Export

        Self = New Structure;
        Self.Insert("Value", Value);
        Self.Insert("Data", Data);

        SerializedTable = New Array;
        For Each RowTable In Table Do
            Row = New Structure;
            Row.Insert("Key", RowTable.Key);
            Row.Insert("Val", RowTable.Val);
            SerializedTable.Add(Row);
        EndDo;

        Self.Insert("Table", SerializedTable);

        Return Self;

    EndFunction

    Procedure Restore(Snapshot) Export

        Value = Snapshot.Value;
        Data = Snapshot.Data;

        Table = New ValueTable;
        Table.Columns.Add("Key");
        Table.Columns.Add("Val");

        For Each SnapshotRow In Snapshot.Table Do
            Row = Table.Add();
            Row.Key = SnapshotRow.Key;
            Row.Val = SnapshotRow.Val;
        EndDo;

    EndProcedure

    #EndRegion
    ```

=== "DataProcessors.SnapshotSpace"
    ```bsl
    Var Snapshots;

    #Region Public

    Procedure Save(Key, Snapshot) Export

        Snapshots.Insert(Key, Snapshot);

    EndProcedure

    Function GetSnapshot(Key) Export

        Return Snapshots.Get(Key);

    EndFunction

    Procedure Restore(Target, Key) Export

        Snapshot = GetSnapshot(Key);
        If Snapshot = Undefined Then
            Return;
        EndIf;

        Target.Restore(Snapshot);

    EndProcedure

    #EndRegion

    Snapshots = New Map;
    ```

## Как обычно распределяются роли

У `Memento` важно не только хранение снимка, но и распределение ответственности.

- `Originator` сам снимает снимок с себя, потому что только он знает, какие данные действительно составляют его корректное внутреннее состояние;
- `Caretaker` или пространство снимков не лезет внутрь объекта, а только хранит версии и решает, какую из них нужно вернуть;
- восстановление часто инициируется именно из пространства истории, а не из самого объекта.

Поэтому на практике часто получается такая схема:

- объект делает `CreateSnapshot()`;
- пространство истории сохраняет снимок;
- позже пространство истории вызывает `Restore(...)` для выбранной версии.

Именно это показано в примере выше через `SnapshotSpace.Restore(Editor, "draft-1")`.

## Платформенный пример в 1С: история данных

У платформы 1С этот паттерн во многом уже реализован встроенным механизмом [История данных](https://v8.1c.ru/platforma/istoriya-dannyh/). Официальное описание платформы прямо говорит, что механизм хранит версии данных, позволяет сравнивать версии и восстанавливать данные в состояние выбранной версии.

Архитектурно это очень близко к `Memento`:

- прикладной объект выступает источником состояния;
- платформа хранит версии в собственном пространстве истории;
- восстановление идет не "изнутри" прикладного кода, а через механизм истории и переход на выбранную версию.

В документации это видно по нескольким точкам расширения и вызовам:

- в версии `8.3.11` появился глобальный доступ к механизму через свойство `ИсторияДанных` / `DataHistory`, то есть пространство снимков стало доступно из встроенного языка ([1C:DN](https://1c-dn.com/library/v8update_2079252602_new_functionality_and_changes/));
- для анализа двух версий платформа использует вызовы вида `ИсторияДанных.ПолучитьРазличиеВерсий(...)`, что прямо показывает работу не с живым объектом, а с двумя сохраненными снимками ([V8Update 8.3.14](https://downloads.v8.1c.ru/content/Platform/8_3_14_1494/1cv8upd_8_3_14_1494.htm));
- при переходе на выбранную историческую версию разработчик может подключиться через обработчик `ОбработкаФормированияПоВерсииИсторииДанных()`, а номер версии передается в форму через параметр `НомерВерсииПереходаНаВерсиюИсторииДанных` ([1C:DN, версия 8.3.13](https://1c-dn.com/library/v8update_2079252604_new_functionality_and_changes/));
- для конкретного объекта документация также описывает принудительное обновление истории через метод `DataHistory.UpdateHistory()`, если нужно добрать версии именно для выбранного объекта ([1C:DN, версия 8.3.13](https://1c-dn.com/library/v8update_2079252604_new_functionality_and_changes/)).

Из этого следует важный практический вывод для 1С: сам снимок обычно относится к объекту, а выбор версии и восстановление чаще относятся уже к пространству истории. Это ровно та роль, которую в паттерне `Memento` играет внешний хранитель снимков.

## Где полезен в 1С

- в редакторах документов и настроек;
- в мастерах, где нужен шаг назад;
- в сценариях локального undo без записи промежуточных состояний в базу.

## Когда паттерн лишний

- если состояние дешево пересчитать заново;
- если история не нужна;
- если копирование больших структур становится слишком дорогим.

## Источник примера

- [zeegin/DesignPatterns: Memento](https://github.com/zeegin/DesignPatterns/tree/master/Memento)
