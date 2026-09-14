"""Restricted release boundary and real process transaction conformance."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from tests.test_v8std_mcp_snapshots import Source
from tests.test_v8std_mcp_release_hold import eventually
from tests.mcp_release_fixture import ProcessAdapter
from tests import mcp_snapshot_fixtures as fixture
import v8std_mcp_release as release

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def envelope(**changes):
    return dict(schema_version=1, release_id="release-1", sequence=1,
                runtime_source_sha="a" * 40, trigger_sha="b" * 40,
                image="ghcr.io/zeegin/v8std-mcp", image_digest="sha256:" + "1" * 64,
                platform_digest="sha256:" + "2" * 64, configuration_digest="3" * 64,
                corpus_id="4" * 64, archive_sha256="5" * 64,
                deadline=int(time.time()) + 300, **changes)


class EnvelopeTests(unittest.TestCase):
    def test_new_journal_parents_are_fsynced_and_symlink_file_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            synced = []
            original = release.sync_dir
            def record(path):
                synced.append(path)
                original(path)
            with patch.object(release, "sync_dir", record):
                release.write_json(root / "state/releases/release.json", {"intent": "before_effect"})
            self.assertLess(synced.index(root), synced.index(root / "state"))
            self.assertIn(root / "state/releases", synced)
            (root / "alias").symlink_to(root / "state/releases/release.json")
            with self.assertRaises(OSError):
                release.read_file(root / "alias")

    def test_docker_stop_refuses_foreign_ownership_or_wrong_descriptor(self):
        record = envelope() | {"name": "v8std-release-release-1", "envelope_hash": "a" * 64,
                               "descriptors": {"sha256:" + "e" * 64: next(iter(release.CONFIG_TYPES))}}
        info = {"Config": {"Image": release.IMAGE + "@" + record["platform_digest"], "Labels": {
            "pro.v8std.release": record["release_id"], "pro.v8std.envelope": record["envelope_hash"],
            "org.opencontainers.image.revision": record["runtime_source_sha"]}}, "Image": "sha256:" + "e" * 64}
        with tempfile.TemporaryDirectory() as temp:
            adapter = release.HostAdapter(Path(temp), {})
            for mutation in ("ownership", "image"):
                bad = json.loads(json.dumps(info))
                if mutation == "ownership":
                    bad["Config"]["Labels"]["pro.v8std.release"] = "foreign"
                else:
                    bad["Image"] = "sha256:" + "f" * 64
                with patch.object(release, "run", return_value=json.dumps([bad]).encode()) as run:
                    with self.assertRaises(release.ReleaseError):
                        adapter.stop(record, time.monotonic() + 3)
                    self.assertEqual(run.call_count, 1)
                    self.assertEqual(run.call_args.args[0][1], "inspect")
    def test_root_policy_static_only_activation_and_immutable_trust(self):
        policy = json.loads((ROOT / "deploy/container/release-policy.example.json").read_text())
        with self.assertRaisesRegex(release.ReleaseError, "not_activated"):
            release.validate_policy(policy)
        policy["enabled"] = True
        self.assertFalse(release.validate_policy(policy)["runtime_enabled"])
        for change in ({"runtime_enabled": True}, {"signer_workflow": "evil/repo/build.yml"},
                       {"static_root": "/etc"}, {"schema_version": True}):
            with self.assertRaises(release.ReleaseError):
                release.validate_policy(policy | change)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "policy.json"
            target.write_text(json.dumps(policy))
            target.chmod(0o666)
            with self.assertRaisesRegex(release.ReleaseError, "policy_permissions"):
                release.trusted_policy(target)

    def test_ci_entry_rejects_bootstrap_internal_commands_and_shell_syntax(self):
        for command in ("bootstrap", "bootstrap-recover", "bootstrap-status", "_deploy", "_index",
                        "deploy --policy /tmp/x", "status; id", "scp -t /etc", "internal-sftp"):
            result = subprocess.run([sys.executable, "-I", str(ROOT / "deploy/container/release-entry.py")],
                env={"SSH_ORIGINAL_COMMAND": command}, capture_output=True, timeout=2)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"restricted command", result.stderr)

    def test_detached_systemd_job_uses_runtime_enforced_service_type(self):
        with patch.object(release, "run") as run:
            release.schedule("deploy")
        argv = run.call_args.args[0]
        self.assertIn("--property=Type=exec", argv)
        self.assertIn("--property=RuntimeMaxSec=300s", argv)
        self.assertNotIn("--pipe", argv)
        self.assertNotIn("--wait", argv)
        self.assertEqual(argv[-1], "_deploy")
        unit = (ROOT / "deploy/container/v8std-release-recover.service").read_text()
        self.assertIn("Type=exec\n", unit)
        self.assertIn("RuntimeMaxSec=300s\n", unit)
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("v8std_mcp_release"))
        return importlib.import_module("v8std_mcp_release")

    def test_strict_unprivileged_envelope_boundary(self):
        release = self.module()
        self.assertEqual(release.validate_envelope(json.dumps(envelope()).encode())["sequence"], 1)
        for changes in ({"schema_version": 2}, {"sequence": True}, {"image": "evil/repo"},
                        {"image_digest": "latest"}, {"release_id": "x; touch /tmp/owned"},
                        {"configuration_digest": "../../policy.json"}, {"env": {}},
                        {"mount": "/var/run/docker.sock"}, {"trigger_sha": "refs/heads/main"},
                        {"deadline": int(time.time()) - 1}):
            with self.subTest(changes=changes), self.assertRaises(release.ReleaseError):
                release.validate_envelope(json.dumps(envelope() | changes).encode())
        for raw in (b"{}", b"x" * 8193, json.dumps(envelope()).replace(
                '"sequence": 1', '"sequence": 1, "sequence": 2').encode()):
            with self.assertRaises(release.ReleaseError):
                release.validate_envelope(raw)

    def test_descriptor_kind_membership_and_docker_id_variants(self):
        child = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                 "config": {"mediaType": "application/vnd.oci.image.config.v1+json", "digest": "sha256:" + "c" * 64}}
        raw_child = release.canonical_json(child)
        child_hash = "sha256:" + release.digest(raw_child)
        index = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json", "manifests": [
            {"mediaType": child["mediaType"], "digest": child_hash, "size": len(raw_child),
             "platform": {"os": "linux", "architecture": "arm64", "variant": "v8"}}]}
        raw_index = release.canonical_json(index)
        request = envelope() | {"image_digest": "sha256:" + release.digest(raw_index), "platform_digest": child_hash}
        mapping = release.verify_descriptors(raw_index, raw_child, request, "linux/arm64")
        self.assertIn(request["image_digest"], mapping)  # containerd index .Id
        self.assertIn(child["config"]["digest"], mapping)  # conventional config .Id
        for args in ((raw_index, raw_child, request, "linux/amd64"),
                     (raw_child, raw_child, request | {"image_digest": child_hash}, "linux/arm64"),
                     (raw_index + b"x", raw_child, request, "linux/arm64")):
            with self.assertRaises(release.ReleaseError):
                release.verify_descriptors(*args)

    def test_attestation_binds_certificate_workflow_main_source_and_namespace(self):
        command = release.attestation_command("oci://" + release.IMAGE + "@sha256:" + "a" * 64, "b" * 40)
        self.assertEqual(command[command.index("--repo") + 1], "zeegin/v8std")
        self.assertEqual(command[command.index("--signer-workflow") + 1], "zeegin/v8std/.github/workflows/ci.yml")
        self.assertEqual(command[command.index("--source-ref") + 1], "refs/heads/main")
        self.assertEqual(command[command.index("--source-digest") + 1], "b" * 40)
        self.assertIn("--deny-self-hosted-runners", command)

    def test_cli_unprivileged_input_has_no_shell_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "injected"
            request = envelope() | {"release_id": "$(touch " + str(target) + ")"}
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/v8std_mcp_release.py"), "validate-envelope"],
                                    input=release.canonical_json(request) + b"\n", capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(target.exists())

    def test_actual_subprocess_and_drip_http_cancel_at_deadline(self):
        started = time.monotonic()
        with self.assertRaisesRegex(release.ReleaseError, "deadline"):
            release.run([sys.executable, "-c", "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(120)"],
                        started + .15)
        self.assertLess(time.monotonic() - started, .6)
        class Drip(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "100")
                self.end_headers()
                try:
                    for _ in range(100):
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        time.sleep(.03)
                except OSError:
                    pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Drip)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            started = time.monotonic()
            with self.assertRaisesRegex(release.ReleaseError, "deadline"):
                release.http(f"http://127.0.0.1:{server.server_port}/", started + .3)
            self.assertLess(time.monotonic() - started, .7)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


class IngressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive, manifest = fixture.snapshot_fixture()
        manifest["archive"]["path"] = "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["sha256"] + "/snapshot.tar.gz"
        self.header = {"schema_version": 1, "publication_id": "content-1", "sequence": 1,
            "trigger_sha": "b" * 40, "manifest": manifest, "deadline": int(time.time()) + 300, "action": "publish"}

    def ingest(self, header=None, archive=None):
        data = release.canonical_json(header or self.header) + b"\n" + (self.archive if archive is None else archive)
        reader, writer = os.pipe()
        def send():
            try:
                with os.fdopen(writer, "wb") as stream:
                    stream.write(data)
            except BrokenPipeError:
                pass
        worker = threading.Thread(target=send)
        worker.start()
        try:
            return release.ingest(self.root, self.root / "static", reader, seconds=1)
        finally:
            os.close(reader)
            worker.join(2)

    def test_ingress_process_dies_between_receipt_and_inbox_then_reconciles(self):
        code = '''
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import v8std_mcp_release as r
root = Path(sys.argv[2])
original = r.write_json
def crash(path, value):
    original(path, value)
    if path.parent.name == 'publications':
        os._exit(73)
r.write_json = crash
r.ingest(root, root / 'static', sys.stdin.fileno())
'''
        result = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT / "scripts"), str(self.root)],
            input=release.canonical_json(self.header) + b"\n" + self.archive, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertFalse((self.root / "pending-index.json").exists())
        self.assertEqual(release.query_status(self.root, None, {
            "schema_version": 1, "kind": "publication", "id": "content-1"})["state"], "RECEIVED")
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        self.assertEqual(publisher.recover()["state"], "COMMITTED")
        target = self.root / "static" / self.header["manifest"]["archive"]["sha256"] / "snapshot.tar.gz"
        self.assertEqual(target.read_bytes(), self.archive)

    def test_orphan_receipt_blocks_new_upload_until_reconciled(self):
        self.ingest()
        (self.root / "pending-index.json").unlink()
        with self.assertRaisesRegex(release.ReleaseError, "publication_busy"):
            self.ingest(self.header | {"publication_id": "content-2", "sequence": 2})

    def test_reference_rechecks_trigger_authority_before_pointer_effects(self):
        self.ingest()
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        publisher.publish(self.header)
        reference = self.header | {"publication_id": "reference-1", "action": "reference"}
        self.ingest(reference, b"")
        def reject(*args):
            raise release.ReleaseError("main_ancestry")
        publisher.verifier = reject
        self.assertEqual(publisher.recover()["state"], "FAILED")
        self.assertFalse((self.root / "current-index.json").exists())

    def test_reconciliation_busy_does_not_change_durable_publication(self):
        self.ingest()
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        before = (self.root / "publications/content-1.json").read_bytes()
        with patch.object(publisher, "publish", side_effect=release.ReleaseError("busy")):
            with self.assertRaisesRegex(release.ReleaseError, "busy"):
                publisher.recover()
        self.assertEqual((self.root / "publications/content-1.json").read_bytes(), before)

    def test_maximum_header_survives_receipt_wrapper_status_and_reference(self):
        header = json.loads(json.dumps(self.header))
        header["manifest"]["test_extension"] = ""
        header["manifest"]["test_extension"] = "x" * (65536 - len(release.canonical_json(header)))
        self.assertEqual(len(release.canonical_json(header)), 65536)
        self.assertEqual(self.ingest(header)["state"], "QUEUED")
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        self.assertEqual(publisher.recover()["state"], "COMMITTED")
        query = {"schema_version": 1, "kind": "publication", "id": header["publication_id"]}
        self.assertEqual(release.query_status(self.root, None, query)["state"], "COMMITTED")
        reference = header | {"publication_id": "ref-1", "action": "reference"}
        self.assertEqual(self.ingest(reference, b"")["state"], "QUEUED")
        self.assertEqual(publisher.recover()["state"], "COMMITTED")
        self.assertEqual(self.ingest(header)["state"], "COMMITTED")

    def test_bounded_pipe_ingress_verification_rename_and_reference(self):
        result = self.ingest()
        self.assertEqual(result["state"], "QUEUED")
        calls = []
        publisher = release.Publisher(self.root, self.root / "static", lambda path, header, deadline: calls.append(path))
        self.assertEqual(publisher.publish(self.header)["state"], "COMMITTED")
        self.assertEqual(len(calls), 1)  # Stub verifies invocation only, not attestation success.
        archive = self.root / "static" / self.header["manifest"]["archive"]["sha256"] / "snapshot.tar.gz"
        self.assertEqual(archive.read_bytes(), self.archive)
        self.assertFalse(list((self.root / "static").glob(".upload-*")))
        reference = self.header | {"publication_id": "reference-1", "action": "reference"}
        self.ingest(reference, b"")
        self.assertEqual(publisher.publish(reference)["state"], "COMMITTED")
        self.assertEqual(json.loads((self.root / "current-index.json").read_text()), reference)

    def test_truncated_excess_corrupt_and_path_injection_reject_without_visibility(self):
        for data in (self.archive[:-1], self.archive + b"extra", b"x" * len(self.archive)):
            with self.subTest(size=len(data)), self.assertRaises(release.ReleaseError):
                self.ingest(archive=data)
        for changes in ({"path": "/etc/v8std-release/policy.json"}, {"publication_id": "../../policy"},
                        {"env": {"PATH": "/tmp"}}, {"action": "shell"}):
            with self.subTest(changes=changes), self.assertRaises(release.ReleaseError):
                self.ingest(self.header | changes)
        self.assertFalse(list((self.root / "static").glob("*/snapshot.tar.gz")))
        self.assertFalse((self.root / "pending-index.json").exists())

    def test_stalled_pipe_is_cancelled_and_own_staging_cleaned(self):
        reader, writer = os.pipe()
        os.write(writer, release.canonical_json(self.header) + b"\n")
        started = time.monotonic()
        try:
            with self.assertRaises(release.ReleaseError):
                release.ingest(self.root, self.root / "static", reader, seconds=.1)
        finally:
            os.close(reader)
            os.close(writer)
        self.assertLess(time.monotonic() - started, .5)
        self.assertFalse(list((self.root / "static").glob(".upload-*")))

    def test_failed_verification_never_publishes_and_retry_preserves_identity(self):
        self.ingest()
        def reject(*args):
            raise release.ReleaseError("attestation")
        publisher = release.Publisher(self.root, self.root / "static", reject)
        with self.assertRaisesRegex(release.ReleaseError, "attestation"):
            publisher.publish(self.header)
        self.assertFalse((self.root / "static" / self.header["manifest"]["archive"]["sha256"]).exists())
        with self.assertRaisesRegex(release.ReleaseError, "publication_busy|mutated_duplicate"):
            self.ingest(self.header | {"trigger_sha": "c" * 40})
        publisher.verifier = lambda *args: None
        self.assertEqual(publisher.publish(self.header)["state"], "COMMITTED")

    def test_committed_upload_retry_does_not_reset_receipt_or_reference(self):
        self.ingest()
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        committed = publisher.publish(self.header)
        reference = self.root / "references" / (self.header["manifest"]["archive"]["sha256"] + ".json")
        before = reference.read_bytes()
        self.assertEqual(self.ingest()["state"], "COMMITTED")
        self.assertEqual(json.loads((self.root / "publications/content-1.json").read_text()), committed)
        self.assertEqual(reference.read_bytes(), before)
        self.assertFalse((self.root / "pending-index.json").exists())

    def test_committed_crash_before_pending_unlink_reconciles(self):
        self.ingest()
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        publisher.publish(self.header)
        release.write_json(self.root / "pending-index.json", self.header)
        publisher.publish(self.header)
        self.assertFalse((self.root / "pending-index.json").exists())

    def test_status_acknowledges_exact_publication_and_reference_ids(self):
        self.ingest()
        query = {"schema_version": 1, "kind": "publication", "id": "content-1"}
        self.assertEqual(release.query_status(self.root, None, query)["state"], "RECEIVED")
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        publisher.publish(self.header)
        outcome = release.query_status(self.root, None, query)
        self.assertEqual((outcome["publication_id"], outcome["sequence"], outcome["state"]), ("content-1", 1, "COMMITTED"))
        reference = self.header | {"publication_id": "reference-1", "action": "reference"}
        query["id"] = "reference-1"
        self.assertEqual(release.query_status(self.root, None, query)["state"], "NOT_FOUND")
        self.ingest(reference, b"")
        self.assertEqual(release.query_status(self.root, None, query)["state"], "RECEIVED")
        publisher.publish(reference)
        self.assertEqual(release.query_status(self.root, None, query)["action"], "reference")
        self.assertEqual(release.query_status(self.root, None, query)["state"], "COMMITTED")
        with self.assertRaises(release.ReleaseError):
            release.query_status(self.root, None, query | {"id": "../../policy"})

    def test_reference_cannot_revert_current_sequence_and_gc_retains_pins(self):
        self.ingest()
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        publisher.publish(self.header)
        reference = self.header | {"publication_id": "current", "action": "reference", "sequence": 3}
        self.ingest(reference, b"")
        publisher.publish(reference)
        stale = reference | {"publication_id": "stale", "sequence": 2}
        self.ingest(stale, b"")
        self.assertEqual(publisher.recover()["state"], "FAILED")
        self.assertEqual(json.loads((self.root / "current-index.json").read_text()), reference)
        release.write_json(self.root / "pins.json", {"archives": []})
        self.assertEqual(publisher.gc(now=time.time() + 8 * 86400), [])
        # An unreferenced older immutable object is removable only after seven
        # days and only with verified ownership/hash, while a pin retains it.
        other = b"test-only transport blob"
        key = release.digest(other)
        release.atomic(self.root / "static" / key / "snapshot.tar.gz", other)
        release.write_json(self.root / "references" / (key + ".json"), {"last_reference": time.time()})
        self.assertEqual(publisher.gc(now=time.time() + 6 * 86400), [])
        release.write_json(self.root / "pins.json", {"archives": [key]})
        self.assertEqual(publisher.gc(now=time.time() + 8 * 86400), [])
        release.write_json(self.root / "pins.json", {"archives": []})
        self.assertEqual(publisher.gc(now=time.time() + 8 * 86400), [key])

    def test_failed_queued_publication_records_failure_and_allows_new_job(self):
        self.ingest()
        def reject(*args):
            raise release.ReleaseError("attestation")
        publisher = release.Publisher(self.root, self.root / "static", reject)
        result = publisher.recover()
        self.assertEqual(result["state"], "FAILED")
        self.assertFalse((self.root / "pending-index.json").exists())
        self.assertEqual(self.ingest(self.header | {"publication_id": "retry-2", "sequence": 2})["state"], "QUEUED")


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = Source()
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(self.source.close)
        self.addCleanup(self.stop_processes)
        ports = [port(), port()]
        edge_port = port()
        config = {"site_url": self.source.url, "refresh_seconds": 1, "max_snippet_chars": 4000,
                  "memory_bytes": 536870912, "cpus": 1}
        config_hash = release.digest(release.canonical_json(config))
        self.policy = {"runtime_enabled": True, "ports": ports, "public_url": f"http://127.0.0.1:{edge_port}", "configs": {config_hash: config}}
        release.write_json(self.root / "policy.json", self.policy)
        self.adapter = ProcessAdapter(self.root, self.policy)
        self.env = envelope() | {"configuration_digest": config_hash,
            "corpus_id": self.source.manifest["corpus_id"], "archive_sha256": self.source.manifest["archive"]["sha256"]}
        self.previous = {**self.env, "release_id": "predecessor", "sequence": 0, "runtime_source_sha": "c" * 40,
            "name": "v8std-release-predecessor", "envelope_hash": "d" * 64, "descriptors": {}, "port": ports[0],
            "hold_token": "e" * 32}
        self.install_snapshot()
        self.adapter.hold(self.previous, "e" * 32, time.monotonic() + 5, self.source.manifest)
        release.write_json(self.root / "active.json", self.previous)
        release.write_json(self.root / "envelope.json", self.env)
        release.write_json(self.root / "edge.json", {"port": ports[0]})
        with (self.root / "edge.log").open("wb") as log:
            self.edge = subprocess.Popen([sys.executable, "-m", "tests.mcp_release_fixture", "edge",
                str(self.root), str(edge_port)], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        eventually(self.health)

    def install_snapshot(self):
        key = self.source.manifest["archive"]["sha256"]
        release.write_json(self.root / "manifests" / (key + ".json"), self.source.manifest)
        release.atomic(self.root / "static" / key / "snapshot.tar.gz", self.source.archive)

    def stop_processes(self):
        for path in (self.root / "processes").glob("*.json"):
            pid = json.loads(path.read_text())["pid"]
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        for child in self.adapter.children:
            child.poll()
        if hasattr(self, "edge"):
            self.edge.terminate()
            self.edge.wait(5)

    def health(self):
        try:
            return json.loads(release.http(self.policy["public_url"] + "/healthz", time.monotonic() + .3))
        except release.ReleaseError:
            return None

    def invoke(self, fault="", mode="deploy"):
        result = subprocess.run([sys.executable, "-m", "tests.mcp_release_fixture", mode, str(self.root), fault],
            cwd=ROOT, capture_output=True, timeout=25)
        if fault.startswith(("crash_", "intent_")):
            self.assertIn(result.returncode, {91, 92, 93}, result.stderr.decode())
        else:
            self.assertEqual(result.returncode, 0, result.stderr.decode())
        return release.Controller(self.root, self.adapter).status()

    def test_success_real_mcp_health_and_independent_runtime_corpus_shas(self):
        result = self.invoke()
        self.assertEqual(result["state"], "COMMITTED", result)
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])
        self.assertEqual(self.health()["corpus_source_sha"], self.source.manifest["source_sha"])
        self.assertFalse(self.adapter.inspect(self.previous, time.monotonic() + 1)["State"]["Running"])

    def test_reboot_after_complete_commit_restores_accepted_container(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        active = json.loads((self.root / "active.json").read_text())
        self.adapter.stop(active, time.monotonic() + 5)
        self.assertEqual(self.invoke(mode="recover")["state"], "COMMITTED")
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])

    def test_ordinary_submit_rejects_missing_predecessor_before_scheduling(self):
        (self.root / "active.json").unlink()
        with patch.object(release, "schedule") as schedule:
            with self.assertRaisesRegex(release.ReleaseError, "predecessor_required"):
                release.submit(self.root, self.adapter, release.canonical_json(self.env))
            schedule.assert_not_called()
        self.assertFalse((self.root / "pending-deploy.json").exists())

    def test_runtime_activation_is_separate_from_publication(self):
        self.adapter.policy["runtime_enabled"] = False
        with patch.object(release, "schedule") as schedule:
            with self.assertRaisesRegex(release.ReleaseError, "runtime_not_activated"):
                release.submit(self.root, self.adapter, release.canonical_json(self.env))
            schedule.assert_not_called()

    def test_public_failure_restores_observed_predecessor_and_retains_snapshot(self):
        result = self.invoke("public_dead")
        self.assertEqual(result["state"], "ROLLED_BACK", result)
        self.assertEqual(self.health()["runtime_sha"], self.previous["runtime_source_sha"])
        self.assertTrue((self.root / "static" / self.previous["archive_sha256"] / "snapshot.tar.gz").is_file())

    def test_pre_switch_pull_failure(self):
        result = self.invoke("pull")
        self.assertEqual(result["state"], "FAILED", result)
        self.assertEqual(self.health()["runtime_sha"], self.previous["runtime_source_sha"])

    def test_crash_after_daemon_switch_reconciles_real_edge(self):
        self.invoke("crash_after_switch")
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])
        result = self.invoke(mode="recover")
        self.assertEqual(result["state"], "ROLLED_BACK", result)
        self.assertEqual(self.health()["runtime_sha"], self.previous["runtime_source_sha"])

    def test_committed_crash_finishes_cleanup_without_undo(self):
        self.invoke("crash_COMMITTED")
        result = self.invoke(mode="recover")
        self.assertEqual(result["state"], "COMMITTED", result)
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])

    def test_committed_candidate_death_restarts_accepted_release(self):
        self.invoke("crash_COMMITTED")
        journal = json.loads((self.root / "releases/release-1.json").read_text())
        self.adapter.stop(journal["candidate"], time.monotonic() + 5)
        result = self.invoke(mode="recover")
        self.assertEqual(result["state"], "COMMITTED", result)
        self.assertTrue(result["cleanup_complete"], result)
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])

    def test_failed_authority_has_no_runtime_effect(self):
        before = len((self.root / "calls.jsonl").read_text().splitlines())
        result = self.invoke("verify")
        self.assertEqual(result["state"], "FAILED", result)
        operations = [json.loads(x)["operation"] for x in (self.root / "calls.jsonl").read_text().splitlines()[before:]]
        self.assertEqual(operations, ["verify"])

    def test_readiness_cancels_actual_blocked_worker_before_loader_360(self):
        started = time.monotonic()
        result = self.invoke("ready")
        self.assertEqual(result["state"], "FAILED", result)
        self.assertLess(time.monotonic() - started, 12)
        journal = json.loads((self.root / "releases/release-1.json").read_text())
        self.assertFalse(self.adapter.inspect(journal["candidate"], time.monotonic() + 1)["State"]["Running"])
        self.assertEqual(self.health()["runtime_sha"], self.previous["runtime_source_sha"])

    def test_rollback_failure_is_recovery_required_and_retry_reconciles(self):
        result = self.invoke("public_dead,switch_old")
        self.assertEqual(result["state"], "RECOVERY_REQUIRED", result)
        self.assertFalse(result["cleanup_complete"])
        self.assertEqual(self.invoke(mode="recover")["state"], "ROLLED_BACK")
        self.assertEqual(self.health()["runtime_sha"], self.previous["runtime_source_sha"])

    def test_manifest_change_between_envelope_and_start_fails_before_switch(self):
        self.source.next_generation()
        result = self.invoke()
        self.assertEqual(result["state"], "FAILED", result)
        self.assertEqual(self.health()["runtime_sha"], self.previous["runtime_source_sha"])

    def test_mutated_duplicate_stale_retry_and_concurrent_lock(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        controller = release.Controller(self.root, self.adapter)
        count = len((self.root / "calls.jsonl").read_text().splitlines())
        controller.deploy(release.canonical_json(self.env))
        self.assertEqual(count, len((self.root / "calls.jsonl").read_text().splitlines()))
        for changes, code in (({"runtime_source_sha": "f" * 40}, "mutated_duplicate"),
                              ({"release_id": "late-job"}, "stale_sequence")):
            with self.assertRaisesRegex(release.ReleaseError, code):
                controller.deploy(release.canonical_json(self.env | changes))
        with release.locked(self.root), self.assertRaisesRegex(release.ReleaseError, "busy"):
            controller.deploy(release.canonical_json(self.env))


def crash_case(fault):
    def test(self):
        self.invoke(fault)
        result = self.invoke(mode="recover")
        self.assertIn(result["state"], {"FAILED", "ROLLED_BACK"}, result)
        self.assertTrue(result["cleanup_complete"], result)
        self.assertEqual(self.health()["runtime_sha"], self.previous["runtime_source_sha"])
        count = len((self.root / "calls.jsonl").read_text().splitlines())
        self.invoke(mode="recover")
        self.assertEqual(count, len((self.root / "calls.jsonl").read_text().splitlines()))
    return test


for _fault in ("crash_RECEIVED", "crash_VERIFIED", "crash_PREPARED", "crash_READY", "crash_SWITCHED",
               "crash_after_start", "intent_pin_predecessor", "intent_pull_candidate", "intent_start_candidate"):
    setattr(TransactionTests, "test_recovery_" + _fault, crash_case(_fault))


if __name__ == "__main__":
    unittest.main()
