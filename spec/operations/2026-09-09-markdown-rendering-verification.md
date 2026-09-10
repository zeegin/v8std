# Task4: Markdown rendering verification, 2026-09-09

## Current interpretation, approved 2026-09-10

The user authorized correcting the agent-added no-JS-dark requirement, not
adding a theme feature. The applicable matrix is 108 recorded combinations:
9 routes × 4 widths × (light JS, dark JS, existing light no-JS). All retain
readable articles, no zero grid column and no direct article text. The three
no-JS header overflow observations within this matrix have equal before/after
widths and are outside the article; they are not claimed fixed. Another 36
dark-preference/no-JS rows remain raw observations of the light fallback.

Mermaid's identical HTML and no-JS source text satisfy preservation checks;
its absent clipboard control is N/A. SVG rendering was not proven in either
reference variant and is not newly claimed or repaired. No product, CSS,
template, dependency or accepted architecture document changed in this scope
clarification. Original probe results below remain unchanged as history.
Fresh integration gates and whole-branch review are recorded at the end.

## Historical collection result, 2026-09-09

Outcome: **PARTIAL / DONE_WITH_CONCERNS**. The authorized evidence collection
is finished and handed off for review. Task4's complete browser gate is **not
passed**. No-JS dark is **NOT PROVEN**, six matrix rows retain overflow, and
the Mermaid browser probe did not prove diagram rendering. No plan checkbox
was changed. No commit, merge, push, publication or MCP operation occurred.

## Scope and identity

Verification followed Task4 of the
[implementation plan](../plans/2026-09-09-markdown-fence-rendering-plan.md)
and its approved design. Work stayed in the existing main checkout and feature branch
`codex/issue-35-markdown-rendering-plan`.

HEAD and main during verification:
`8e891945dc3767ea328239b8c562ffded7d4e4d6`. This is the base, **not an
implementation/integration commit**. The older design reproduction base
`f9e660bd...` is not the tested working-tree base.

`git diff --binary main` SHA-256 before and after probes:
`d24f854376100a71aee274ee204e733ef829de0e1571a5f95f30963b80a548c4`.
This tracked-diff hash excludes untracked implementation files. Their exact
identity is included below and in `before-task4-snapshot.json`.

| Checked file | SHA-256 |
|---|---|
| scripts/check_article_html.py | 848b7c02cb2e3993082fd0c72cd5fbcf1f77ae4dd479a8c2794ef15fd63dd9c0 |
| scripts/v8std_markdown.py | da1cf9a6de442346e55facb60970e5790b9467f471a16db3f5cb9d84f1fb6235 |
| scripts/zensical_docs.sh | 39cc36abb43f39785bf9255a150773b7677572eda64996099ac2873af858698e |
| zensical.toml | 9792880301a4638b2879ac885c2186cb7059cc5787ef52967fb0f9415a6b41a4 |
| tests/test_article_html.py | a907a7991c8e5ea0433400ca0f0ebec797f2c482834c0e7fb33b13874a845f10 |
| tests/test_v8std_markdown.py | c7783ab296349f416825439dff67aadc4dce5ef7be65a826274d06089940e8d4 |

Host: Python 3.12.10, Zensical 0.0.47, Markdown 3.10.2, PyMdown 11.0.1.
Browser: isolated headless Google Chrome 151.0.7922.109 through bundled
Playwright/Node 24.19.0; no installation or user browser profile.

All runtime JSON, command logs, HTML fixtures and screenshots remain in
`/tmp/v8std-issue35.pLZSHc`. They are temporary local evidence, not committed
attachments. This report and scripts preserve the findings and reproduction.

## Corpus and source preservation

`verify-task4.py corpus` exited 0. Each of **1428** `docs/**/*.md` files was
rendered by a fresh Markdown instance with project configuration, once with
the extension and once without. HTMLParser projections compared ordered
heading/link/pre/code/highlight/mermaid tags and sorted attributes; exact
pre/code text; and whitespace-normalized ordinary visible text. Code
whitespace was not normalized. Initially valid pages also required full HTML
byte equality.

