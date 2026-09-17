"""Clean-host acceptance: real journals, runtime, MCP smoke and crash recovery."""
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from tests.mcp_release_fixture import release
from tests.mcp_initial_install_fixture import HostFixture, InitialAdapter, ROOT


class InitialInstallTests(unittest.TestCase):
    def setUp(self):
        self.host = HostFixture()
        self.addCleanup(self.host.close)
        self.root, self.env, self.adapter = self.host.root, self.host.env, self.host.adapter
        self.boundaries = self.adapter.boundaries()
        self.boundaries.__enter__()
        self.addCleanup(self.boundaries.__exit__, None, None, None)
        self.initial = release.InitialInstallController(self.root, self.adapter)

    def submit(self, env=None):
        return self.initial.submit(release.canonical_json(env or self.env))

    def journal(self):
        return release.read_record(self.root / "releases" / (self.env["release_id"] + ".json"))

    def assert_static(self):
        status, _, raw = self.host.request("/indexes/v1/" + self.env["archive_sha256"] + "/snapshot.tar.gz")
        self.assertEqual(status, 200)
        self.assertEqual(release.digest(raw), self.env["archive_sha256"])

    def assert_maintenance(self):
        status, headers, _ = self.host.request("/mcp", "POST")
        self.assertEqual(status, 503)
        self.assertEqual(headers.get("Retry-After"), "1")
        self.assert_static()

    def assert_failed(self, result):
        self.assertEqual(result["state"], "FAILED", result)
        self.assertTrue(result["cleanup_complete"], result)
        self.assert_maintenance()
        candidate = self.journal().get("candidate")
        info = self.adapter.inspect(candidate, time.monotonic() + 2) if candidate else None
        self.assertTrue(info is None or info["State"]["Running"] is False)
        self.assertFalse((self.root / "active.json").exists())
        self.assertFalse((self.root / "predecessor.json").exists())

    def assert_accepted(self, result):
        self.assertEqual(result["state"], "COMMITTED", result)
        self.assertTrue(result["cleanup_complete"], result)
        active = release.read_record(self.root / "active.json")
        for field in ("release_id", "runtime_source_sha", "image_digest", "platform_digest",
                      "configuration_digest", "corpus_id", "archive_sha256"):
            self.assertEqual(active[field], self.env[field])
        status, _, raw = self.host.request("/healthz")
        self.assertEqual(status, 200)
        health = json.loads(raw)
        self.assertEqual(health["runtime_sha"], self.env["runtime_source_sha"])
        self.assertEqual(health["archive_sha256"], self.env["archive_sha256"])
        self.assertIsNone(health["hold_token"])
        self.assertFalse((self.root / "predecessor.json").exists())
        self.assertFalse(self.adapter.policy["runtime_enabled"])
        self.assert_static()

    def invoke(self, fault="", mode="execute"):
        code, raw, error = self.host.invoke(fault, mode)
        self.assertEqual(code, -signal.SIGKILL if fault.startswith("kill_") else 0, error.decode())
        return self.initial.status() if fault.startswith("kill_") else json.loads(raw)

    def test_clean_host_acceptance_and_lost_pointer_recovery(self):
        self.assert_maintenance()
        self.assertEqual(self.submit()["state"], "RECEIVED")
        self.assert_accepted(self.initial.execute())
        self.assertNotIn("predecessor", self.journal())
        self.assertEqual(release.read_record(self.root / "pins.json"), {"archives": [self.env["archive_sha256"]]})
        (self.root / "active.json").unlink()
        self.assert_accepted(release.Controller(self.root, self.adapter).recover())

    def test_root_cli_accepts_and_recovers_same_durable_transaction(self):
        self.assertEqual(self.invoke(mode="cli_submit")["state"], "RECEIVED")
        self.assert_accepted(self.invoke(mode="cli_execute"))
        (self.root / "active.json").unlink()
        self.assert_accepted(self.invoke(mode="cli_recover"))

    def test_duplicate_even_expired_is_immutable_and_new_id_cannot_bypass_acceptance(self):
        self.submit()
        result = self.initial.execute()
        with patch.object(release.time, "time", return_value=self.env["deadline"] + 1):
            self.assertEqual(self.submit(), result)
        with self.assertRaisesRegex(release.ReleaseError, "mutated_duplicate"):
            self.submit(self.env | {"trigger_sha": "f" * 40})
        (self.root / "active.json").unlink()
        next_env = self.env | {"release_id": "release-2", "sequence": 2}
        self.host.authorize(next_env)
        with self.assertRaises(release.ReleaseError):
            self.submit(next_env)
        self.assertEqual(self.journal()["state"], "COMMITTED")

    def test_received_recovery_fails_closed_and_higher_sequence_can_retry(self):
        self.submit()
        self.assert_failed(release.Controller(self.root, self.adapter).recover())
        with self.assertRaisesRegex(release.ReleaseError, "stale_sequence"):
            self.submit(self.env | {"release_id": "stale"})
        retry = self.env | {"release_id": "release-2", "sequence": 2}
        self.host.authorize(retry)
        self.assertEqual(self.submit(retry)["state"], "RECEIVED")

    def test_schedule_failure_leaves_receipt_for_fail_closed_recovery(self):
        self.adapter.fault = "schedule_failure"
        with self.assertRaises(release.ReleaseError):
            self.submit()
        self.assertEqual(self.journal()["state"], "RECEIVED")
        self.adapter.fault = ""
        self.assert_failed(release.Controller(self.root, self.adapter).recover())

    def test_runtime_policy_authorization_and_ownership_rechecked_at_execute(self):
        self.submit()
        self.adapter.policy["runtime_enabled"] = True
        self.assert_failed(self.initial.execute())
        self.assertFalse((self.root / "processes").exists())

    def test_authorization_changed_after_submit_cannot_start_candidate(self):
        self.submit()
        self.host.authorize(self.env | {"trigger_sha": "f" * 40})
        self.assert_failed(self.initial.execute())
        self.assertFalse((self.root / "processes").exists())

    def test_dirty_host_after_submit_cannot_start_candidate(self):
        self.submit()
        release.atomic(self.root / "slots/foreign/data", b"untouched")
        self.assert_failed(self.initial.execute())
        self.assertEqual((self.root / "slots/foreign/data").read_bytes(), b"untouched")
        self.assertFalse((self.root / "processes").exists())

    def test_foreign_host_is_rejected_before_receipt_or_runtime_effects(self):
        cases = {"legacy-app": b"old", "legacy-config": b"old", "legacy-data": b"old",
            "legacy-unit-present": b"old", "active.json": b"{}", "predecessor.json": b"{}",
            "pending-deploy.json": b"{}", "releases/corrupt.json": b"broken",
            "slots/foreign/data": b"old"}
        for name, raw in cases.items():
            with self.subTest(name=name):
                path = self.root / name
                release.atomic(path, raw)
                with self.assertRaises((release.ReleaseError, OSError, KeyError)):
                    self.submit()
                path.unlink()
                if name.startswith("slots/"):
                    path.parent.rmdir()
                self.assertFalse((self.root / "releases/release-1.json").exists())
                self.assertFalse((self.root / "processes").exists())
        release.atomic(self.root / "upstream.conf", b"server 127.0.0.1:8123;\n")
        with self.assertRaises(release.ReleaseError):
            self.submit()
        self.assertEqual((self.root / "upstream.conf").read_bytes(), b"server 127.0.0.1:8123;\n")

    def test_foreign_container_or_inspection_error_never_means_empty(self):
        for info in ({"Config": {"Image": "foreign/app", "Labels": {}}, "State": {"Running": False}},
                     {"Config": {"Image": release.IMAGE + "@" + self.env["platform_digest"], "Labels": {}},
                      "State": {"Running": True}}):
            release.write_json(self.root / "foreign-containers.json", {"v8std-release-foreign": info})
            with self.assertRaises(release.ReleaseError):
                self.submit()
        (self.root / "foreign-containers.json").unlink()
        self.submit()
        self.invoke("kill_after_start")
        self.adapter.fault = "inspect_error"
        result = release.Controller(self.root, self.adapter).recover()
        self.assertEqual(result["state"], "RECOVERY_REQUIRED")
        self.assertFalse(result["cleanup_complete"])
        self.adapter.fault = ""
        self.assert_failed(release.Controller(self.root, self.adapter).recover())

    def test_noninitial_and_unknown_historical_journals_do_not_authorize_install(self):
        for kind, state, cleaned in (("bootstrap", "FAILED", True), (None, "FAILED", True),
                                     ("initial-install", "UNKNOWN", True), ("initial-install", "FAILED", False)):
            old = {"kind": kind, "envelope": self.env | {"release_id": "old"}, "state": state,
                   "intent": "complete", "cleanup_complete": cleaned, "candidate": None}
            release.write_json(self.root / "releases/old.json", old)
            with self.assertRaises(release.ReleaseError):
                self.submit(self.env | {"sequence": 2})
            (self.root / "releases/old.json").unlink()
        self.assertFalse((self.root / "processes").exists())

    def test_initial_authorization_binds_exact_payload_and_no_extra_authority(self):
        path = self.root / "authorization.json"
        good = release.read_record(path)
        for change in ({"schema_version": True}, {"mode": "bootstrap"}, {"envelope_sha256": "0" * 64},
                       {"allow_no_predecessor": 1}, {"allow_no_predecessor": False}, {"command": "id"}):
            release.write_json(path, good | change)
            with self.subTest(change=change), self.assertRaises(release.ReleaseError):
                self.submit()
        release.write_json(path, good)
        self.assertIsNone(self.adapter.initial_authorization(self.env))
        self.adapter.policy["runtime_enabled"] = True
        with self.assertRaises(release.ReleaseError):
            self.submit()

    def test_partial_or_corrupt_handoff_import_blocks_activation(self):
        good = {"schema_version": 1, "handoff_sha256": "a" * 64, "state": "COMMITTED", "publication_sequence": 20}
        path = self.root / "handoff-import.json"
        for value in (good | {"state": "PREPARED"}, good | {"handoff_sha256": "bad"},
                      good | {"publication_sequence": True}, good | {"schema_version": True}, {}):
            release.write_json(path, value)
            with self.subTest(value=value), self.assertRaises(release.ReleaseError):
                self.submit()
        release.atomic(path, b"broken")
        with self.assertRaises(release.ReleaseError):
            self.submit()
        release.write_json(path, good)
        self.assertEqual(self.submit()["state"], "RECEIVED")

    def test_preloaded_verification_failures_leave_maintenance(self):
        for fault in ("attestation", "ancestry", "descriptor", "image_missing"):
            with self.subTest(fault=fault):
                self.submit()
                self.adapter.fault = fault
                self.assert_failed(self.initial.execute())
                self.adapter.fault = ""
                self.env = self.env | {"release_id": self.env["release_id"] + "x", "sequence": self.env["sequence"] + 1}
                self.host.authorize(self.env)
        self.assertFalse((self.root / "processes").exists())

    def test_maintenance_and_stop_are_independent_cleanup_obligations(self):
        self.submit()
        self.invoke("kill_after_switch")
        self.adapter.fault = "maintenance"
        result = release.Controller(self.root, self.adapter).recover()
        self.assertEqual(result["state"], "RECOVERY_REQUIRED")
        self.assertFalse(result["cleanup_complete"])
        self.assertFalse(self.adapter.inspect(self.journal()["candidate"], time.monotonic() + 2)["State"]["Running"])
        with self.assertRaisesRegex(release.ReleaseError, "recovery_pending"):
            self.submit(self.env | {"release_id": "next", "sequence": 2})
        self.adapter.fault = ""
        self.assert_failed(release.Controller(self.root, self.adapter).recover())

    def test_failed_stop_does_not_claim_cleanup_or_prevent_maintenance(self):
        self.submit()
        self.invoke("kill_after_switch")
        self.adapter.fault = "stop"
        result = release.Controller(self.root, self.adapter).recover()
        self.assertEqual(result["state"], "RECOVERY_REQUIRED")
        self.assertFalse(result["cleanup_complete"])
        self.assert_maintenance()
        self.assertTrue(self.adapter.inspect(self.journal()["candidate"], time.monotonic() + 2)["State"]["Running"])
        self.adapter.fault = ""
        self.assert_failed(release.Controller(self.root, self.adapter).recover())

    def test_failed_attempt_retains_owned_stopped_container_and_allows_retry(self):
        self.submit()
        self.invoke("kill_after_start")
        self.assert_failed(release.Controller(self.root, self.adapter).recover())
        candidate = self.journal()["candidate"]
        self.assertIsNotNone(self.adapter.inspect(candidate, time.monotonic() + 2))
        self.assertTrue((self.root / "slots/release-1").exists())
        self.env = self.env | {"release_id": "release-2", "sequence": 2}
        self.host.authorize(self.env)
        release.write_json(self.root / "envelope.json", self.env)
        self.submit()
        self.assert_accepted(self.initial.execute())

    def test_acceptance_recovers_stopped_and_missing_containers(self):
        self.submit()
        self.initial.execute()
        candidate = self.journal()["candidate"]
        for absent in (False, True):
            self.adapter.stop(candidate, time.monotonic() + 5)
            if absent:
                (self.root / "processes/release-1.json").unlink()
            (self.root / "active.json").unlink()
            self.assert_accepted(release.Controller(self.root, self.adapter).recover())

    def test_accepted_recovery_uses_held_manifest_not_replaced_manifest_file(self):
        self.submit()
        self.initial.execute()
        candidate = self.journal()["candidate"]
        self.adapter.stop(candidate, time.monotonic() + 5)
        release.atomic(self.root / "manifests" / (self.env["archive_sha256"] + ".json"), b"corrupt")
        self.assert_accepted(release.Controller(self.root, self.adapter).recover())

    def test_expired_worker_does_not_start_runtime_and_recovery_cleans_receipt(self):
        self.submit()
        with patch.object(release.time, "time", return_value=self.env["deadline"] + 1):
            result = self.initial.execute()
        self.assertFalse(result["cleanup_complete"])
        self.assertFalse((self.root / "processes").exists())
        self.assert_failed(release.Controller(self.root, self.adapter).recover())

    def test_work_timeout_leaves_live_sixty_second_cleanup_reserve(self):
        self.env = self.env | {"deadline": int(time.time()) + 62}
        self.host.authorize(self.env)
        with patch.object(release, "TRANSACTION", 62):
            self.submit()
            before = time.monotonic()
            self.assert_failed(self.initial.execute())
        self.assertLess(time.monotonic() - before, 15)
        self.assertIsNotNone(self.journal()["candidate"])

    def test_initial_capacity_uses_single_container_and_no_network_evidence(self):
        # Policy's ordinary overlap requirement is intentionally1TiB in fixture.
        self.adapter.initial_capacity(self.env, time.monotonic() + 2)
        original = release.read_file
        def memory(path, *args, **kwargs):
            return b"MemAvailable: 655359 kB\n" if path == Path("/proc/meminfo") else original(path, *args, **kwargs)
        with patch.object(release, "read_file", memory), self.assertRaisesRegex(release.ReleaseError, "memory_capacity"):
            self.adapter.initial_capacity(self.env, time.monotonic() + 2)
        self.adapter.policy["capacity"]["disk_bytes"] = 2**63 - 1
        with self.assertRaisesRegex(release.ReleaseError, "disk_capacity"):
            self.adapter.initial_capacity(self.env, time.monotonic() + 2)
        self.adapter.policy["capacity"]["disk_bytes"] = 1
        with patch.object(resource, "getrlimit", return_value=(15, 15)), self.assertRaisesRegex(release.ReleaseError, "fd_capacity"):
            self.adapter.initial_capacity(self.env, time.monotonic() + 2)
        with self.assertRaisesRegex(release.ReleaseError, "memory_capacity"):
            release.HostAdapter.capacity(self.adapter, time.monotonic() + 2)

    def test_corrupt_archive_and_manifest_cannot_reach_start(self):
        self.submit()
        archive = self.root / "static" / self.env["archive_sha256"] / "snapshot.tar.gz"
        original = archive.read_bytes()
        release.atomic(archive, original + b"bad")
        result = self.initial.execute()
        self.assertEqual(result["state"], "FAILED", result)
        self.assertFalse((self.root / "processes").exists())
        release.atomic(archive, original)
        self.assert_static()

    def test_large_valid_held_manifest_survives_journal_and_recovery(self):
        manifest = self.host.source.manifest | {"extension": ""}
        manifest["extension"] = "x" * (65536 - len(release.canonical_json(manifest)))
        release.write_json(self.root / "manifests" / (self.env["archive_sha256"] + ".json"), manifest)
        self.submit()
        self.assertEqual(self.host.invoke("kill_state_VERIFIED")[0], -signal.SIGKILL)
        self.assert_failed(self.invoke(mode="recover"))

    def test_corrupt_cleanup_flag_cannot_skip_precommit_recovery(self):
        self.submit()
        self.invoke("kill_state_VERIFIED")
        journal = self.journal() | {"cleanup_complete": True}
        release.write_json(self.root / "releases/release-1.json", journal)
        with self.assertRaises(release.ReleaseError):
            release.Controller(self.root, self.adapter).recover()

    def test_runtime_wrong_identity_cannot_be_accepted(self):
        self.submit()
        original = self.adapter.start
        def wrong_revision(record, deadline):
            original(record | {"runtime_source_sha": "f" * 40}, deadline)
        # Docker process launch boundary: run a real server with wrong identity.
        with patch.object(self.adapter, "start", wrong_revision):
            result = self.initial.execute()
        self.assertEqual(result["state"], "RECOVERY_REQUIRED")
        self.assertFalse(result["cleanup_complete"])
        self.assert_maintenance()
        self.assertFalse((self.root / "active.json").exists())
        # The foreign identity is deliberately not stopped by release recovery.
        record = release.read_record(self.root / "processes/release-1.json")["record"]
        self.adapter.stop(record, time.monotonic() + 5)

    def test_public_smoke_failure_closes_route_without_accepting(self):
        self.submit()
        self.adapter.fault = "public_dead"
        self.assert_failed(self.initial.execute())
        self.adapter.fault = ""

    def test_blocked_readiness_is_cancelled_and_owned_runtime_is_stopped(self):
        self.submit()
        self.adapter.fault = "ready"
        self.assert_failed(self.initial.execute())
        self.adapter.fault = ""

    def assert_nginx_failure(self, fault):
        self.submit()
        self.adapter.fault = fault
        result = self.initial.execute()
        self.assertEqual(result["state"], "RECOVERY_REQUIRED", result)
        self.assertFalse(result["cleanup_complete"])
        candidate = self.journal()["candidate"]
        self.assertFalse(self.adapter.inspect(candidate, time.monotonic() + 2)["State"]["Running"])
        self.assertFalse((self.root / "active.json").exists())
        self.assert_static()
        self.adapter.fault = ""
        self.assert_failed(release.Controller(self.root, self.adapter).recover())

    def test_nginx_validation_failure_requires_confirmed_recovery(self):
        self.assert_nginx_failure("nginx_test")

    def test_nginx_reload_failure_requires_confirmed_recovery(self):
        self.assert_nginx_failure("nginx_reload")

    def test_received_crash_before_schedule_is_recoverable(self):
        self.invoke("kill_state_RECEIVED", mode="submit")
        self.assert_failed(self.invoke(mode="recover"))

    def test_status_filters_untrusted_exception_details(self):
        self.submit()
        with patch.object(self.adapter, "verify", side_effect=OSError("secret credential private hostname")):
            result = self.initial.execute()
        self.assertEqual(result["error_code"], "host_failure")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(release.query_status(self.root, self.adapter, {
            "schema_version": 1, "kind": "release", "id": "release-1"}), result)

    def test_committed_inspect_failure_stays_accepted_and_incomplete(self):
        self.submit()
        self.initial.execute()
        self.adapter.fault = "inspect_error"
        result = release.Controller(self.root, self.adapter).recover()
        self.assertEqual(result["state"], "COMMITTED")
        self.assertFalse(result["cleanup_complete"])
        self.adapter.fault = ""
        self.assert_accepted(release.Controller(self.root, self.adapter).recover())

    def test_newer_ordinary_release_supersedes_initial_history(self):
        self.submit()
        self.initial.execute()
        self.adapter.policy["runtime_enabled"] = True
        # Ordinary capacity is the existing separate overlap policy boundary.
        request = self.env | {"release_id": "ordinary-2", "sequence": 2, "runtime_source_sha": "d" * 40}
        release.write_json(self.root / "envelope.json", request)
        with patch.object(self.adapter, "capacity", lambda deadline: None):
            result = release.Controller(self.root, self.adapter).deploy(release.canonical_json(request))
        self.assertEqual(result["state"], "COMMITTED", result)
        active = release.read_record(self.root / "active.json")
        self.adapter.stop(active, time.monotonic() + 5)
        self.assertEqual(release.Controller(self.root, self.adapter).recover()["state"], "COMMITTED")
        self.assertEqual(release.read_record(self.root / "active.json")["release_id"], "ordinary-2")
        self.assertEqual(json.loads(self.host.request("/healthz")[2])["runtime_sha"], "d" * 40)


