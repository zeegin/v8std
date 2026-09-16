---
schema_version: 1
kind: plan
id: mcp-host-provisioning
design: design:mcp-clean-host-installation
implements: []
---

# MCP Host Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Подготовить повторяемую установку выделенного MCP host и проверку его готовности к отдельному первому запуску.

**Architecture:** Операторский provision CLI строит проверяемый fixed-path manifest и применяет его с durable журналом. Package/TLS effects отделены от bounded runtime transaction. Никакой переустановки ОС, публикации или включения runtime CI в provisioner нет.

**Tech Stack:** Ubuntu 24.04 amd64, Python 3.12 stdlib, Docker Engine/Compose/buildx, nginx, Certbot webroot, systemd, OpenSSH, GitHub CLI, unittest.

**Spec:** [Clean-host design](../designs/2026-09-16-mcp-clean-host-installation-design.md), [runtime contract](../contracts/mcp-release-runtime-v1-r1.md), [release policy](../designs/2026-09-16-mcp-clean-host-release-policy-design.md).

## Global Constraints

- Только основной checkout и feature-ветка; в ходе реализации не изменять реальный host, GitHub settings, registry, доступы или production.
- Root-only plan/apply/check/prepare-runtime, не publisher PUBLIC/sudoers. Никаких shell/env/mount команд из входного JSON.
- Поддерживаемая ОС — чистая Ubuntu 24.04 x86_64; неизвестный существующий файл, symlink, контейнер, сервис или изменённый managed artifact блокирует apply.
- Повтор на том же собственном состоянии не сбрасывает journals, cache, usage history, publication sequence, TLS identity или runtime policy.
- Первоначально MCP maintenance 503/Retry-After, monitoring 410/no-store, runtime_enabled=false; static delivery не зависит от контейнера.
- Пять tools, JSON POST, no Resources, один SITE_URL и постоянный cache не меняются.
- Секреты устанавливаются отдельной операторской процедурой и не печатаются, не берутся из личного HOME, не входят в Git/handoff/image/web root.
- Нет reinstall/wipe API, Docker prune, удаления чужих vhosts, обхода SSH/TLS verification или автоматической покупки ресурсов.
- До остановки production нужен отдельный человеческий gate после уведомления пользователей. Локальная реализация этот gate не проходит.
- TDD RED/GREEN; host-boundary effects заменяются только в filesystem/process fixtures. Реальные nginx routes дополнительно проверяются в непривилегированном disposable контейнере, без host socket.

## File boundaries

`v8std_mcp_provision.py` — root-only CLI (расширение handoff CLI).
`v8std_mcp_host.py` — manifest, safe managed paths, durable provisioning stages
и subprocess adapter. `deploy/container/host-*` — fixed templates. Shared release
helpers используются напрямую; не копировать parsing/atomic/command routines.
Не строить универсальную систему configuration management или пакетный менеджер.

### Task 1: Implement replayable host installation and readiness

**Files:**

- Create: `scripts/v8std_mcp_host.py`, `tests/test_v8std_mcp_provision.py`.
- Modify: `scripts/v8std_mcp_provision.py` (handoff commands preserved).
- Create: `deploy/container/host-nginx.conf`, `deploy/container/host-http.conf`, `deploy/container/host-tls.conf`, `deploy/container/host-nginx.service.conf`, `deploy/container/host-usage.logrotate`, `deploy/container/host-certbot-deploy`, `deploy/container/host-input.schema.json`.
- Create: `spec/operations/2026-09-16-mcp-clean-host-installation.md` (generic runbook, no live facts or private values).
- Read/reuse: existing edge-http/edge-locations, release-entry/sudoers, release recovery timer/service, release policy validator and initial-install constants, handoff helpers.

**Interfaces:**

```python
def validate_inputs(raw: bytes) -> dict: ...
def plan_host(source: Path, inputs: dict, adapter) -> dict: ...
def apply_host(source: Path, inputs: dict, expected_plan_sha256: str, adapter) -> dict: ...
def check_host(adapter) -> dict: ...
def prepare_runtime(envelope: dict, adapter) -> dict: ...
```

CLI `plan --source DIRECTORY --inputs FILE`,
`apply --source DIRECTORY --inputs FILE --plan-sha256 HEX`, `check`,
`prepare-runtime --envelope FILE`. No host-root, shell, command or arbitrary target
path options. All modes require root. Validate source/input ownership and every
parent; source tree supplies exact Git blobs from `source_sha`, not mutable working
files. Source SHA must be a full 40-hex commit reachable from its local main;
before accepting installed controller, verify current upstream main ancestry with
the dedicated GitHub verifier. No production source build.

Input exact fields: schema_version=1, source_sha, policy (existing policy schema,
enabled=true and runtime_enabled=false, nonempty configs, linux/amd64),
publisher_public_key (one ssh-ed25519 key, no options/comments/newlines), tls_email
(single valid address), ssh_port (integer 1..65535). No access token or private key.
Input remains a root-owned 0600 operator file outside Git. Plan does not echo key,
email, credentials or machine inventory: returns path/action/content digest/mode,
bounded package/service action IDs, required prerequisites and plan_sha256.
Plan hash binds source SHA, full input hash, exact template bytes and desired
operations, not changing timestamps or whether a step is already complete.