| Measure | Result |
|---|---:|
| Baseline structurally invalid Markdown pages | 42 |
| Changed HTML pages | 42 |
| Originally valid pages with byte-identical HTML | 1386 |
| After-render structurally invalid pages | 0 |
| Semantic, code, attribute or valid-page regressions | 0 |
| Compact/separated reference fixtures, exact HTML | 11/11 |

The prior fresh site baseline, recorded by Task1, had **1429 articles, 234
violations on 42 pages**. The final checked site has **1429 articles, zero
violations**. The HTML count includes generated `404.html`; it is not the
1428-source-file count. The baseline counts are attributed to Task1, not
presented as a second baseline site build by this worker.

Final `git diff --exit-code main -- docs data/diagnostic-sources.json` exited
0 with empty output. All 3358 preexisting files in the initial tracked/source/
implementation snapshot still matched their initial SHA-256 at handoff.
This includes generated AI files, CSS, templates and dependencies.

Source checks: diagnostic article integrity **358**, ACC **691**, relation
graph **358**, all exit 0. Source-derived expected Markdown sidecars were
regenerated in memory and compared to **1270** actual site sidecars: zero
mismatches. No normalized HTML input replaced the sidecar/AI source corpus.

Independent source manifest digest over sorted `docs/**/*.md`, followed by
`data/diagnostic-sources.json`, with each record `path + NUL + file_sha256 + LF`:
**1429 files**, SHA-256
`e402aa912934177bc418bfe58e9766c986fddc9d6cea7c2759dbdb19e1c7c462`.
The ledger's `6d1e2372...` digest uses an unspecified serialization; these two
aggregate digests are not asserted equal. Git/main equality and per-file
before/after hashes provide the independently verified preservation evidence.

Evidence: `corpus.json`, `sidecars.json`, `before-task4-snapshot.json`,
`after-task4-probes-snapshot.json`, `browser-oracles.json`, source-check logs.

## Serve and local Docker

Serve ran through `VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh serve
--dev-addr=127.0.0.1:8769`. The first probe incorrectly treated the startup
HTTP response as ready; it exited 1 before the article file existed. Its own
process group was stopped. The corrected verification script waited for one
valid article and the actual HTML file, then completed successfully.

For the successful run (own process group leader PID 55673): initial and
mtime-triggered HTTP responses each contained one article and zero checker
violations. Only `touch docs/diagnostics/bslls/SetPrivilegedMode.md` triggered
the rebuild. HTML file mtime changed; serve remained the same process; the log
contains the initial and subsequent `No issues found` events. No checker
rewrote the response.

Source before/after SHA-256:
`ccff3b04bac6621a0734d8c8b87f1fe917c35c2214b7f2a812c0b3f00b22eafe`.
HTTP body before/after SHA-256:
`06cf99bbcab3a96a58f8afe006d594c86eabdaae2e342d133c3aa8a077e79876`.
Evidence: `serve.json`, `serve.log`, `serve-initial.html`, `serve-rebuilt.html`.

Docker context was explicitly `desktop-linux`, using its local Unix socket;
client/server preflight 29.7.2. Real local Docker build, image import from `/tmp` with
`PYTHONPATH=/opt/v8std`, and project-config render through a read-only `/docs`
mount all exited 0. The rendered compact BSL fixture contained standalone
before/code/after blocks and passed `check_html` (1 article, 0 violations).

Built runtime: Zensical **0.0.47**, Markdown **3.10.3**, PyMdown **11.0.2**.
Thus Docker evidence is independent of the older host dependency versions.
The existing install script and dependency policy were not changed.
Image retained locally: `v8std-markdown-check:issue35`, ID
`sha256:79d5bb8144a85cb30916cd503af23eefa0ac62d56cba4e94b7ac581d95a0a4a2`.
No compose service or MCP server was started. Evidence: `docker-{build,import,render}.{json,log}`.