def crash_case(fault, accepted):
    def test(self):
        self.submit()
        self.invoke(fault)
        result = self.invoke(mode="recover")
        (self.assert_accepted if accepted else self.assert_failed)(result)
        self.assertEqual(self.invoke(mode="recover")["state"], result["state"])
    return test


for _boundary in ("state_VERIFIED", "state_PREPARED", "state_READY", "state_SWITCHED",
                  "before_start", "after_start", "before_switch", "after_switch", "before_commit"):
    setattr(InitialInstallTests, "test_crash_" + _boundary, crash_case("kill_" + _boundary, False))
for _boundary in ("state_COMMITTED", "after_commit", "before_pointer", "after_pointer"):
    setattr(InitialInstallTests, "test_crash_" + _boundary, crash_case("kill_" + _boundary, True))


def uncertain_write_case(boundary, accepted):
    def test(self):
        self.submit()
        outcome = self.invoke("error_" + boundary)
        self.assertEqual(outcome["state"], "COMMITTED" if accepted else "FAILED", outcome)
        if accepted:
            self.assertFalse(outcome["cleanup_complete"])
        (self.assert_accepted if accepted else self.assert_failed)(self.invoke(mode="recover"))
    return test


for _boundary, _accepted in (("before_commit", False), ("after_commit", True),
                             ("before_pointer", True), ("after_pointer", True)):
    setattr(InitialInstallTests, "test_uncertain_write_" + _boundary, uncertain_write_case(_boundary, _accepted))


