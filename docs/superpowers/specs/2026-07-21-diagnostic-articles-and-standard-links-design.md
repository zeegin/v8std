# Diagnostic Articles and Exact Standard Links Design

## Status

Approved direction: hybrid synchronization of upstream diagnostic articles plus
v8std-owned exact mappings to standard clauses.

## Goal

Turn every BSL Language Server and EDT v8-code-style diagnostic page into a
complete, source-backed article, then make every diagnostic-to-standard
relationship explicit, reviewable, reproducible, and linked to the exact
standard clause that explains the diagnostic.

The work covers 186 BSL Language Server diagnostics and 172 EDT v8-code-style
diagnostics. ACC articles and extraction from the ACC configuration are outside
this scope. Existing ACC content and relationships must remain intact.

## Current problem

The repository currently stores relationships in two manually maintained
places:

- diagnostic pages link to whole standard pages;
- standard pages contain reverse diagnostic links, usually in a generic
  `Проверки` block.

The model loses the clause number that is present in many upstream references.
Consequently:

- none of the 706 current links contains a clause anchor;
- the two directions can be structurally symmetric while semantically wrong;
- unsupported upstream URL forms are silently skipped;
- stale and overly generic relationships cannot be distinguished from reviewed
  relationships;
- short local diagnostic cards omit restrictions, examples, and remediation
  guidance available in upstream articles.

## Design principles

1. Upstream text and v8std analysis are separate concerns.
2. Generated data has one source of truth and is never maintained twice.
3. Every accepted relationship records evidence and an exact clause.
4. An unknown or incomplete relationship fails validation instead of silently
   degrading to a page-level link.
5. Upstream synchronization is reproducible from pinned Git revisions.
6. Generated files are committed so the site build remains network-independent.
7. ACC is not migrated and must not be modified by the generator.

## Source and licensing model

### Source revisions

The first migration uses these reviewed snapshots:

- BSL Language Server:
  `f4616cda8a216789ee40529ed857e614b9e2ea25`;
- EDT v8-code-style:
  `c8fe7932babf718c0ace3cf836a99d6a3b98d098`.

Later updates require an explicit revision change in the source manifest. The
sync command refuses a checkout whose `HEAD` does not match the manifest.

### Licensing boundary

Imported article bodies remain attributed derivative material:

- BSL Language Server article bodies retain `LGPL-3.0-or-later` provenance;
- EDT v8-code-style article bodies retain `EPL-2.0` provenance.

Each generated page contains a machine-readable HTML comment with the source
repository, source path, revision, license, and content hash. A repository
notice documents that these managed article sections retain their upstream
licenses and are not relicensed by the repository's CC0 declaration.

The following sections are v8std-owned editorial content and are kept outside
the imported body:

- local diagnostic metadata;
- `Соответствие стандартам`;
- evidence and review status;
- navigation and v8std source links.

The generator must not remove upstream copyright or license notices if they
appear in a source article.

## Data model

### Source manifest

`data/diagnostic-sources.json` records one family entry and one diagnostic entry
per page.

Family fields:

- `family`: `bslls` or `v8-code-style`;
- `repository`: canonical Git repository URL;
- `revision`: full 40-character Git SHA;
- `license`: SPDX identifier;
- `source_root`: directory containing Russian diagnostic Markdown.

Diagnostic fields:

- `id`: local canonical diagnostic identifier;
- `source_path`: path relative to the upstream repository;
- `source_url`: immutable GitHub URL using the pinned revision;
- `content_sha256`: hash of the normalized imported body.

The manifest contains exactly 186 BSL Language Server entries and 172 EDT
v8-code-style entries. Duplicate IDs, missing local pages, missing source files,
or unmanifested local pages are validation errors.

### Relationship registry

`data/diagnostic-standard-links.json` contains reviewed relationships for BSL
Language Server and EDT v8-code-style. ACC relationships remain outside this
registry during this project.

Each review record contains:

- `diagnostic`: canonical ID including family prefix;
- `standard`: `stdNNN`;
- `clause`: normalized visible clause number such as `2.4.3`, required for a
  confirmed record and optional for a rejected proposal;
- `anchor`: rendered Markdown/HTML anchor such as `243`, required for a
  confirmed record and absent when a rejected proposal has no meaningful
  clause;
- `evidence`: one or more immutable source URLs or a local-standard citation;
- `reason`: concise explanation of why the diagnostic enforces that clause;
- `review`: `confirmed` or `rejected`;
- `notes`: optional explanation for upstream corrections or exceptions.

Only `confirmed` records are rendered. Rejected upstream suggestions remain in
the registry so they are not reintroduced during later synchronization. A
rejected record still names the proposed standard and evidence, and its
`reason` explains why the proposal is not normative.

A confirmed relationship without a clause is invalid. If a whole standard
genuinely applies but no numbered clause exists, the registry uses the
standard's stable `stdNNN` heading as an explicit top-level clause and records
that decision in `notes`.

## Generated diagnostic article

Every generated page has this order:

1. existing canonical marker (`bslls:...` or `v8cs:...`);
2. source title with the canonical diagnostic ID;
3. existing local metadata such as type, importance, default state, tags, or
   EDT category;
4. managed imported article body, excluding the duplicate upstream H1;
5. `Соответствие стандартам` generated from confirmed registry entries;
6. `Источник диагностики` with immutable source URL, revision, license, and
   attribution.

The managed imported body is delimited by HTML comments. Manual text outside
the managed block is preserved. Manual edits inside the block are overwritten
and detected by the content hash.

Standard links use exact local anchors, for example:

```markdown
[#std455, п. 2.4.3: Структура модуля](../../std/455.md#243)
```

Each link is followed by the registry's short `reason`, allowing readers and
reviewers to understand the mapping without opening the registry.

## Standard-page backlinks

The generator removes only BSL Language Server and EDT links that it owns.
ACC links and unrelated page content are preserved byte-for-byte.

Confirmed backlinks are rendered in a managed `Проверки` block belonging to
the exact clause. The block is placed at the end of that numbered clause,
immediately before the next numbered heading. Multiple diagnostics for one
clause share one block and use stable family/ID sorting.

If an old generic block contains both ACC and managed-family links, the ACC
lines remain in the old block while BSL Language Server and EDT lines move to
their reviewed clauses. Empty generated blocks are removed.

The forward diagnostic link and reverse standard backlink are always generated
from the same registry entry.

## Import and generation commands

`scripts/sync_diagnostic_articles.py` has two modes:

- `--check`: verify source revisions, manifests, hashes, generated article
  bodies, and coverage without changing files;
- `--write`: update manifests and generated article sections from explicitly
  supplied local upstream checkouts.

It requires both source checkout paths. It never clones repositories or uses
the network implicitly.

`scripts/generate_diagnostic_standard_links.py` also has two modes:

- `--check`: validate registry schema, clauses, anchors, evidence, forward
  links, backlinks, and deterministic output;
- `--write`: regenerate relationship sections and managed backlinks.

Both scripts use only the Python standard library. JSON is chosen instead of
YAML so CI and source-composition tests do not depend on optional PyYAML.

## Upstream URL normalization

The relationship importer recognizes and normalizes all observed v8std forms:

- `#content:NNN:hdoc`;
- `#content:NNN:hdoc:X.Y`;
- `/content/NNN/hdoc`;
- `/content/NNN/hdoc/`;
- `/content/NNN/hdoc#X.Y`;
- the known upstream typo `#contrut:NNN:hdoc`.

An unknown v8std URL form is a hard error with source file and URL in the
message. The importer never treats an unparsed URL as "no relationship".

Nearby prose such as `раздел 5.7` may propose a clause, but it cannot create a
confirmed relationship without registry review.

## Semantic review workflow

Every source-proposed relationship goes through this sequence:

1. normalize the source URL and extract standard and proposed clause;
2. confirm that the local standard exists;
3. confirm that the visible clause exists and renders to the recorded anchor;
4. read the diagnostic's scope and limitations from the imported article;
5. compare those conditions with the normative text of the clause;
6. record a concise reason and immutable evidence;
7. confirm, redirect to another clause/standard, or reject the suggestion;
8. regenerate both link directions;
9. run semantic coverage tests.

Generic references are not accepted merely because upstream lists them.
Specifically, the 44 repeated BSL Language Server references to `std456` are
review candidates, not automatic additions.

The migration must resolve all issues listed in
`diagnostic-standard-links-review-2026-07-21.md`, including missing links,
misplaced clause blocks, stale transaction references, and the misleading
`extension-md-object-prefix` and `using-isinrole` relationships.

## Error handling and invariants

Generation fails when any of these conditions is true:

- source checkout revision differs from the pinned revision;
- source/local catalog composition differs from the manifest;
- a source article is empty or has no H1;
- an expected Russian article is missing;
- an upstream v8std URL is not parsed;
- a confirmed relationship references a missing standard or clause;
- the stored anchor differs from the anchor rendered by the current heading;
- a confirmed relationship has no evidence or reason;
- duplicate or contradictory confirmed/rejected entries exist;
- a managed-family Markdown link exists outside generated regions;
- generated output differs from committed output in `--check` mode;
- ACC content changes during either generator run.

## Tests

Tests are added before implementation and must demonstrate red-green behavior.

Unit tests cover:

- every supported and unsupported upstream URL form;
- source title/body normalization;
- immutable source URL construction;
- source revision and hash validation;
- Markdown anchor derivation for integer and dotted clauses;
- relationship schema and rejection handling;
- deterministic article and backlink rendering;
- preservation of ACC and unmanaged content.

Repository-level tests prove:

- exact 186/172 catalog coverage;
- all 358 pages contain a non-empty managed article body;
- normalized bodies match the pinned upstream snapshots;
- every confirmed link has a valid exact anchor;
- forward and reverse relationships are equal because they derive from one
  registry;
- all source-proposed links are confirmed or explicitly rejected;
- the audit's known missing and wrong mappings cannot regress;
- `--check` reports a clean repository after generation;
- AI/MCP artifacts expose exact standard links and complete article text;
- strict documentation build succeeds.

The final verification runs the complete Python test suite, AI artifact
generation, search benchmark, strict Zensical build, generator check modes,
`git diff --check`, and a clean regeneration diff.

## Rollout sequence

1. Introduce tests, manifests, registry schema, and parsers.
2. Import complete BSL Language Server articles.
3. Review and migrate BSL Language Server relationships.
4. Import complete EDT v8-code-style articles.
5. Review and migrate EDT relationships.
6. Generate exact backlinks and remove obsolete managed links.
7. Regenerate indexes and AI/MCP artifacts.
8. Run the complete verification matrix and inspect representative rendered
   pages from each family.

The family split creates reviewable checkpoints but does not narrow the final
scope: completion requires all 358 articles and every proposed relationship to
be accounted for.

## Acceptance criteria

The objective is complete only when all of the following are proved from the
current checkout:

- 186 BSL Language Server and 172 EDT pages contain source-backed articles;
- every article records immutable source revision, path, hash, license, and
  attribution;
- source manifests exactly match both local catalogs and pinned upstream
  catalogs;
- every upstream-proposed relationship is confirmed or explicitly rejected;
- every confirmed relationship targets an existing exact clause anchor;
- diagnostic pages and standard pages are generated from one registry and are
  symmetric;
- every audit finding is resolved or represented as a documented rejection;
- ACC files are unchanged;
- all tests, generators, AI/MCP generation, benchmark, and strict site build
  pass from a clean regeneration;
- no unreviewed page-level fallback link remains for BSL Language Server or EDT.

## Non-goals

- extracting ACC diagnostics from the configuration;
- rewriting ACC diagnostic articles;
- changing analyzer implementations;
- fixing incorrect upstream documentation in external repositories;
- fetching sources during ordinary site or CI builds;
- adding a general-purpose documentation localization framework.
