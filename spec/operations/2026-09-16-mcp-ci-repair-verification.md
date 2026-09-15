# CI publication repair: local verification

Verified source: `816b592fc6c7911cf5f328f38eda97693e7c973b` (signature G), primary
checkout, branch `codex/mcp-container-distribution-design`. Plan clarification:
`149730d2b81b8255c53ffdd68b0287628cbc08ee`. This report is later documentation,
not a newly built runtime or a live publication.

## Result and approved rule

The three retained CI review findings are fixed: exact-envelope QUEUED remains
pending; COMMITTED publication waits for completed cleanup; missing/expired
history plus404 cannot authorize manifest-less Pages success. The existing
enabled archive-first transaction establishes fresh positive evidence before
Pages, so first publication remains possible with runtime deployment disabled.
No new bootstrap flag, trusted metadata interface or authority is introduced.
The prior initial404 exception is removed from the current execution plans.

The choice applies the already approved UNKNOWN boundary in the tools-only
design: source planning may build a candidate, but cannot claim absence or
permission to publish. Its operational consequence is intentional: without a
verified prior manifest or enabled successful corpus publication, the new Pages
deployment stops and the existing published site stays in place. Were this
sequencing wrong, first-release orchestration would require revision; explicit
enabled-first-publication and disabled-history-loss regressions cover it.

Independent scoped re-review approved all three findings as addressed, with no
new breakage or out-of-scope observations. That approval is scoped to
`149730d..816b592`; it is not the pending whole-branch integration review.

## Checks on the stable source

Runner: `/tmp/v8std-final-gates.e7aqas/venv/bin/python`; repository `.venv`
unchanged. Implementation RED/GREEN, detailed commands and actual helper/CLI
boundary coverage are recorded in the appended CI-fix section of
[container verification](mcp-container-verification.md).

- Publication:48/48 pass, no warnings/skips; RED previously reproduced the
  three errors through positive transition tests and negative file/CLI checks.
- Release and architecture focused run:163/163 pass in220.895s.
- Independent strict build: exit0;3283 vectors,1430 articles,0 violations,
  3 canonical license files. Pinned builder `v8std-final-ci:108b91f`, image ID
  `sha256:cffef3a1b208b462e5f2ca4b9266b1d6ca2c99e031d0170b2c04f1398583a722`;
  network none, user501:20, cap-drop ALL, no-new-privileges.
- Only after strict build exited, full suite on the same source:735 tests in
  361.481s,722 passed/13 skipped,0 failures/errors/warnings. Native nginx
  public-monitoring-retirement tests were explicitly enabled and passed.
- CLI impact against main completed; ordinary architecture validation against
  main and whitespace checks passed. `validate --merge-ready` still reports
  exactly two incomplete parent plans; this scoped repair does not waive them.

Full-suite command:

```sh
V8STD_MONITORING_RETIREMENT_DOCKER=1 /tmp/v8std-final-gates.e7aqas/venv/bin/python -m unittest discover -s tests -v
```

Local raw logs: `/tmp/v8std-ci-fix-gates.ZiEIAe/strict-build.log`,
`full-suite.log`, `impact-main.log`, `merge-ready.log`. No source edits or
concurrent generated-site rebuild occurred during the full suite.

The13 skips remain skips:5 opt-in image/build checks,4 native-root logging
checks,2 logging Docker checks and2 release Docker checks. Their separate prior
fixture evidence is not relabelled as this run's passes or live-host acceptance.

## Artifact identity and remaining boundary

The actual input identity helper confirms both identities on816b592 equal the
tested tools-only candidate `c4c0878a3c5e12323358f139e070253bd9e8ac5a`:

- runtime `9f580a029745e00395e4a49b1e79c9f1d4ee0f9f6c583d614f5ac02abfa1e35a`;
- corpus `021a01ae0e5c06eac49f1625c9a3b06b5e3619535f9f1f1216f3059e49a14f08`.

Thus the [retained candidate proof](2026-09-15-mcp-tools-only-verification.md)
still applies to those artifact inputs; no old image was relabelled and no new
image was claimed. CI-helper behavior is covered by this turn's tests instead.

Whole-branch review and parent-plan completion remain pending. No merge, push,
registry/Pages publication, production deployment/setup, GitHub setting/secret
change, Docker Catalog submission, PR closure or public comment occurred.
No production capacity or100000-agent support claim follows from these tests.