`HostProvisionAdapter` owns a fixed filesystem root for production; tests inject
a disposable adapter. Commands always argv with fixed executable allowlist and
bounded deadline/output, no shell. Production has no root override. A single
root-owned `/var/lib/v8std-release/provision.json` keeps schema_version,
source_sha, input_sha256, plan_sha256, state PREPARED/COMMITTED, completed stage
IDs, owned file digests/modes and installed package versions. Journal before
effects; resume the same identity after interruption, reject another plan/source
instead of overwriting. Existing fully installed state allows read-only check,
but apply refuses while runtime accepted or enabled so it cannot reset upstream.

- [ ] **Step 1: Behavioral RED for plan, replay and safe conflicts.**

Use a synthetic Git repository with main and exact allowlisted source blobs, a
temporary filesystem root and adapter that emulates apt/systemd/Certbot effects
but performs real file writes/checks. All expectations are hand-derived, not
generated by plan_host on both sides.

```python
plan = plan_host(source, inputs, adapter)
self.assertFalse(adapter.effects)
apply_host(source, inputs, plan['plan_sha256'], adapter)
self.assertEqual(read_record(root / 'var/lib/v8std-release/provision.json')['state'], 'COMMITTED')
self.assertFalse(read_record(root / 'etc/v8std-release/policy.json')['runtime_enabled'])
usage = root / 'var/log/v8std-mcp/tool-usage.jsonl'
usage.write_bytes(b'preserved-history\n')
apply_host(source, inputs, plan['plan_sha256'], adapter)
self.assertEqual(usage.read_bytes(), b'preserved-history\n')
```

Prove conflict/symlink/mismatching source/plan hash, unsupported OS/arch,
foreign vhost/container/listener/user, wrong file ownership, invalid key/inputs,
non-root caller and enabled runtime all reject before destructive effects.
Check no runtime acceptance/journal/predecessor or publisher broad permission is
created by setup. Fixture setup writes are not production provisioning evidence.

- [ ] **Step 2: Observe RED.**

Run `python -m unittest tests.test_v8std_mcp_provision -v` using verified locked
runtime dependencies. Record missing behavior, not an unrelated import error.

- [ ] **Step 3: Implement fixed manifest and safe package/service stages.**

Read `/etc/os-release`, architecture, effective SSH listener port, current nginx
configuration/service, installed packages and Docker inventory before applying.
Existing v8std install accepts only exact recorded digests/modes; foreign active
services or nonbaseline web listeners fail. Check input ssh_port matches actual
administrative SSH listener before firewall changes. Never alter sshd or host keys.

Packages: Ubuntu python3/git/ca-certificates/curl/gnupg/nginx/certbot/logrotate/
sudo/ufw; Docker official apt repository supplies docker-ce/docker-ce-cli/
containerd.io/docker-buildx-plugin/docker-compose-plugin; GitHub official apt
repository supplies gh with attestation support. Fail on conflicting Docker
packages instead of uninstalling them. Fetch keys only by bounded HTTPS to their
official fixed URLs; keep signed-by scoped repository files, record key/package
identity. Replays do not upgrade existing recorded packages automatically.
Do not run convenience install scripts or fetch executable code from input URLs.

Install reviewed Python files into `/opt/v8std-release/scripts/`: release,
snapshot_format, chunks, provision, handoff and host modules; include the forced
entry as `/opt/v8std-release/release-entry.py`. Root-owned directories 0755/code
0644 (entry 0755), configuration 0600, release state 0700. Use exact git blobs
after content validation, no recursive source-tree copy. Create static directories
0755 and private usage directory 0700/file uid 10001,gid 0,mode0640 through shared
helper; never truncate or replace an existing valid usage file. Logs rotation
contains only `/var/log/v8std-mcp/tool-usage.jsonl`, not legacy paths.

Create system account v8std-publisher without password, without Docker/sudo groups
and without writable release files. SSH needs a valid shell for forced command;
use `/bin/sh` plus root-owned authorized_keys with `restrict,command=...` and an
sshd Match block (AllowTcpForwarding no, X11Forwarding no, PermitTTY no,
PermitUserRC no, ForceCommand exact entry). Validate `sshd -t` before reload.
No general shell/SFTP: exact forced entry and exact sudoers allowlist determine
authority. Install sudoers only after `visudo -cf` validates its staged bytes.
Existing user/group conflicts deny adoption; durable user-creation intent makes
interruption replay distinguish its own account from a pre-existing one.

Use `/etc/nginx/nginx.conf` from host-nginx template: worker_processes auto,
worker_rlimit_nofile 131072 in main context, worker_shutdown_timeout30s, events
worker_connections65536, http includes mime types, bounded keepalive30s/1000,
private access/error logs and the managed edge-http/server includes only. This
does not claim 100000-user capacity. Existing custom config rejects; package
default generated during this own install may be replaced only when dpkg
identifies its unmodified shipped bytes. Preserve a root-private copy/digest
in provisioning state. Never enumerate/delete unrelated vhosts.