## Browser matrix and residual failures

Routes: `/diagnostics/bslls/SetPrivilegedMode/`, the same route with
`?h=привилеги#setprivilegedmode`, `/std/640/`, `/std/643/`, `/std/686/`,
`/std/726/`, `/lang/`,
`/diagnostics/v8-code-style/common-module-named-self-reference/`, and
`/diagnostics/bslls/TransferringParametersBetweenClientAndServer/`.
The EDT route is the specified baseline representative.

Each route used widths 390/768/1024/1920, JS on/off, and light/dark OS preference:
**144 rows and 144 screenshots**, zero navigation/probe errors, all HTTP 200.
Screenshots awaited fonts (`loaded`), used reduced motion and disabled
animations, and had no consent overlay. In JS contexts the actual consent UI
was opened, GitHub unchecked through its label, the unchecked state verified,
then `Принять` saved the refusal. No optional cookie was enabled.

| Requested mode | Rows | Actual scheme | Layout failures | Theme gate |
|---|---:|---|---:|---|
| JS light | 36 | default | 0 | Proven |
| JS dark | 36 | slate | 0 | Proven |
| no-JS light | 36 | default | 3 | Light observed; overflow remains |
| no-JS dark | 36 | default | 3 | **NOT PROVEN** |

All 144 rows had zero non-whitespace direct article text nodes and no zero
grid column. At issue35 widths 1024/1920, columns were respectively
`151.609px 577.281px` / `166.75px 846.688px`; page widths equaled viewports.
At 390/768 the article was non-grid and readable. These measurements are not
an assertion that all browser gates passed.

The **six failure rows** are lang, EDT and residual BSLLS, each at 390 px in
both no-JS OS preferences. Their page width is **403 px**. A reconstructed
before-render comparison used the current identical theme shell, substituted
only the article rendered without the extension, and served the HTML outside
the corpus. Before and after both measured 403 px; corresponding JS cases
measured 390 px. This is a controlled renderer comparison, not an archived
pre-change full-site build.

Cause evidence: the unchanged outer `.md-header__topic` / `.md-ellipsis`
title reaches x=403 (width 306) in these no-JS pages. The article containers do
not produce that page overflow. Code spans can extend within their scrolling
containers; actual horizontal wheel probes confirmed internal code scroll
on issue35/lang/residual with and without JS, **6/6**, advancing scrollLeft
to 240/47/240 px. The header issue predates the renderer change, but the six
matrix failures remain recorded and are not relabeled green.

Evidence: `browser-matrix.json`, `layout-details.json`, `final-diagnostics.json`,
`layout-*.png`, `code-scroll-*.png`. Parent also independently viewed issue35
mobile light/dark and no-JS std640 keyboard focus screenshots and reported
them readable with no consent blur. This report's worker visually inspected
issue35 mobile light, issue35 1920 dark, residual mobile dark, and std686
1024 no-JS screenshots; the remaining screenshots are available for review.

## Clipboard, links, search and Mermaid

`browser-interactions.json` contains **53 checks** and no probe exceptions.
Of these, **42 non-fixture checks passed**: 32 page-code preservation checks
(8 distinct pages × 4 JS/preference combinations), four anchor checks, four
keyboard chip checks, and two JS search-highlight checks. Both no-JS
preferences still mean actual light, not dark coverage.

Real code-copy buttons copied **184 blocks** from the eight pages in two JS
themes; clipboard permissions were granted only to isolated contexts and
reads followed the probe's own copy action. DOM pre/code text matched the
without-extension oracle exactly. Clipboard strings matched expected code
with the theme's terminal-newline trimming (`trimEnd`); this transformation
was not applied to the corpus preservation comparison.

