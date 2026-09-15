---
schema_version: 1
kind: plan
id: mcp-public-monitoring-retirement
design: design:mcp-public-monitoring-retirement
implements:
  - design:mcp-public-monitoring-retirement
  - adr:RETIRE_PUBLIC_MCP_MONITORING
  - invariant:PUBLIC_MONITORING_ROUTES_ARE_GONE
  - invariant:PRIVATE_OPERATIONAL_DATA_IS_NOT_PUBLISHED
  - contract:MCP_MONITORING_PROJECTION@3.0
  - contract:MCP_USAGE_EVENTS@1.1
---

# Public monitoring retirement implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove public monitoring without disturbing MCP or private operational evidence.

**Architecture:** Retire producer and public artifacts; nginx keeps explicit410 tombstones. Preserve private logging and the independent release controller. Record recoverable production retirement separately from MCP deployment.

**Tech Stack:** Python unittest, nginx, systemd, SSH, local Docker fixture.

**Spec:** `spec/designs/2026-09-15-mcp-public-monitoring-retirement-design.md`

## Global Constraints

- HTTPS `/monitoring` and all `/monitoring/` return410 with `Cache-Control: no-store`.
- Do not restart/deploy MCP, push, publish Docker, remove logs/rotation or alter other vhosts/TLS/SSH/fail2ban.
- Production removal is separately authorized by the user's2026-09-15 confirmation; preserve root-owned0700 archive outside web root.
- No new dashboard, sampler or monitoring privileges. Private logger and health/readiness remain.
- Main structured documents remain byte-identical; change their lifecycle through successors.
- Existing container plan remains incomplete; this retirement does not authorize integration of the whole branch.

## Operational execution (controller, separate from implementation checkboxes)

1. Capture public410-vs-current regression, MCP health/PID/start, exact nginx realpath and units.
2. Create root-only archive with `mktemp -d /root/v8std-monitoring-retired-XXXXXXXX`; copy original nginx config there. Disable/stop exact timer and service.
3. Patch only the two existing monitoring locations to the410 fragment below using a local candidate and `apply_patch`; transfer it into the archive. Validate exact original checksum before installing. Run `nginx -t`; if it fails restore original config without reload. Reload nginx only after successful validation.
4. Move the exact monitoring units/drop-in, generator and web directory into the archive; daemon-reload; mask both retired units. Do not remove the harmless legacy MCP Before= dependency or restart its process.
5. Verify GET/HEAD410/no-store for exact/slash/JSON/query/unknown child paths; masked inactive units, absent public directory and renderer; original MCP PID/start, health and initialize/tools/list. Check raw-log modes/rotation unchanged. Record archive path and commands in operations evidence without raw log or dashboard contents.

### Task 1: Remove the publication path and lock the retired HTTP boundary

**Files:** Delete `scripts/v8std_mcp_monitoring.py`, `tests/test_v8std_mcp_monitoring.py`; modify `deploy/container/edge-locations.conf`, `tests/test_v8std_architecture_repository.py`; create `tests/test_v8std_mcp_monitoring_retirement.py`.

**Interfaces:** Consume the shipped `edge-locations.conf` using a real local nginx fixture (pinned local nginx image from `tests/test_v8std_mcp_release_docker.py`); produce opt-in HTTP conformance with `V8STD_MONITORING_RETIREMENT_DOCKER=1`. No host SSH or production work in the subagent.

- [ ] **RED:** Start a disposable nginx with shipped include, bounded timeouts, dead upstream, legacy `monitoring/index.html` and `stats.json` containing a sentinel under fixture root. Probe GET/HEAD paths `/monitoring`, `/monitoring/`, `/monitoring/stats.json?x=1`, `/monitoring/unknown`. Assert literal410/no-store and absent sentinel. Before implementation existing config fails this boundary. Use loopback-only published port and exact UUID-owned container cleanup; never prune or pull. Preserve health/index boundaries in the fixture. Add architecture lifecycle expectations that old dashboard/input designs are superseded and OpenMetrics remains accepted.

```python
self.assertEqual(status, 410)
self.assertEqual(headers.get('cache-control'), 'no-store')
self.assertNotIn(b'private-monitoring-sentinel', body)
```

- [ ] **GREEN:** Remove generator and its dedicated tests; leave logger/server/logrotate unchanged. Add these locations to shipped include. Update architecture repository expectations for the successor graph; preserve historical aliases.

```nginx
location = /monitoring {
    add_header Cache-Control "no-store" always;
    return 410;
}
location ^~ /monitoring/ {
    add_header Cache-Control "no-store" always;
    return 410;
}
```

- [ ] **VERIFY:** Run real nginx conformance and existing private logger tests. Record RED/GREEN output and prove owned fixture cleanup. Search active publication surfaces for remaining renderer/monitoring links; no source-text-only substitute for HTTP behavior.

```sh
V8STD_MONITORING_RETIREMENT_DOCKER=1 .venv/bin/python -m unittest tests.test_v8std_mcp_monitoring_retirement -v
.venv/bin/python -m unittest tests.test_v8std_mcp_server tests.test_v8std_architecture_repository -v
```

### Task 2: Reconcile release obligations and record evidence

**Files:** Modify candidate-only `spec/plans/2026-09-10-mcp-container-distribution-plan.md`, `spec/designs/2026-09-10-mcp-container-distribution-design.md`, `spec/operations/mcp-container-activation.md`, `spec/operations/mcp-container-verification.md`, `spec/operations/mcp-first-container-release-roadmap.md`; create `spec/operations/2026-09-15-public-monitoring-retirement.md`.

**Interfaces:** Consume Task1 tests and controller's actual production evidence. Produce unambiguous current runbooks, retaining dated historical observations as history.

- [ ] Replace the container plan's public-monitor preservation step with retirement evidence plus persistent private logging/rotation checks for the new runtime (remaining incomplete until actually verified). Remove generator/tests from active test commands; replace with retirement conformance. Do not claim new container telemetry has been implemented.
- [ ] Clarify preserve-monitoring prose to mean private logs and health/readiness; link the retirement decision for old dated statements. Record exact production archive/PID/codes/unit states with no payloads. Scan `docs`, `.github`, `deploy`, scripts and current runbooks; historical frozen design references remain as evidence, not active instructions.
- [ ] Run semantic impact and ordinary architecture validation, strict build then full suite once. Record existing whole-branch release gates separately; no merge-ready or production-release claim from this scoped completion.

```sh
.venv/bin/python scripts/v8std_architecture.py impact --root . --base-ref main
.venv/bin/python scripts/v8std_architecture.py validate --root .
VIRTUAL_ENV="$PWD/.venv" ./scripts/zensical_docs.sh build --strict
.venv/bin/python -m unittest discover -s tests -v
```
