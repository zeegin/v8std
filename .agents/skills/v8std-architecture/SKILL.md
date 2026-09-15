---
name: v8std-architecture
description: Use when a v8std request may mutate files, affect architecture, requirements, ADRs, invariants, contracts or plans, or when implementation evidence changes the assessed impact.
---

# V8std architecture workflow

## Core rule

Classify impact before mutation and again before merge. A change is trivial
only after evidence excludes requirement, ADR, invariant and observable-contract
impact. Before mutation this is a manual assessment of intent and intended paths;
the CLI can inspect only an existing Git diff. Every mutation still uses a branch.

The normative process specification is
`spec/process/architecture-artifacts-v2.md`. The Python validator is its
executable implementation, not a second policy source. Read the specification;
never reproduce its fields or regexes in this skill.

## Required flow

1. Read `AGENTS.md`, `spec/README.md`, the current branch, `main`, and the
   process specification.
2. If the current branch is `main`, create a feature branch before the first write.
3. Inspect the actual code/docs and intended paths. A clean Git diff contains no
   evidence about the requested change.
4. Apply [impact check](references/impact-check.md) manually to the intent and
   intended paths. Call the change trivial only when every architecture trigger
   is disproved.
5. If architecture impact is found or remains unresolved, stop mutation, use
   `superpowers:brainstorming`, and select artifacts with
   [document triggers](references/document-triggers.md).
6. After written design approval, use `superpowers:writing-plans` when
   implementation is requested.
7. If implementation contradicts design or impact classification, stop and use
   [failure recovery](references/failure-recovery.md).
8. After a diff exists and before merge, run CLI `impact`, inspect all changed
   paths, repeat the semantic impact check, then run `validate --merge-ready`,
   declared fitness checks, the full test suite and strict build. Empty CLI output
   never proves triviality.
9. Merge locally into `main`. Push local `main` only with explicit authority; an
   authorized push automatically builds and publishes the site. Before controlled
   initial activation, MCP deployment requires a separate explicit request and
   exact verified main SHA. After activation, an authorized push permits the
   configured CI rollout of verified main and published digest, with post-deploy
   checks and rollback. It never grants this agent manual production/settings/
   credential mutations outside that path.

## Quick reference

| Evidence | Result |
|---|---|
| Only implementation internals change; no boundary or architecture trigger | Trivial path, branch and gates still required |
| Requirement, decision, durable property or boundary may change | Nontrivial; return to design |
| Accepted target has no complete accepted plan | It remains accepted but is not `IMPLEMENTED` |
| Complete accepted plan explicitly implements target | Target may be `IMPLEMENTED` |
| Existing structured document is in `main` | Frozen; create successor/version/revision |
| User authorizes push of local `main` | Verify local `main`; push automatically publishes the site |
| Before MCP activation | Explicit deployment request, verified main SHA and independent host prerequisites |
| After MCP activation | Authorized main push permits configured CI rollout of verified SHA/digest, not ad-hoc agent deployment |

## Red flags

Stop on: “small contract tweak”, direct `main`, merge-date ADR rename, editing an
accepted contract in place, incomplete plan, design-only called implemented,
silent invariant loss, site publication treated as ad-hoc MCP mutation authority, or
Git workflow proposed as a product invariant.

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
