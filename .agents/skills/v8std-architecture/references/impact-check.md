# Impact check

Perform before mutation and before merge. It is a semantic assessment, not the
CLI command itself.

## Before mutation

Inspect the request, actual code/docs and intended paths, then answer every
question below manually. CLI `impact` reads only an existing Git diff. On a clean
branch it has no changed paths to inspect, so empty output proves nothing about
the requested change.

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

## Diff and merge recheck

After a diff exists, run
`.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main`.
Its output lists only contract/invariant candidates whose `governs` paths match
the diff; it is not a semantic verdict. Inspect every candidate and every changed
path, answer the questions again, then record the conclusion in the task handoff.
New impact returns the work to design; it does not justify weakening the gate.
