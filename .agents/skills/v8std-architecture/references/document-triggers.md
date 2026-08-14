# Document triggers

Select documents by cause, not by perceived change size.

| Cause | Required artifact |
|---|---|
| New or changed obligation | Design requirement with semantic code |
| Choice among architecture alternatives | One atomic ADR |
| Durable property whose violation falsifies a decision | Product invariant and fitness check |
| Observable producer/consumer boundary | Versioned contract and conformance evidence |
| Multiple related decisions, requirements or boundaries | Design connecting the graph |
| Approved implementation is requested | Checkbox plan with typed `implements` |
| Repository workflow/schema changes | Process specification, skill or `AGENTS.md`; never product invariant |

Use typed references from the process specification. A replacement explicitly
preserves, replaces or cancels affected requirements, ADRs, invariants and
contracts. Compatibility determines contract revision versus version. Existing
structured documents in `main` are evidence snapshots, not editable records.
