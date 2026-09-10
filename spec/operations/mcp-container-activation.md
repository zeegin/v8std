# Controlled initial activation of container delivery

**Status:** prerequisite checklist; host-controller commands and rehearsal
evidence are completed by the release implementation task. This document does
not authorize a live operation, enable CI, or establish current host capacity.

## Authority and stop conditions

Initial activation requires an explicit operational request for the exact
verified main SHA and published image digest. Until then, leave production,
secrets, branch rules, environment settings and unrelated hosted services alone.
The ordinary automatic path starts only after initial rollback has been proven.

Stop before any switch if the backup cannot be restored, the source manifest
is not reachable, the image/provenance/configuration is unverified, capacity is
insufficient, the predecessor is missing, or the restricted controller cannot
reconcile a crash. A healthy systemd wrapper is not application readiness.

## Host inventory and backup gate

- Refresh the actual target host identity, OS, CPU/RAM/swap, available disk,
  file descriptors, network budget, running services, containers and listeners.
  Prior incident measurements are historical, not current capacity evidence.
- Identify the precise nginx virtual hosts, includes, default server, certificate
  paths and renewal hooks. Ensure the ai.v8std.ru TLS endpoint and renewal no
  longer depend on an old site's configuration before any cleanup.
- Preserve SSH access, monitoring, fail2ban and certificate renewal. Removing an
  old website is not permission to remove unrelated operating services.
- Back up the existing Python runtime, environment/dependencies, unit/drop-ins,
  nginx configuration, working corpus/cache and certificate configuration to
  protected off-host storage. Keep secrets out of repository and public logs.
- Restore into a disposable environment and exercise the old endpoint. Record
  exact cleanup targets and recovery instructions; obtain the operational
  approval before removing or disabling them. Prefer recoverable moves.

## CI and restricted-host gate

- Protect main and require the actual validation checks used by this workflow.
  Audit bypass permissions; a branch name alone is not an authorization check.
- Restrict the production environment to verified main releases. PRs, forks,
  tags, untrusted inputs and stale runs must not obtain host credentials.
- Establish a restricted release identity and a separately constrained static
  artifact publisher. Neither credential grants arbitrary shell commands,
  arbitrary paths/environment variables, root login or Docker group access.
- Install and verify the trusted host controller, its fixed configuration,
  attestation verifier, bounded job supervision and durable journal/recovery.
  Ordinary release envelopes cannot replace their own trust policy.
- Keep automatic runtime switching disabled until the initial published-image
  cutover and predecessor recovery are demonstrated. Test the kill switch: it
  blocks new releases without interrupting an in-flight rollback.

## Artifact and bootstrap ordering gate

Use the same published runtime digest later supplied to local users and the
Catalog. Do not rebuild a special production image on the server.

1. Verify the main source SHA, published multi-platform index digest,
   host-platform child membership, publisher identity and configuration digest.
2. Install the independent nginx index store and publish the verified immutable
   archive under its hash before publishing a manifest that references it.
3. Publish the site's manifest and verify its actual public source URL and
   archive bytes. A successful Pages job alone is insufficient to prove freshness.
4. Verify the public-default thin image against that manifest before stable
   promotion or the first container switch. Before this bootstrap, candidate
   builds are not a usable public-default release.
5. Exercise the candidate on its private loopback port, with exact runtime SHA
   and corpus ID, real MCP calls and static downloads while the runtime stops.
6. Perform the initial controlled cutover while retaining the tested Python
   predecessor. Do not manufacture a Docker predecessor or claim rollback from
   an empty release history. Establish the first verified container predecessor
   before enabling ordinary automated transactions.

## Capacity and acceptance gate

Measure old runtime + candidate + snapshot preparation together, including
Docker/OS overhead and static index traffic. Verify memory, disk staging and
pins, descriptors, CPU and bandwidth before switching. Raise capacity or change
the accepted rollout design if the measured host cannot accommodate overlap;
do not silently kill the predecessor to make room.

Exercise initialized idle agents, normal POST tool calls, reconnects, shared NAT,
snapshot refresh and concurrent archive downloads. Record the actual mix,
duration, error rate and latency. Neither worker_connections nor idle TCP count
proves support for 100,000 coding agents.

Record the initial release journal, exact SHA/digests/corpus/configuration,
public MCP/TLS and static delivery results, failure/rollback rehearsal and
monitoring checks in the verification record. External Catalog acceptance and
closure of the alternative PR remain separate delivery outcomes.