class InitialBoundaryTests(unittest.TestCase):
    def test_authorization_rejects_nonroot_or_group_writable_path_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "authorization.json"
            release.write_json(path, {})
            path.chmod(0o666)
            with patch.object(release, "INITIAL_INSTALL_AUTH", path), self.assertRaisesRegex(release.ReleaseError, "policy_permissions"):
                release.HostAdapter(Path(directory), {}).initial_authorization({})
            path.chmod(0o600)
            if path.stat().st_uid != 0:
                with patch.object(release, "INITIAL_INSTALL_AUTH", path), self.assertRaisesRegex(release.ReleaseError, "policy_permissions"):
                    release.HostAdapter(Path(directory), {}).initial_authorization({})
            alias = Path(directory) / "alias"
            alias.symlink_to(path)
            with patch.object(release, "INITIAL_INSTALL_AUTH", alias), self.assertRaisesRegex(release.ReleaseError, "policy_permissions"):
                release.HostAdapter(Path(directory), {}).initial_authorization({})

    def test_maintenance_requires_real_503_retry_after_and_is_bounded(self):
        class Reply(BaseHTTPRequestHandler):
            status, retry, drip = 503, "1", False
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.send_response(self.status)
                if self.retry is not None:
                    self.send_header("Retry-After", self.retry)
                self.send_header("Content-Length", "100" if self.drip else "0")
                self.end_headers()
                if self.drip:
                    try:
                        for _ in range(100):
                            self.wfile.write(b"x")
                            self.wfile.flush()
                            time.sleep(.02)
                    except OSError:
                        pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Reply)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/mcp"
            self.assertEqual(release.http(url, time.monotonic() + 3, body=b"{}", maintenance=True), b"")
            for status, retry in ((200, "1"), (503, None), (503, "0")):
                Reply.status, Reply.retry = status, retry
                with self.subTest(status=status, retry=retry), self.assertRaises(release.ReleaseError):
                    release.http(url, time.monotonic() + 3, body=b"{}", maintenance=True)
            Reply.status, Reply.retry, Reply.drip = 503, "1", True
            before = time.monotonic()
            with self.assertRaisesRegex(release.ReleaseError, "deadline"):
                release.http(url, before + .4, body=b"{}", maintenance=True)
            self.assertLess(time.monotonic() - before, 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_initial_verbs_are_root_only_and_restricted_entry_denies_them(self):
        for command in ("initial-install", "_initial-install", "initial-install-recover"):
            with patch.object(sys, "argv", ["release", command]), patch.object(os, "geteuid", return_value=1001):
                with self.assertRaisesRegex(release.ReleaseError, "host_privilege"):
                    release.main()
            result = subprocess.run([sys.executable, "-I", str(ROOT / "delivery/vps/release-entry.py")],
                env={"SSH_ORIGINAL_COMMAND": command}, capture_output=True, timeout=3)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"restricted command", result.stderr)

    def test_initial_scheduling_is_root_only(self):
        with patch.object(os, "geteuid", return_value=1001):
            with self.assertRaisesRegex(release.ReleaseError, "host_privilege"):
                release.schedule("initial-install")
        with patch.object(os, "geteuid", return_value=0), patch.object(release, "run", return_value=b"") as run:
            release.schedule("initial-install")
        self.assertEqual(run.call_args.args[0][-1], "_initial-install")
        self.assertIn("--property=RuntimeMaxSec=300s", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