Templates target only product domain ai.v8std.ru. HTTP initially provides ACME
webroot `/var/lib/v8std-acme`, maintenance/static/monitoring routes; once TLS is
issued, normal non-ACME HTTP redirects to HTTPS. TLS server includes existing
edge-locations, TLS1.2/1.3 and certbot live paths; unknown paths return404. Include
`release.MAINTENANCE_UPSTREAM` at fixed policy path. nginx systemd drop-in sets
LimitNOFILE131072; release recovery units are the existing reviewed units.

Firewall stage uses ufw incoming deny/outgoing allow, allows the verified SSH
port and TCP80/443; reject unexpected pre-existing rules rather than flushing.
Docker exposure remains loopback-only in existing release start; verify no other
published external ports. Do not claim ufw alone filters Docker published ports.
All planned files and package/firewall/service side effects appear in plan output.

- [ ] **Step 4: TLS, service identity and preparation gates.**

Certbot uses webroot certonly, noninteractive explicit agreement, product domain,
private input email and bounded invocation, not nginx's automatic config rewrite.
Existing certificate state is reusable only after product hostname/issuer/expiry
validation and matching managed renewal profile; unexpected certificate symlinks
outside standard certbot archive layout reject. Enable certbot.timer and install
fixed executable deploy hook `nginx -t && systemctl reload nginx`; these fixed
shell statements contain no input interpolation. Verify timer and certificate
with real commands; failure leaves managed maintenance and resumable journal.

Service verifier credentials are created separately under the fixed release HOME
by the operator, not copied from their personal account. check reports controlled
missing-auth code if gh attestation, upstream main access or registry verification
fails; no raw output or credential echo. Runtime CI remains disabled regardless.
Before apply, operator may create only the standard root-private gh/Docker
credential files under that HOME. Preflight explicitly recognizes those owned
credential paths without reading their content into the plan or journal; they
are not a foreign publication/runtime store. Missing credentials may permit
package staging, but prevent final source verification and COMMITTED setup.
Re-running apply after the separate credential step resumes its own journal.

`prepare-runtime` requires COMMITTED provision and COMMITTED handoff import,
exact matching runtime artifact identity (source/index/platform/config/corpus,
not expired release ID/deadline), confirmed maintenance/TLS/static hashes, trusted
policy and provenance. It pulls only exact published platform digest, verifies
local image/config and corpus, and reports PREPARED without authorizing or starting
initial-install. No build/push. New root-owned initial-install authorization and
fresh major-1 deadline remain separate operator actions in runbook.

`check` verifies actual installed file identities, services/timers, effective
limits, restricted SSH/sudo, live TLS/maintenance/410/static behavior and verifier
readiness. Partial setup never reports READY merely from the provision journal.

- [ ] **Step 5: GREEN, interruption and real route checks.**

Run `python -m unittest tests.test_v8std_mcp_provision tests.test_v8std_mcp_handoff tests.test_v8std_mcp_initial_install tests.test_v8std_mcp_release -v`.
Inject crash after each stage and uncertain journal persistence, rerun same plan
and verify no unrelated changes or lost data. Verify all spawned programs are
bounded and separate auth failures from filesystem conflicts. Cover pre-existing
package nginx defaults versus custom bytes and correct main/http directive scope.

Use a local cached nginx image in an explicitly named, unprivileged disposable
container to run generated config and real POST/GET/static/monitoring requests.
No pull, Docker socket, host root mount, host network or privileged mode. Generate
temporary self-signed TLS only inside fixture; tests trusting that test certificate
do not change production TLS checks. Assert maintenance503/Retry-After,
monitoring410/no-store, static exact hash and unknown404; execute nginx -t.
Clean only owned test resources. If local image unavailable, record that gate
incomplete rather than claim success from source-text assertions.

- [ ] **Step 6: Write operator runbook and independent review.**

Document exact CLI/input field sequence, plan hash verification, fixed locations,
service credentials as separate private action, signed artifact prerequisites,
handoff off-host checksum, and separate authorization/deadline for initial-install.
Keep explicit stop-notice gate before OS reinstall, SSH key check through trusted
console, production smoke and disabled automatic rollout until old/new capacity
and rollback acceptance. Include Docker Catalog preparation/submission/visibility
as separate external deliverables; no fake digest or claim of publication.
Record failure/retry semantics and which local checks actually ran.

## Integration evidence

- [ ] Repeat semantic impact and architecture fitness, strict build and complete suite on the final combined clean-host candidate, after scoped review.

Этот локальный план не доказывает доступность production, выданный TLS сертификат,
фактический перенос данных, производительность host или публикацию в Catalog.

## Primary installation references

[Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/),
[GitHub CLI Linux installation](https://github.com/cli/cli/blob/trunk/docs/install_linux.md),
[Certbot webroot/renewal](https://eff-certbot.readthedocs.io/en/stable/using.html),
[Ubuntu Noble Certbot package](https://packages.ubuntu.com/noble/certbot).
Package acquisition follows signed repositories; verify current command support
during actual preparation instead of assuming the distribution gh is sufficient.