Existing `#setprivilegedmode` links navigated and positioned the target in
view. `h=привилеги` produced the observed matching `mark[data-md-highlight]`
elements. On std640, Shift+Tab followed by Tab moved focus back to the actual
first diagnostic chip, with `:focus-visible` observed; Enter navigated to its
unchanged OrderOfParams URL. `chip-focus-*.png` records the focused state.

Ten applicable compact/reference code fixtures produced equal clipboard
strings. The original JSON's eleventh fixture, **Mermaid**, has
`passed=false`, `compact=[]`, `reference=[]`, `expectedBlocks=1`. This raw
failure is retained. Its expectation incorrectly assumed that a Mermaid
pre/code becomes a code-copy control. Both actual variants have zero copy
buttons. The scoped rerun `browser-fixture-copy.json` marks this case
**not applicable to clipboard**, with `passed=null`, not true; ten code
fixtures pass. This does not prove Mermaid browser rendering.

The required preservation evidence is independently present: compact and
separated-reference HTML matched exactly in the in-memory fixture test;
with JS disabled both browsers showed the identical
`<pre class="mermaid"><code>graph TD\nA --&gt; B</code></pre>` and visible
`graph TD / A --> B` text between the same surrounding paragraphs.

With JS enabled the supplemental fixture browser produced an empty
`div.mermaid` in **both** variants; no SVG was observed. The first temporary
fixture server also yielded `Uncaught Error: File not found`. A later
fixture-only server supplied real site assets as a fallback; its already
completed diagnostic still found empty Mermaid divs, with no page errors.
Therefore SVG/diagram rendering remains **NOT PROVEN / PARTIAL**; no claim
that Mermaid was successfully replaced by SVG is supported. No product
regression was demonstrated by the equal before/reference behavior, and
no product fix was attempted. Collection was stopped by the parent/controller.
This is not a user waiver of the browser gates; no user answer on no-JS dark
scope has been received.

## Gates, process boundaries and handoff

| Command/probe | Exit | Confirmed result |
|---|---:|---|
| Diagnostic integrity / ACC --check / standard links --check | 0 each | 358 / 691 / 358 |
| Four preservation unittest modules | 0 | 94 tests |
| Renderer + checker focused unittest modules | 0 | 52 tests |
| unittest discover -s tests -v | 0 | 338 tests, 33.775 s |
| Architecture impact | 0 | ARTICLE_HTML and source/code invariant |
| Architecture validate | 0 | Valid candidate graph |
| Architecture validate --merge-ready | 1 | INCOMPLETE_PLAN only |
| Final applicable strict build (pre-browser-strict) | 0 | No issues found; 11.67 s renderer, 36.14 s wrapper |
| Build-integrated and standalone article checker | 0 each | 1429 articles, 0 violations |
| Final source diff / git diff --check | 0 each | Empty output |

The full suite alone used process-scoped `GIT_CONFIG_COUNT=1`,
`GIT_CONFIG_KEY_0=commit.gpgsign`, `GIT_CONFIG_VALUE_0=false` for its Git
fixtures. No permanent Git config was changed. No staging operation was run.
The binary index checksum changed during read-only Git/status/stat refresh;
byte-identical index preservation is **not claimed**. The existing staged
plan remains the only staged path (772 inserted lines); no plan file was
edited by this task. Subsequent Git reads used `GIT_OPTIONAL_LOCKS=0`.

The last strict build restored the full site after serve and preceded browser
checks. All checked product/source/test/config files remained hash-identical
afterward, so it remains applicable at handoff. Per the parent's explicit
instruction, no redundant full suite or strict build was run after browser
collection. This is not a claim of a later build run.

Semantic impact assessment: the verification files collect evidence for the
approved ARTICLE_HTML@1.0 boundary and source/code invariant; they introduce
no product requirement, ADR, contract, compatibility or governed product-path
change. Existing chip contract behavior was exercised. No-JS scope was not
narrowed: the pending user response is still absent. The plan/integration gate
remains the controller's responsibility.

