---
name: v8std-architecture
description: Use when a v8std request may mutate files, affect architecture, requirements, ADRs, invariants, contracts or plans, or when implementation evidence changes the assessed impact.
---

# V8std architecture workflow

## Core rule

Classify impact before mutation and again before merge. A change is trivial
only after evidence excludes requirement, ADR, invariant and observable-contract
impact. Every mutation still uses a branch.

The normative process specification is
`spec/process/architecture-artifacts-v1.md`. The Python validator is its
executable implementation, not a second policy source. Read the specification;
never reproduce its fields or regexes in this skill.

## Required flow

1. Read `AGENTS.md`, `spec/README.md`, the current branch, `main`, and the
   process specification.
2. If the current branch is `main`, create a feature branch before the first write.
3. Inspect the actual code/docs and run
   `.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main`.
4. Apply [impact check](references/impact-check.md). Call the change trivial only
   when every architecture trigger is disproved.
5. If architecture impact is found or remains unresolved, stop mutation, use
   `superpowers:brainstorming`, and select artifacts with
   [document triggers](references/document-triggers.md).
6. After written design approval, use `superpowers:writing-plans` when
   implementation is requested.
7. If implementation contradicts design or impact classification, stop and use
   [failure recovery](references/failure-recovery.md).
8. Before merge, repeat impact check; run `validate --merge-ready`, declared
   fitness checks, the full test suite and strict build.
9. Merge locally into `main`. Do not push or deploy without explicit authority.

## Quick reference

| Evidence | Result |
|---|---|
| Only implementation internals change; no boundary or architecture trigger | Trivial path, branch and gates still required |
| Requirement, decision, durable property or boundary may change | Nontrivial; return to design |
| Accepted target has no complete accepted plan | It remains accepted but is not `IMPLEMENTED` |
| Complete accepted plan explicitly implements target | Target may be `IMPLEMENTED` |
| Existing structured document is in `main` | Frozen; create successor/version/revision |
| User requests deployment | Verify exact SHA is in `main`, then handle separately |

## Red flags

Stop on: “small contract tweak”, direct `main`, merge-date ADR rename, editing an
accepted contract in place, incomplete plan, design-only called implemented,
silent invariant loss, or Git workflow proposed as a product invariant.

The matching RED/GREEN cases are in
[pressure scenarios](references/pressure-scenarios.md).

## Common rationalizations

| Rationalization | Reality |
|---|---|
| “The user called it trivial” | Triviality is the impact result, not an input |
| “It is docs/config only” | Observable boundaries often live there |
| “Existing tests are green” | They do not prove unchanged architecture intent |
| “Editing the accepted file is clearer” | Frozen evidence requires a successor/version |
| “Direct main is faster” | The branch-first Git flow has no trivial exception |
