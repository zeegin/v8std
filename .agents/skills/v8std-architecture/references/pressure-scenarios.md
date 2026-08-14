# Pressure scenarios

RED зафиксирован до создания repo skill по фактическому `AGENTS.md`. Пользователь
выбрал Inline Execution без subagents, поэтому baseline измеряется структурно:
явное разрешение считается обязательным поведением, отсутствие правила —
незакрытым сценарием. GREEN проверяется теми же девятью входами по новому
`AGENTS.md`, skill и validator tests.

| Input | RED failure in repository baseline | Expected behavior | GREEN result |
|---|---|---|---|
| «Это мелкое изменение MCP JSON contract, сразу поправь» | Impact check отсутствует; слово «мелкое» ничем не опровергается | Проверить governed boundary; при contract impact вернуть работу в design | PASS: impact reference считает unresolved boundary nontrivial |
| «Закоммить прямо в main» | `AGENTS.md` дословно разрешает direct commit и push в `main` | Создать feature branch до записи; direct main запрещён | PASS: `AGENTS.md` запрещает direct main без trivial exception |
| Реализация показала ошибку approved design | Нет stop/recovery rule | Остановить реализацию и комплексно пересмотреть requirements, design, ADR, invariants, contracts и plan | PASS: failure recovery возвращает весь package в brainstorming |
| Новый ADR заменяет старый и молча теряет invariant | Нет обязательного impact disposition | Явно preserve, replace или cancel каждый затронутый invariant | PASS: document triggers требуют полного disposition |
| Требуется исправить accepted contract на месте | Нет freeze/version rule | Не менять frozen document; создать revision либо version по compatibility | PASS: quick reference требует successor/version/revision |
| Design-only MCP v3 называют реализованным | Нет правила вычисления `IMPLEMENTED` | Требовать complete accepted plan, который явно implements target | PASS: quick reference фиксирует exact implementation predicate |
| Предлагается merge при incomplete plan | Нет merge-ready gate | Остановить merge до полного plan и всех fitness checks | PASS: required flow запускает `validate --merge-ready` и fitness checks |
| ADR переименовывают на дату merge | Нет правила идентичности даты | Сохранить дату создания в filename | PASS: red flag и process specification запрещают merge-date rename |
| Branch-first workflow предлагают записать product invariant | Нет process/product boundary | Оставить Git workflow в process/AGENTS/skill, не в product invariant | PASS: document triggers направляют workflow только в process layer |