Cleanup: successful serve's own process group was stopped; initial temporary
fixture HTTP server PID 57995 was stopped when replaced. At handoff PID 56154
was positively identified as this task's `python -m http.server 8769 ... site`,
and PID 60329 as this task's fixture server on 8770. Both received SIGTERM and
were absent on the subsequent process check. No unrelated process was killed.
Browser probes finished and closed their isolated contexts. Evidence and the
local Docker image were retained.

Supplemental reproduction scripts are retained in the temporary execution
archive `/tmp/v8std-issue35.pLZSHc/execution/`, not shipped as product files:
`verify-task4.py`
(snapshot/corpus/gates/serve/docker/build/assets/fixtures-server),
`browser-task4.cjs` (matrix), `interactions-task4.cjs` (clipboard/links),
`layout-task4.cjs` (controlled before/after and wheel scroll),
`final-diagnostics-task4.cjs` (header and Mermaid observations). Use the provided
bundled Node with `NODE_PATH` pointing to its `node_modules`; static site
preview uses 8769, temporary fixture server 8770. Only start servers on free
ports and stop the processes started for the reproduction.
Durable renderer/parser regression checks are the committed
`tests/test_v8std_markdown.py` and `tests/test_article_html.py`; temporary
screenshots and probes supplement, rather than replace, those checks.

Remaining review decisions: no-JS-dark scope, six unchanged no-JS header
overflow rows, and unproven Mermaid JS diagram output. Evidence is available
for task review and the controller's broad code review; no integration SHA
or public-site post-deploy evidence exists.

Token telemetry snapshot at 2026-09-09 20:41:11 UTC (before final report text):
2,779,595 cumulative tokens, including 2,669,184 cached input and 24,154 output.
This is a measured intermediate total, not an exact final-turn total.

## Review fix round 1

Bounded verifier/report corrections only; overall result remains **PARTIAL**.
Unexpected gate, full-suite, Docker import/render, build/checker and sidecar
failures now propagate through `main` to a nonzero process exit. Gates collect
all command failures. Only exit 1 with the exact sole expected
`INCOMPLETE_PLAN ...markdown-fence-rendering-plan.md: plan is not complete`
diagnostic is classified separately: `gates-summary.json` says **PARTIAL**,
never PASSED. Other errors alongside it are failures.

The saved Docker render argument now exactly matches the previously successful
`docker-render.json` command, with correct Python newline/quote escaping.
New `docker-runtime` mode checks the existing image without rebuilding it.

