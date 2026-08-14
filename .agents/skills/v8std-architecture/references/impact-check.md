# Impact check

Run before mutation and before merge. Inspect the actual diff or intended paths;
the validator's `impact` output is a candidate list, not a semantic verdict.

## Questions

Answer each with evidence:

1. Does the request add, remove or reinterpret a product requirement?
2. Does it choose a different architecture direction or reverse an ADR?
3. Can it violate, replace or retire a durable product property?
4. Does it change an observable boundary: endpoint, URI, MCP tool/resource,
   JSON field, event, metric, Markdown/HTML contract or generated registry?
5. Does it alter compatibility, producer, consumers, version or conformance?
6. Does it change a path listed by contract/invariant `governs`?
7. Does implementation evidence contradict the approved design or earlier
   triviality assessment?

Any “yes” or unresolved answer is nontrivial. Use brainstorming before further
mutation. “The user called it trivial”, small diff size, no runtime code, or a
passing existing suite are not evidence of triviality.

## Merge recheck

Compare `main...HEAD`, rerun `impact`, inspect every candidate and newly changed
path, then record the conclusion in the task handoff. New impact returns the
work to design; it does not justify weakening the gate.
