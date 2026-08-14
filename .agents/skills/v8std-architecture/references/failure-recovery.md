# Failure recovery

## Implementation defect

The approved requirement/design/boundary remains correct and code fails to
implement it. Add a failing regression test, prove RED, fix the cause, prove
GREEN, then repeat impact and merge gates.

## Project error

Evidence shows a requirement, decision, invariant, contract, scope or
triviality classification is wrong or incomplete. Stop implementation. Do not
patch around the design or relax validation.

Return to `superpowers:brainstorming` and review the package together:

1. affected requirements and their lifecycle;
2. design decisions and alternatives;
3. ADR replacement/cancellation;
4. invariant preservation/replacement/retirement;
5. contract compatibility and version/revision;
6. implementation plan, evidence and rollback.

Write successors rather than modifying structured `main` artifacts. Resume
implementation only after the revised written design and plan are approved.

## Classification test

If changing only code could make the approved conformance test pass, treat it
as an implementation defect. If success requires redefining what “pass” means,
it is a project error.