Validation: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python
/tmp/v8std-issue35.pLZSHc/test_task4_verifier_fix1.py` — **11 tests, exit 0**.
All external commands were stubbed: tests cover every unexpected gate exit,
exact versus additional/wrong merge-ready diagnostics, mixed failures, both
build/checker exits, Docker build short-circuit, import/render aggregation,
top-level propagation, and exact equality to both prior Docker commands.
Actual corrected `verify-task4.py docker-runtime --label fix1-docker` —
**exit 0**, import **0**, render **0**, rendered **1 article / 0 violations**.
Evidence: `fix1-docker-{import,render}.{json,log}`. Same existing image/runtime;
no build, installation, service, browser matrix or product suite was run.

Both reports now attribute collection closure to the **parent/controller**,
not a user waiver. No-JS dark still requires the unanswered user scope
decision; six unchanged overflows and Mermaid SVG remain partial. No product,
product tests, plan or Git state was modified in this correction round.

Controller handoff: scoped re-review marked all three verifier/report findings
ADDRESSED with no new breakage. Product hashes still match the table above.
Only Task4 Steps 1–3 are marked complete in the candidate plan. Browser scope
and final acceptance remain open; no final whole-branch review or integration
has occurred. The user has not waived the dark/no-JS matrix requirement.

## Pre-review local gates, 2026-09-10

The scope clarification at the top supersedes the historical pending no-JS-dark
decision. All applicable plan steps are complete; broad review remains the
integration gate. No theme or Mermaid feature was added or separately queued.

Product file hashes still equal the six values above. Source/CSS/template/
dependency diff against main is empty. Fresh runs:

| Gate | Exit | Result |
|---|---:|---|
| `VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict` | 0 | 1429 articles, 0 violations; renderer 11.98 s |
| `python -m unittest tests.test_v8std_markdown tests.test_article_html tests.test_diagnostics_registry_js -v` | 0 | 59 tests |
| `python -m unittest discover -s tests -v` after build | 0 | 338 tests, 32.995 s |
| Diagnostic integrity / ACC / relation graph | 0 each | 358 / 691 / 358 |
| Standalone HTML checker | 0 | 1429 articles, 0 violations |
| Architecture impact / normal validate | 0 each | ARTICLE_HTML + preservation invariant; valid graph |
| Source diff / `git diff --check` | 0 each | Empty output |

Python above is `.venv/bin/python`. Full-suite Git fixtures used only the
already documented process-scoped signing override, not a product Git config
change. The first suite was incorrectly launched concurrently with build and
failed its existing published-license test while the site was being replaced;
the sequential full run above passed after all three licenses were published.
No code/test workaround was made. Logs are `final-20260910-{build,fitness,
suite,suite-sequential}.log` in the same temporary evidence directory.

## Final review fix and renewed evidence, 2026-09-10

Whole-branch review found one remaining recognized-fence case: Setext consumed
the marker before `---` and created a false heading instead of code plus hr.
The single fix wave added a narrow priority61 guard before Setext60; the
general normalizer stays at11 and list tree pass at25. Four regression tests
cover compact/reference, ordinary headings, containers, indentation and
idempotence. RED was observed; the 56 renderer/checker tests passed afterward.
Scoped re-review found the issue ADDRESSED and no new breakage or observations.

An independent old-module/new-module comparison rendered all 1428 current
Markdown sources, with reset between pages: zero HTML changes and zero source
changes. Thus existing-page browser and serve observations remain applicable;
they are not claimed as a new browser matrix or a new serve run. The new Setext
input is covered directly by reference-equality tests and the Docker probe.

Only these two hashes differ from the initial six-file table:

| Final file | SHA-256 |
|---|---|
| scripts/v8std_markdown.py | 1c27093958ea164f98f2d68d09da2cf653071b54c524aff195de775bfe206b68 |
| tests/test_v8std_markdown.py | b51bbf93c7e3b530ffdd3d744203f3aba56edb19e9791479d5b12e9df4e5c74a |

Fresh strict build exited0: renderer12.05s,1429articles/0violations,3licenses.
Renewed fitness run exited0:63tests. Docker image was actually rebuilt with
the final module (build exit0), ID
`sha256:21f1e0dcd2f89f3e70e75bf769582a1857bc2c065d18e432e465a92f47c85656`.
Fallback import from `/opt/v8std` confirms the guard exists. The mounted-config
probe asserts exact equality of compact Setext input and separated reference,
presence of hr, absence of h2, and checker `(1, [])`; exit0. Runtime remains
Markdown3.10.3/PyMdown11.0.2/Zensical0.0.47. No MCP service was started.

Supplemental corpus/fix probes are temporary artifacts. To rerun scripts that
resolve ROOT from their placement, restore the archived execution directory to
`spec/operations/issue35-execution/` in a feature checkout first. The shipped
test modules and commands above remain the durable regression entry points.

Final full suite, run sequentially after the last build, exited0:
**342 tests in34.089s, OK** (`post-fix-suite.log`). All plan checkboxes are now
complete. The final scope is still exactly the original rendering repair:
accepted design/ADR/invariants/contracts, source corpus and MCP remain unchanged.
Integration will report its verified SHA separately; publication remains
unauthorized and issue35 must stay open until a public post-publication check.
