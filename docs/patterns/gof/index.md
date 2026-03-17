---
title: GOF
---

# GOF

`GOF` — это набор из 23 классических паттернов проектирования из книги *Design Patterns: Elements of Reusable Object-Oriented Software*.

## Как читать раздел

1. Сначала понять намерение паттерна, а не копировать форму.
2. Потом посмотреть, как эта идея раскладывается на объекты метаданных, общие модули, формы и обработчики в 1С.
3. И только после этого решать, нужен ли паттерн в прикладной задаче или достаточно более простого кода.

## Порождающие паттерны

| Паттерн | Коротко | Пример |
| --- | --- | --- |
| [Абстрактная фабрика](abstract-factory/index.md) (`Abstract Factory`) | Создает семейства связанных объектов через единый интерфейс. | [AbstractFactory](https://github.com/zeegin/DesignPatterns/tree/master/AbstractFactory) |
| [Строитель](builder/index.md) (`Builder`) | Разделяет процесс пошаговой сборки сложного объекта и его итоговое представление. | [Builder](https://github.com/zeegin/DesignPatterns/tree/master/Builder) |
| [Фабричный метод](factory-method/index.md) (`Factory Method`) | Делегирует создание объектов специализированному методу или подклассу. | [FactoryMethod](https://github.com/zeegin/DesignPatterns/tree/master/FactoryMethod) |
| [Прототип](prototype/index.md) (`Prototype`) | Создает новые объекты копированием заранее настроенного экземпляра. | [Prototype](https://github.com/zeegin/DesignPatterns/tree/master/Prototype) |
| [Одиночка](singleton/index.md) (`Singleton`) | Ограничивает создание класса одним экземпляром и дает глобальную точку доступа. | [Singleton](https://github.com/zeegin/DesignPatterns/tree/master/Singleton) |

## Структурные паттерны

| Паттерн | Коротко | Пример |
| --- | --- | --- |
| [Адаптер](adapter/index.md) (`Adapter`) | Приводит несовместимый интерфейс к ожидаемому клиентом виду. | [Adapter](https://github.com/zeegin/DesignPatterns/tree/master/Adapter) |
| [Мост](bridge/index.md) (`Bridge`) | Разделяет абстракцию и реализацию, чтобы их можно было развивать независимо. |  |
| [Компоновщик](composite/index.md) (`Composite`) | Позволяет работать с одиночными объектами и их деревьями единообразно. |  |
| [Декоратор](decorator/index.md) (`Decorator`) | Добавляет объекту поведение через обертку, не меняя исходный класс. |  |
| [Фасад](facade/index.md) (`Facade`) | Дает простой внешний вход к сложной подсистеме. |  |
| [Приспособленец](flyweight/index.md) (`Flyweight`) | Выносит общую часть состояния, чтобы экономить память на большом числе однотипных объектов. |  |
| [Заместитель](proxy/index.md) (`Proxy`) | Подставляет специальный объект вместо реального и контролирует доступ к нему. |  |

## Поведенческие паттерны

| Паттерн | Коротко | Пример |
| --- | --- | --- |
| [Цепочка обязанностей](chain-of-responsibility/index.md) (`Chain of Responsibility`) | Передает запрос по цепочке обработчиков, пока кто-то не возьмет его на себя. | [ChainOfResponsibility](https://github.com/zeegin/DesignPatterns/tree/master/ChainOfResponsibility) |
| [Команда](command/index.md) (`Command`) | Представляет действие как отдельный объект. | [Command](https://github.com/zeegin/DesignPatterns/tree/master/Command) |
| [Интерпретатор](interpreter/index.md) (`Interpreter`) | Описывает грамматику языка и интерпретирует выражения этого языка. |  |
| [Итератор](iterator/index.md) (`Iterator`) | Дает способ обходить коллекцию, не раскрывая ее внутреннее устройство. | [Iterator](https://github.com/zeegin/DesignPatterns/tree/master/Iterator) |
| [Посредник](mediator/index.md) (`Mediator`) | Централизует взаимодействие между объектами и уменьшает прямые связи между ними. | [Mediator](https://github.com/zeegin/DesignPatterns/tree/master/Mediator) |
| [Снимок](memento/index.md) (`Memento`) | Сохраняет и восстанавливает внутреннее состояние объекта. | [Memento](https://github.com/zeegin/DesignPatterns/tree/master/Memento) |
| [Наблюдатель](observer/index.md) (`Observer`) | Подписчики получают уведомление об изменении состояния издателя. | [Observer](https://github.com/zeegin/DesignPatterns/tree/master/Observer) |
| [Состояние](state/index.md) (`State`) | Перекладывает поведение по состояниям в отдельные объекты-состояния. | [State](https://github.com/zeegin/DesignPatterns/tree/master/State) |
| [Стратегия](strategy/index.md) (`Strategy`) | Инкапсулирует взаимозаменяемые алгоритмы за единым интерфейсом. | [Strategy](https://github.com/zeegin/DesignPatterns/tree/master/Strategy) |
| [Шаблонный метод](template-method/index.md) (`Template Method`) | Задает каркас алгоритма, оставляя отдельные шаги на расширение. | [TemplateMethod](https://github.com/zeegin/DesignPatterns/tree/master/TemplateMethod) |
| [Посетитель](visitor/index.md) (`Visitor`) | Выносит операции над структурой объектов в отдельный объект-посетитель. | [Visitor](https://github.com/zeegin/DesignPatterns/tree/master/Visitor) |
