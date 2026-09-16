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
from tests.mcp_release_fixture import ProcessAdapter, BootstrapAdapter, bootstrap_environment, prepare_legacy, LEGACY_SHA
from tests import mcp_snapshot_fixtures as fixture
import delivery.vps.v8std_mcp_release as release

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def envelope(**changes):
    return dict(schema_version=1, release_id="release-1", sequence=1,
                runtime_source_sha="a" * 40, trigger_sha="b" * 40,
                image="ghcr.io/zeegin/v8std-mcp", image_digest="sha256:" + "1" * 64,
                platform_digest="sha256:" + "2" * 64, configuration_digest="3" * 64,
                corpus_id="4" * 64, archive_sha256="5" * 64,
                deadline=int(time.time()) + 300, **changes)


class EnvelopeTests(unittest.TestCase):
    def test_control_directory_is_readable_under_recovery_umask(self):
        with tempfile.TemporaryDirectory() as temp:
            adapter = release.HostAdapter(Path(temp), {})
            old_umask = os.umask(0o077)
            try:
                adapter.control({"release_id": "held"}, "hold", "a" * 32)
                directory = Path(temp) / "slots/held/control"
                self.assertEqual(directory.stat().st_mode & 0o777, 0o755)
                directory.chmod(0o700)  # Repair a directory left by old recovery.
                adapter.control({"release_id": "held"}, "hold", "a" * 32)
                self.assertEqual(directory.stat().st_mode & 0o777, 0o755)
            finally:
                os.umask(old_umask)

    def test_control_file_has_final_permissions_at_atomic_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            original = os.replace
            published = []
            def replace(source, target):
                published.append(Path(source).stat().st_mode & 0o777)
                original(source, target)
                self.assertEqual(Path(target).stat().st_mode & 0o777, 0o644)
            old_umask = os.umask(0o077)
            try:
                with patch.object(release.os, "replace", replace):
                    release.HostAdapter(Path(temp), {}).control({"release_id": "held"}, "hold", "a" * 32)
                self.assertEqual(published, [0o644])
            finally:
                os.umask(old_umask)

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
        policy = json.loads((ROOT / "delivery/vps/release-policy.example.json").read_text())
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
            result = subprocess.run([sys.executable, "-I", str(ROOT / "delivery/vps/release-entry.py")],
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
        unit = (ROOT / "delivery/vps/v8std-release-recover.service").read_text()
        self.assertIn("Type=exec\n", unit)
        self.assertIn("RuntimeMaxSec=300s\n", unit)
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("delivery.vps.v8std_mcp_release"))
        return importlib.import_module("delivery.vps.v8std_mcp_release")

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
            result = subprocess.run([sys.executable, "-I", str(ROOT / "delivery/vps/v8std_mcp_release.py"), "validate-envelope"],
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


class SmokeBoundaryTests(unittest.TestCase):
    """Faults replace HTTP bytes only; smoke and JSON-RPC validation stay real."""

    def setUp(self):
        self.record = envelope() | {"hold_token": "e" * 32}
        self.health = {"ok": True, "runtime_sha": "a" * 40, "corpus_id": "4" * 64,
                       "archive_sha256": "5" * 64, "hold_token": "e" * 32}
        self.deadline = time.monotonic() + 30
        self.requests = [
            ("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "v8std-release", "version": "1"}}),
            ("tools/list", {}),
            ("tools/call", {"name": "v8std_search", "arguments": {"query": "std437", "limit": 1}}),
            ("tools/call", {"name": "v8std_get_page", "arguments": {"id_or_alias_or_url": "std437"}}),
            ("tools/call", {"name": "v8std_explain_snippet", "arguments": {"snippet": "Запрос = Новый Запрос;", "limit": 1}}),
            ("tools/call", {"name": "v8std_get_related", "arguments": {"id_or_alias_or_url": "std437", "limit": 1}}),
            ("tools/call", {"name": "v8std_explain_diagnostics", "arguments": {"codes": ["missing"]}}),
            ("resources/read", {"uri": "v8std://llms-full.txt"}),
        ]
        self.results = [
            {"serverInfo": {"name": "v8std", "version": "1"}, "protocolVersion": "2025-03-26",
             "capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False}}},
            {"tools": [{"name": name} for name in ("v8std_search", "v8std_get_page", "v8std_get_related",
                "v8std_explain_snippet", "v8std_explain_diagnostics")]},
        ]
        for value in ({"results": [{"id": "std437"}]},
                      {"found": True, "page": {"id": "std437"}},
                      {"standards": [{"id": "std437"}]},
                      {"found": True, "id": "std437", "title": "Запросы", "relations": None, "related": []},
                      {"diagnostics": [], "standards": [], "unknown_codes": [{"code": "missing", "frequency": 1}],
                       "total_input": 1, "unique_codes": 1}):
            self.results.append({"isError": False, "content": [{"type": "text", "text": json.dumps(value)}],
                                 "structuredContent": value})
        self.denied = {"jsonrpc": "2.0", "id": 8, "error": {"code": -32601, "message": "Method not found"}}

    def run_smoke(self, replacements=None):
        self.seen = []
        health_reads = 0
        def http(url, deadline, *, body=None, limit=1024 * 1024):
            nonlocal health_reads
            self.assertEqual(deadline, self.deadline)
            self.assertEqual(limit, 1024 * 1024)
            if body is None:
                self.assertEqual(url, "http://fixture/healthz")
                stage = "health_before" if health_reads == 0 else "health_after"
                health_reads += 1
                reply = self.health
            else:
                self.assertEqual(url, "http://fixture/mcp")
                request = json.loads(body)
                number = request["id"]
                method, params = self.requests[number - 1]
                self.assertEqual(request, {"jsonrpc": "2.0", "id": number, "method": method, "params": params})
                stage = params["name"] if method == "tools/call" else method
                reply = self.denied if stage == "resources/read" else {
                    "jsonrpc": "2.0", "id": number, "result": self.results[number - 1]}
            self.seen.append(stage)
            reply = (replacements or {}).get(stage, reply)
            if isinstance(reply, Exception):
                raise reply
            return reply if isinstance(reply, bytes) else json.dumps(reply).encode()
        with patch.object(release, "http", http):
            return release.smoke("http://fixture", self.record, self.deadline)

    def assert_rejected(self, stage, reply, code):
        with self.assertRaises(release.ReleaseError) as caught:
            self.run_smoke({stage: reply})
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.seen[-1], stage)

    def test_smoke_probes_all_five_tools_and_brackets_the_resource_denial(self):
        self.assertEqual(self.run_smoke(), self.health)
        self.assertEqual(self.seen, ["health_before", "initialize", "tools/list", "v8std_search", "v8std_get_page",
            "v8std_explain_snippet", "v8std_get_related", "v8std_explain_diagnostics", "resources/read", "health_after"])

    def test_initialize_rejects_even_empty_or_null_resource_capability(self):
        for resources in ({}, None, {"subscribe": True}):
            with self.subTest(resources=resources):
                result = self.results[0] | {"capabilities": {"resources": resources, "tools": {}}}
                self.assert_rejected("initialize", {"jsonrpc": "2.0", "id": 1, "result": result}, "resource_capability")

    def test_resource_read_success_is_not_retirement(self):
        self.assert_rejected("resources/read", {"jsonrpc": "2.0", "id": 8, "result": {
            "contents": [{"uri": "v8std://llms-full.txt", "text": "corpus"}]}}, "resource_disabled")

    def test_resource_denial_accepts_safe_alternate_message(self):
        reply = self.denied | {"error": {"code": -32601, "message": "Method not found: resources/read"}}
        self.assertEqual(self.run_smoke({"resources/read": reply}), self.health)
        self.assertEqual(self.seen[-1], "health_after")

    def test_resource_denial_requires_error_without_content_or_result(self):
        bad = [self.denied | {"result": None}, self.denied | {"content": "corpus"},
               self.denied | {"contents": [{"text": "corpus"}]}, self.denied | {"error": None}]
        for error in ({"code": -32602, "message": "Invalid params"}, {"code": -32601},
                      {"code": -32601, "message": "Method not found", "data": {"text": "corpus"}}):
            bad.append(self.denied | {"error": error})
        for reply in bad:
            with self.subTest(reply=reply):
                self.assert_rejected("resources/read", reply, "resource_disabled")

    def test_resource_denial_requires_compact_nonempty_message(self):
        for message in (None, 42, {}, [], "", " ", "x" * 257, "corpus text\n" * 100):
            with self.subTest(message=message):
                reply = self.denied | {"error": {"code": -32601, "message": message}}
                self.assert_rejected("resources/read", reply, "resource_disabled")

    def test_resource_denial_must_match_request_id_and_jsonrpc_version(self):
        bad = [{key: value for key, value in self.denied.items() if key != omitted} for omitted in ("id", "jsonrpc")]
        bad += [self.denied | change for change in ({"id": 9}, {"id": "8"}, {"id": 8.0}, {"jsonrpc": "1.0"})]
        for reply in bad:
            with self.subTest(reply=reply):
                self.assert_rejected("resources/read", reply, "rpc")

    def test_resource_denial_does_not_swallow_transport_parse_or_deadline_errors(self):
        cases = [(release.ReleaseError(code), code) for code in ("http_failed", "deadline", "input_size")]
        cases += [(b"not json", "input_shape"), (b"[]", "input_shape"),
                  (b'data: {}\n\ndata: {}\n\n', "rpc_stream")]
        for reply, code in cases:
            with self.subTest(reply=reply):
                self.assert_rejected("resources/read", reply, code)

    def test_retained_tools_reject_rpc_and_tool_errors(self):
        for name, number in (("v8std_get_related", 6), ("v8std_explain_diagnostics", 7)):
            for reply, code in (({"jsonrpc": "2.0", "id": number, "error": self.denied["error"]}, "rpc"),
                                ({"jsonrpc": "2.0", "id": number, "result": {"isError": True}}, "rpc_tool"),
                                ({"jsonrpc": "2.0", "id": number, "result": {}}, "tool_content")):
                with self.subTest(name=name, code=code):
                    self.assert_rejected(name, reply, code)

    def test_health_identity_and_generation_bracket_remain_required(self):
        for field in ("runtime_sha", "corpus_id", "archive_sha256", "hold_token"):
            for stage, code in (("health_before", "health_identity"), ("health_after", "smoke_generation_changed")):
                with self.subTest(field=field, stage=stage):
                    self.assert_rejected(stage, self.health | {field: "different"}, code)
        self.assert_rejected("health_before", self.health | {"ok": False}, "health_identity")

    def test_search_and_page_must_still_be_useful(self):
        for name, number, value, code in (("v8std_search", 3, {"results": []}, "search_empty"),
                ("v8std_get_page", 4, {"found": False}, "page_smoke"),
                ("v8std_get_page", 4, {"found": True, "page": {"id": "wrong"}}, "page_smoke")):
            with self.subTest(name=name, value=value):
                self.assert_rejected(name, {"jsonrpc": "2.0", "id": number, "result": {"structuredContent": value}}, code)

    def test_rpc_success_stays_strict_and_single_sse_frame_remains_supported(self):
        for reply, code in (({"jsonrpc": "2.0", "id": 1, "error": self.denied["error"]}, "rpc"),
                ({"jsonrpc": "2.0", "id": True, "result": {}}, "rpc"),
                ({"id": 1, "result": {}}, "rpc"),
                ({"jsonrpc": "2.0", "id": 1, "result": [], "error": None}, "rpc"),
                ({"jsonrpc": "2.0", "id": 1, "result": {"isError": True}}, "rpc_tool")):
            with self.subTest(reply=reply), patch.object(release, "http", return_value=json.dumps(reply).encode()):
                with self.assertRaises(release.ReleaseError) as caught:
                    release.rpc("http://fixture", "tools/list", {}, self.deadline, 1)
                self.assertEqual(caught.exception.code, code)
        raw = b'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n\n'
        with patch.object(release, "http", return_value=raw):
            self.assertEqual(release.rpc("http://fixture", "tools/list", {}, self.deadline, 1), {"tools": []})


class PublicationOrderingTests(unittest.TestCase):
    """Ordering is enforced by real ingestion and Publisher, including recovery."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root, self.store = Path(temp.name) / "state", Path(temp.name) / "objects"
        self.archive, self.manifest = fixture.snapshot_fixture()
        self.manifest["archive"]["path"] = "https://ai.v8std.ru/indexes/v1/" + self.manifest["archive"]["path"]
        self.publisher = release.Publisher(self.root, self.store)
        self.transport = patch.object(release, "run", self.command)
        self.transport.start()
        self.addCleanup(self.transport.stop)

    def command(self, argv, deadline, **kwargs):
        if argv[:3] == ["gh", "attestation", "verify"]:
            self.assertIn("--deny-self-hosted-runners", argv)
            self.assertEqual(argv[argv.index("--source-ref") + 1], "refs/heads/main")
            return b"[]"
        if argv[:2] == ["gh", "api"]:
            sha = argv[2].split("/compare/")[1].split("...")[0]
            return json.dumps({"status": "behind" if sha == "c" * 40 else "identical",
                               "merge_base_commit": {"sha": sha}}).encode()
        self.fail("unexpected external transport")

    def header(self, identity, sequence, action="publish", **changes):
        return dict(schema_version=1, publication_id=identity, sequence=sequence,
                    trigger_sha="b" * 40, manifest=self.manifest,
                    deadline=int(time.time()) + 300, action=action) | changes

    def ingest(self, header):
        with tempfile.TemporaryFile() as stream:
            stream.write(release.canonical_json(header) + b"\n")
            if header["action"] == "publish":
                stream.write(self.archive)
            stream.seek(0)
            return release.ingest(self.root, self.store, stream.fileno())

    def history(self):
        headers = [self.header("current", 36), self.header("ack", 37, "reference"),
                   self.header("failed-latest", 41, trigger_sha="c" * 40)]
        for header in headers:
            self.ingest(header)
            result = self.publisher.recover()
        self.assertEqual(result["state"], "FAILED")
        return headers

    def test_failed_watermark_rejects_older_equal_and_keeps_exact_duplicates(self):
        headers = self.history()
        before = (self.root / "current-index.json").read_bytes()
        for sequence in (40, 41):
            with self.subTest(sequence=sequence), self.assertRaisesRegex(release.ReleaseError, "stale_sequence"):
                self.ingest(self.header("new-" + str(sequence), sequence))
        self.assertFalse((self.root / "publications/new-40.json").exists())
        for header, state in zip(headers, ("COMMITTED", "COMMITTED", "FAILED")):
            self.assertEqual(self.ingest(header)["state"], state)
        with self.assertRaisesRegex(release.ReleaseError, "mutated_duplicate"):
            self.ingest(headers[0] | {"sequence": 43})
        self.assertEqual(self.ingest(self.header("new-42", 42))["state"], "QUEUED")
        self.assertEqual(self.publisher.recover()["state"], "COMMITTED")
        self.assertEqual((self.root / "current-index.json").read_bytes(), before)

    def test_unverified_queued_request_cannot_bypass_later_failed_history(self):
        headers = self.history()
        old = headers[0]
        release.write_json(self.root / "publications/current.json", {"header": old, "state": "RECEIVED"})
        with self.assertRaisesRegex(release.ReleaseError, "stale_sequence"):
            self.publisher.publish(old)

    def test_verified_reconciliation_and_terminal_duplicate_keep_later_pointer(self):
        headers = self.history()
        for state in ("VERIFIED", "RECOVERY_REQUIRED", "COMMITTED"):
            release.write_json(self.root / "publications/current.json", {"header": headers[0], "state": state})
            self.assertEqual(self.publisher.publish(headers[0])["state"], "COMMITTED")
            self.assertEqual(release.read_record(self.root / "current-index.json")["sequence"], 37)

    def test_handoff_marker_cannot_replace_missing_history_or_allow_partial_import(self):
        self.history()
        marker = dict(schema_version=1, handoff_sha256="a" * 64, state="PREPARED", publication_sequence=41)
        for change in ({}, {"state": "BROKEN"}, {"state": "COMMITTED", "publication_sequence": 40},
                       {"state": "COMMITTED", "extra": True}, {"schema_version": True}):
            release.write_json(self.root / "handoff-import.json", marker | change)
            with self.subTest(change=change), self.assertRaises(release.ReleaseError):
                self.ingest(self.header("new-42", 42))
        release.write_json(self.root / "handoff-import.json", marker | {"state": "COMMITTED"})
        self.assertEqual(self.ingest(self.header("new-42", 42))["state"], "QUEUED")

    def test_unknown_corrupt_misnamed_and_duplicate_sequence_history_fail_closed(self):
        headers = self.history()
        path = self.root / "publications/failed-latest.json"
        original = path.read_bytes()
        for change in ({"state": "UNKNOWN"}, {"header": headers[2] | {"sequence": 36}},
                       {"header": headers[2] | {"publication_id": "wrong-id"}}, {"unexpected": 1}):
            release.write_json(path, {"header": headers[2], "state": "FAILED"} | change)
            with self.subTest(change=change), self.assertRaises(release.ReleaseError):
                self.ingest(self.header("new-42", 42))
            path.write_bytes(original)

    def test_killed_atomic_receipt_writer_does_not_poison_durable_history(self):
        headers = self.history()
        code = '''
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import delivery.vps.v8std_mcp_release as r
path = Path(sys.argv[2])
record = r.read_record(path)
def die(*args): os._exit(73)
r.os.replace = die
r.write_json(path, record)
'''
        result = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT),
            str(self.root / "publications/failed-latest.json")], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertEqual(len(list((self.root / "publications").glob(".write-*"))), 1)
        self.assertEqual(self.ingest(self.header("new-42", 42))["state"], "QUEUED")
        self.assertEqual(self.publisher.recover()["state"], "COMMITTED")
        self.assertEqual(self.ingest(headers[2])["state"], "FAILED")

    def test_more_than_ten_thousand_receipts_do_not_permanently_stop_publication(self):
        self.history()
        directory = self.root / "publications"
        for sequence in range(42, 10043):
            header = self.header("failed-" + str(sequence), sequence)
            (directory / (header["publication_id"] + ".json")).write_bytes(
                json.dumps({"header": header, "state": "FAILED"}).encode())
        with self.assertRaisesRegex(release.ReleaseError, "stale_sequence"):
            self.ingest(self.header("stale", 10042))
        self.assertEqual(self.ingest(self.header("next", 10043))["state"], "QUEUED")
        self.assertEqual(self.publisher.recover()["state"], "COMMITTED")


class IngressTests(unittest.TestCase):
    def test_committed_publication_survives_inbox_cleanup_exception(self):
        self.ingest()
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        original = publisher.clear_pending
        for action in ("publish", "reference"):
            for after_unlink in (False, True):
                with self.subTest(action=action, after_unlink=after_unlink):
                    header = self.header | {"publication_id": f"{action}-{int(after_unlink)}",
                        "action": action, "sequence": (20 if action == "reference" else 10) + int(after_unlink)}
                    if action == "publish" and not after_unlink:
                        header = self.header
                    else:
                        self.ingest(header, self.archive if action == "publish" else b"")
                    def fail_cleanup(value):
                        if after_unlink:
                            original(value)
                        raise OSError("injected inbox cleanup error")
                    with patch.object(publisher, "clear_pending", fail_cleanup):
                        result = publisher.recover()
                    self.assertEqual(result["state"], "COMMITTED")
                    self.assertEqual(result["error_code"], "publication_cleanup_failed")
                    query = {"schema_version": 1, "kind": "publication", "id": header["publication_id"]}
                    self.assertEqual(release.query_status(self.root, None, query)["state"], "COMMITTED")
                    archive_hash = header["manifest"]["archive"]["sha256"]
                    target = self.root / "static" / archive_hash / "snapshot.tar.gz"
                    self.assertEqual(target.read_bytes(), self.archive)
                    reference = (self.root / "references" / (archive_hash + ".json")).read_bytes()
                    if action == "reference":
                        self.assertEqual(release.read_record(self.root / "current-index.json"), header)
                    recovered = publisher.recover()
                    self.assertEqual(recovered["state"], "COMMITTED")
                    self.assertNotIn("error_code", recovered)
                    self.assertFalse((self.root / "pending-index.json").exists())
                    self.assertEqual((self.root / "references" / (archive_hash + ".json")).read_bytes(), reference)

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
import delivery.vps.v8std_mcp_release as r
root = Path(sys.argv[2])
original = r.write_json
def crash(path, value):
    original(path, value)
    if path.parent.name == 'publications':
        os._exit(73)
r.write_json = crash
r.ingest(root, root / 'static', sys.stdin.fileno())
'''
        result = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT), str(self.root)],
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
        reference = self.header | {"publication_id": "reference-1", "action": "reference", "sequence": 2}
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
        reference = header | {"publication_id": "ref-1", "action": "reference", "sequence": 2}
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
        reference = self.header | {"publication_id": "reference-1", "action": "reference", "sequence": 2}
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
        reference = self.header | {"publication_id": "reference-1", "action": "reference", "sequence": 2}
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
        with self.assertRaisesRegex(release.ReleaseError, "stale_sequence"):
            self.ingest(stale, b"")
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

    def publish_retention_fixture(self, publisher, name, sequence, now):
        files = fixture.corpus_files()
        files["llms.txt"] += ("\n" + name + "\n").encode()
        archive, manifest = fixture.snapshot_fixture(files=fixture.with_metadata(files))
        manifest["archive"]["path"] = "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["path"]
        header = self.header | {"publication_id": name + "-" + str(sequence), "sequence": sequence,
                                "deadline": int(now) + 300, "manifest": manifest}
        with patch.object(release.time, "time", return_value=now):
            self.ingest(header, archive)
            self.assertEqual(publisher.publish(header)["state"], "COMMITTED")
        return header

    def reference_retention_fixture(self, publisher, published, sequence, now, *, enqueue_only=False):
        header = published | {"publication_id": "ref-" + str(sequence), "sequence": sequence,
                              "action": "reference", "deadline": int(now) + 300}
        with patch.object(release.time, "time", return_value=now):
            self.ingest(header, b"")
            if not enqueue_only:
                self.assertEqual(publisher.publish(header)["state"], "COMMITTED")
        return header

    def test_gc_keeps_public_pages_archive_after_lost_reference_without_later_progress(self):
        now = 1_800_000_000
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        a = self.publish_retention_fixture(publisher, "a", 1, now)
        self.reference_retention_fixture(publisher, a, 2, now)
        b = self.publish_retention_fixture(publisher, "b", 3, now)
        # Pages is a separate owner: host current-index remains A after caller loss.
        release.write_json(self.root / "pages-manifest.json", b["manifest"])
        self.assertFalse((self.root / "pending-index.json").exists())
        release.write_json(self.root / "pins.json", {"archives": []})
        for days in (8, 365):
            self.assertEqual(publisher.gc(now=now + days * 86400), [])
            public = release.read_record(self.root / "pages-manifest.json")
            self.assertTrue((self.root / "static" / public["archive"]["sha256"] / "snapshot.tar.gz").is_file())

    def test_later_reference_starts_grace_for_all_uncertain_archives_and_preserves_pins(self):
        now = 1_800_000_000
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        a = self.publish_retention_fixture(publisher, "a", 1, now)
        self.reference_retention_fixture(publisher, a, 2, now)
        b = self.publish_retention_fixture(publisher, "b", 3, now)
        c = self.publish_retention_fixture(publisher, "c", 4, now)
        release.write_json(self.root / "pins.json", {"archives": []})
        self.assertEqual(publisher.gc(now=now + 8 * 86400), [])
        later = now + 9 * 86400
        reference = self.reference_retention_fixture(publisher, c, 5, later)
        keys = [item["manifest"]["archive"]["sha256"] for item in (a, b, c)]
        self.assertEqual(release.read_record(self.root / "references" / (keys[1] + ".json")),
                         {"last_reference": later})
        self.assertEqual(publisher.gc(now=later + 7 * 86400 - 1), [])
        # An exact retry is not new acknowledged progress and cannot alter grace.
        with patch.object(release.time, "time", return_value=later + 100):
            publisher.publish(reference)
        self.assertEqual(release.read_record(self.root / "references" / (keys[1] + ".json")),
                         {"last_reference": later})
        release.write_json(self.root / "pins.json", {"archives": [keys[1]]})
        self.assertEqual(publisher.gc(now=later + 7 * 86400), [keys[0]])
        release.write_json(self.root / "pins.json", {"archives": []})
        self.assertEqual(publisher.gc(now=later + 7 * 86400), [keys[1]])
        self.assertTrue((self.root / "static" / keys[2] / "snapshot.tar.gz").is_file())

    def test_same_archive_republication_and_stale_reference_do_not_release_uncertainty(self):
        now = 1_800_000_000
        publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
        a = self.publish_retention_fixture(publisher, "a", 1, now)
        self.reference_retention_fixture(publisher, a, 2, now)
        b = self.publish_retention_fixture(publisher, "b", 3, now)
        current = self.reference_retention_fixture(publisher, b, 4, now)
        reused = self.publish_retention_fixture(publisher, "a", 5, now)
        self.assertEqual(reused["manifest"], a["manifest"])
        before = {p.name: p.read_bytes() for p in (self.root / "references").iterdir()}
        with self.assertRaisesRegex(release.ReleaseError, "stale_sequence"):
            self.reference_retention_fixture(publisher, a, 3, now, enqueue_only=True)
        self.assertEqual(release.read_record(self.root / "current-index.json"), current)
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / "references").iterdir()}, before)
        release.write_json(self.root / "pins.json", {"archives": []})
        self.assertEqual(publisher.gc(now=now + 8 * 86400), [])
        later = now + 9 * 86400
        self.reference_retention_fixture(publisher, b, 6, later)
        self.assertEqual(publisher.gc(now=later + 7 * 86400 - 1), [])
        self.assertEqual(publisher.gc(now=later + 7 * 86400), [a["manifest"]["archive"]["sha256"]])

    def test_reference_grace_writes_survive_actual_process_death_and_retry(self):
        code = '''
import os,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import delivery.vps.v8std_mcp_release as r
root, cut, when, now = Path(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
r.time.time = lambda: now
original = r.write_json
def crash(path, value):
    selected = str(path.relative_to(root)) == cut
    if selected and when == 'before': os._exit(73)
    original(path, value)
    if selected and when == 'after': os._exit(73)
r.write_json = crash
r.Publisher(root, root / 'static', lambda *args: None).recover()
'''
        parent = self.root
        now, later = 1_800_000_000, 1_800_000_000 + 9 * 86400
        for cut in ("b", "c", "current-index.json"):
            for when in ("before", "after"):
                with self.subTest(cut=cut, when=when):
                    self.root = parent / (cut + "-" + when)
                    publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
                    a = self.publish_retention_fixture(publisher, "a", 1, now)
                    self.reference_retention_fixture(publisher, a, 2, now)
                    b = self.publish_retention_fixture(publisher, "b", 3, now)
                    c = self.publish_retention_fixture(publisher, "c", 4, now)
                    d = self.publish_retention_fixture(publisher, "d", 5, later)
                    reference = self.reference_retention_fixture(publisher, d, 6, later, enqueue_only=True)
                    keys = [h["manifest"]["archive"]["sha256"] for h in (a, b, c, d)]
                    target = ("references/" + keys[1 if cut == "b" else 2] + ".json"
                              if cut != "current-index.json" else cut)
                    died = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT), str(self.root),
                                           target, when, str(later)], capture_output=True, timeout=5)
                    self.assertEqual(died.returncode, 73, died.stderr)
                    release.write_json(self.root / "pins.json", {"archives": []})
                    self.assertEqual(publisher.gc(now=later + 1), [])
                    # Recreate controller after the interrupted durable writes.
                    publisher = release.Publisher(self.root, self.root / "static", lambda *args: None)
                    with patch.object(release.time, "time", return_value=later + 2):
                        self.assertEqual(publisher.recover()["state"], "COMMITTED")
                    self.assertEqual(release.read_record(self.root / "current-index.json"), reference)
                    self.assertFalse((self.root / "pending-index.json").exists())
                    self.assertEqual(publisher.gc(now=later + 7 * 86400 - 1), [])
                    self.assertEqual(set(publisher.gc(now=later + 7 * 86400 + 2)), set(keys[:3]))
                    self.assertTrue((self.root / "static" / keys[3] / "snapshot.tar.gz").is_file())

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


def bootstrap_window(request):
    now = int(time.time())
    return {"schema_version": 1, "start_utc": now - 60, "end_utc": now + 7000,
            "return_reserve_seconds": 1800, "envelope_sha256": release.digest(release.canonical_json(request)),
            "mode": "stop-start", "legacy_unit": "v8std-mcp.service",
            "legacy_source_sha": "b7bef11e145a188b30e7a7b17df2be4cb1acbd0c",
            "backup_manifest_sha256": "d" * 64,
            "capacity": {"disk_bytes": 1, "available_memory_bytes": 671088640,
                         "file_descriptors": 4096, "network_evidence": "e" * 64}}


class BootstrapBoundaryTests(unittest.TestCase):
    def test_guard_refuses_stale_manager_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            adapter = release.HostAdapter(Path(temp), {})
            def run(argv, deadline):
                if argv[1] == "is-enabled":
                    return b"enabled\n"
                if argv[1] == "is-active":
                    return b"active\n"
                return b"NeedDaemonReload=yes\nDropInPaths=\nLoadState=loaded\n"
            def read(path):
                return {"10-release-guard.conf": release.LEGACY_GUARD,
                        "v8std-bootstrap-recover.service": release.BOOTSTRAP_SERVICE,
                        "v8std-bootstrap-recover.timer": release.BOOTSTRAP_TIMER}[path.name].encode()
            with patch.object(release, "trusted_path"), patch.object(release, "read_file", read), patch.object(release, "run", run):
                with self.assertRaisesRegex(release.ReleaseError, "bootstrap_guard_loaded"):
                    adapter.arm_bootstrap_guard(time.monotonic() + 2)

    def test_installed_boot_guard_templates_and_ci_exclusion(self):
        for name, expected in (("legacy-release-guard.conf", release.LEGACY_GUARD),
                               ("v8std-bootstrap-recover.service", release.BOOTSTRAP_SERVICE),
                               ("v8std-bootstrap-recover.timer", release.BOOTSTRAP_TIMER)):
            self.assertEqual((ROOT / "delivery/vps" / name).read_text(), expected)
        self.assertNotIn("Before=v8std-mcp.service", release.BOOTSTRAP_SERVICE)
        self.assertNotIn("ExecStart=", release.LEGACY_GUARD)  # Original legacy command preserved.
        for command in ("bootstrap", "bootstrap-status", "bootstrap-recover", "_bootstrap", "_legacy-allowed"):
            result = subprocess.run([sys.executable, "-I", str(ROOT / "delivery/vps/release-entry.py")],
                env={"SSH_ORIGINAL_COMMAND": command}, capture_output=True, timeout=2)
            self.assertNotEqual(result.returncode, 0)

    def test_window_exact_identity_time_and_fixed_targets(self):
        request = envelope()
        window = bootstrap_window(request)
        self.assertEqual(release.validate_bootstrap_window(window, request), window)
        for change in ({"start_utc": int(time.time()) + 1}, {"end_utc": int(time.time()) + 1800},
                       {"end_utc": window["start_utc"] + 7201}, {"return_reserve_seconds": 1799},
                       {"envelope_sha256": "f" * 64}, {"legacy_unit": "sshd.service"},
                       {"backup_path": "/etc"}, {"mode": "automatic"}, {"start_utc": True}):
            with self.subTest(change=change), self.assertRaises(release.ReleaseError):
                release.validate_bootstrap_window(window | change, request)
        # Recovery is an owed duty, not new window authority.
        expired = window | {"start_utc": 1, "end_utc": 7201}
        self.assertEqual(release.validate_bootstrap_window(expired, request, recovery=True), expired)

    def test_boot_guard_denies_pending_and_accepted_legacy_start(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertTrue(release.legacy_start_allowed(root))
            journal = {"kind": "bootstrap", "envelope": envelope(), "state": "VERIFIED",
                       "intent": "stop_legacy", "legacy_start_allowed": False}
            release.write_json(root / "releases/release-1.json", journal)
            self.assertFalse(release.legacy_start_allowed(root))
            journal["legacy_start_allowed"] = True
            release.write_json(root / "releases/release-1.json", journal)
            self.assertTrue(release.legacy_start_allowed(root))
            journal["state"] = "COMMITTED"
            release.write_json(root / "releases/release-1.json", journal)
            self.assertFalse(release.legacy_start_allowed(root))
            (root / "releases/release-1.json").write_bytes(b"broken")
            with self.assertRaises(release.ReleaseError):
                release.legacy_start_allowed(root)


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
        if fault.startswith("kill_active_"):
            self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr.decode())
        elif fault.startswith(("crash_", "intent_")):
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

    def test_smoke_accepts_real_held_tools_only_runtime(self):
        health = release.smoke(self.adapter.url(self.previous), self.previous, time.monotonic() + 30)
        self.assertEqual(health["hold_token"], self.previous["hold_token"])
        self.assertEqual(health["runtime_sha"], self.previous["runtime_source_sha"])
        self.assertEqual(health["corpus_id"], self.source.manifest["corpus_id"])
        self.assertEqual(health["archive_sha256"], self.source.manifest["archive"]["sha256"])

    def test_reboot_after_complete_commit_restores_accepted_container(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        active = json.loads((self.root / "active.json").read_text())
        self.adapter.stop(active, time.monotonic() + 5)
        self.assertEqual(self.invoke(mode="recover")["state"], "COMMITTED")
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])

    def test_accepted_recovery_readiness_is_capped_at_90_seconds(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        active = release.read_record(self.root / "active.json")
        self.adapter.stop(active, time.monotonic() + 5)
        allowances = []
        def blocked_hold(record, token, deadline, manifest=None):
            allowances.append(deadline - time.monotonic())
            raise release.ReleaseError("deadline")
        with patch.object(self.adapter, "hold", blocked_hold):
            result = release.Controller(self.root, self.adapter).recover()
        self.assertEqual(result["error_code"], "active_recovery_failed")
        self.assertEqual(len(allowances), 1)
        self.assertLessEqual(allowances[0], release.READINESS)
        self.assertFalse(result["cleanup_complete"])

    def test_rejected_queued_release_id_is_immutable_and_exactly_idempotent(self):
        with patch.object(release, "schedule"):
            self.assertEqual(release.submit(self.root, self.adapter, release.canonical_json(self.env))["state"], "QUEUED")
        self.invoke(mode="queued_expired")  # Actual worker, clock advanced past work allowance.
        query = {"schema_version": 1, "kind": "release", "id": self.env["release_id"]}
        rejected = release.query_status(self.root, self.adapter, query)
        self.assertEqual(rejected["state"], "REJECTED")
        self.assertEqual(rejected["error_code"], "insufficient_transaction_budget")
        self.assertFalse((self.root / "pending-deploy.json").exists())
        with patch.object(release, "schedule") as schedule:
            self.assertEqual(release.submit(self.root, self.adapter, release.canonical_json(self.env)), rejected)
            self.assertEqual(release.Controller(self.root, self.adapter).deploy(release.canonical_json(self.env)), rejected)
            for change in ({"deadline": self.env["deadline"] + 1}, {"runtime_source_sha": "f" * 40}):
                with self.assertRaisesRegex(release.ReleaseError, "mutated_duplicate"):
                    release.submit(self.root, self.adapter, release.canonical_json(self.env | change))
            schedule.assert_not_called()
        self.assertFalse((self.root / "pending-deploy.json").exists())
        # Crash after writing REJECTED but before deleting the durable inbox.
        release.write_json(self.root / "pending-deploy.json", self.env)
        self.invoke(mode="queued_expired")
        self.assertFalse((self.root / "pending-deploy.json").exists())
        self.assertEqual(release.query_status(self.root, self.adapter, query), rejected)

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


def active_recovery_crash_case(fault):
    def test(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        active = release.read_record(self.root / "active.json")
        self.adapter.stop(active, time.monotonic() + 5)
        # A restarted process is not proof the public upstream/smoke/resume ran.
        release.write_json(self.root / "edge.json", {"port": self.previous["port"]})
        self.invoke(fault, mode="recover")
        process = self.adapter.inspect(active, time.monotonic() + 2)
        self.assertTrue(process["State"]["Running"])
        self.assertFalse(release.Controller(self.root, self.adapter).status()["cleanup_complete"])
        with self.assertRaisesRegex(release.ReleaseError, "recovery_pending"):
            release.Controller(self.root, self.adapter).existing(self.env | {"release_id": "next", "sequence": 2})
        result = self.invoke(mode="recover")
        self.assertEqual(result["state"], "COMMITTED")
        self.assertTrue(result["cleanup_complete"])
        self.assertIsNone(result["error_code"])
        state = self.health()
        self.assertEqual(state["runtime_sha"], active["runtime_source_sha"])
        self.assertEqual(state["archive_sha256"], active["archive_sha256"])
        self.assertIsNone(state["hold_token"])
        self.source.next_generation()
        eventually(lambda: (self.health() or {}).get("corpus_id") == self.source.manifest["corpus_id"])
        self.assertFalse(self.adapter.inspect(self.previous, time.monotonic() + 1)["State"]["Running"])
    return test


for _fault in ("kill_active_after_start", "kill_active_after_smoke", "kill_active_before_resume"):
    setattr(TransactionTests, "test_" + _fault, active_recovery_crash_case(_fault))


for _fault in ("crash_RECEIVED", "crash_VERIFIED", "crash_PREPARED", "crash_READY", "crash_SWITCHED",
               "crash_after_start", "intent_pin_predecessor", "intent_pull_candidate", "intent_start_candidate"):
    setattr(TransactionTests, "test_recovery_" + _fault, crash_case(_fault))


class BootstrapProcessTests(unittest.TestCase):
    install_snapshot = TransactionTests.install_snapshot

    def health(self):
        # This independent observer includes spawning an HTTP worker. The former
        # 300ms harness allowance is not a product readiness requirement and is
        # below process startup jitter on the one-CPU Linux fixture. Stay below
        # the controller's existing3s read cap; transaction/ready budgets do not
        # change. Real identity/smoke gates are still executed by the controller.
        try:
            return json.loads(release.http(self.policy["public_url"] + "/healthz", time.monotonic() + 2))
        except release.ReleaseError as error:
            self.last_probe_error = error.code
            return None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v8std-bootstrap-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.source = Source()
        self.addCleanup(self.source.close)
        self.environment = bootstrap_environment(self.root)
        self.addCleanup(self.environment.close)
        self.addCleanup(self.stop_owned)
        config = {"site_url": self.source.url, "refresh_seconds": 1, "max_snippet_chars": 4000,
                  "memory_bytes": 536870912, "cpus": 1}
        key = release.digest(release.canonical_json(config))
        self.policy = {"runtime_enabled": False, "configs": {key: config}, "ports": [port(), port()],
                       "public_url": f"http://127.0.0.1:{port()}"}
        self.env = envelope() | {"configuration_digest": key, "corpus_id": self.source.manifest["corpus_id"],
                                 "archive_sha256": self.source.manifest["archive"]["sha256"]}
        self.window = bootstrap_window(self.env)
        release.write_json(self.root / "legacy-port.json", {"port": port()})
        self.files = fixture.corpus_files()
        self.window["backup_manifest_sha256"] = prepare_legacy(self.root, self.files)
        for filename, value in (("policy.json", self.policy), ("envelope.json", self.env), ("window.json", self.window)):
            release.write_json(self.root / filename, value)
        self.install_snapshot()
        self.adapter = BootstrapAdapter(self.root, self.policy)
        self.adapter.legacy_restore(self.window, time.monotonic() + 5)
        self.adapter.legacy_start(time.monotonic() + 5)
        (self.root / "guard-paused").touch()
        with (self.root / "edge.log").open("wb") as log:
            self.edge = subprocess.Popen([sys.executable, "-m", "tests.mcp_release_fixture", "edge",
                str(self.root), self.policy["public_url"].rsplit(":", 1)[1]], cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log)
        try:
            eventually(self.health)
        except AssertionError:
            self.fail((self.root / "legacy.log").read_text())
        self.static_errors = []
        self.static_samples = 0
        self.static_stop = threading.Event()
        def sample():
            while not self.static_stop.is_set():
                try:
                    self.assert_static()
                    self.static_samples += 1
                except Exception as error:
                    self.static_errors.append(str(error))
                self.static_stop.wait(.1)
        self.static_thread = threading.Thread(target=sample)
        self.static_thread.start()

    def stop_owned(self):
        if hasattr(self, "static_thread"):
            self.static_stop.set()
            self.static_thread.join(3)
        guard = self.root / "guard.json"
        if guard.exists():
            pid = release.read_record(guard)["pid"]
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        for path in (self.root / "processes").glob("*.json"):
            record = release.read_record(path)["record"]
            self.adapter.stop(record, time.monotonic() + 5)
        for child in getattr(self, "adapter", ProcessAdapter(self.root, {})).children:
            child.poll()
        if hasattr(self, "edge"):
            self.edge.terminate()
            self.edge.wait(5)

    def invoke(self, fault="", mode="bootstrap"):
        # Crash survivors (including multiprocessing's resource tracker) must
        # not keep a PIPE's EOF open after the controller itself has exited.
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
            result = subprocess.run([sys.executable, "-m", "tests.mcp_release_fixture", mode, str(self.root), fault],
                cwd=ROOT, stdout=output, stderr=error, timeout=25)
            output.seek(0)
            error.seek(0)
            result.stdout, result.stderr = output.read(), error.read()
        if fault.startswith("kill_"):
            self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr.decode())
            outcome = release.Controller(self.root, self.adapter).status()
        else:
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            outcome = json.loads(result.stdout)
        self.assertEqual(self.static_errors, [])
        self.assertGreater(self.static_samples, 0)
        if self.window["mode"] == "stop-start":
            observations = [json.loads(line) for line in (self.root / "observations.jsonl").read_text().splitlines()]
            self.assertTrue(observations)
            self.assertLessEqual(max(len(x["live_runtimes"]) for x in observations), 1)
        return outcome

    def assert_legacy(self):
        self.adapter.legacy_check(self.window, time.monotonic() + 8, public=True)
        health = self.health()
        self.assertEqual(health["sha256"], release.digest(self.files["pages.jsonl"]))
        self.assertEqual(health["vectors"]["sha256"], release.digest(self.files["search-vectors.jsonl"]))
        observed = release.read_record(self.root / "legacy-observed.json")
        self.assertEqual(observed["source_sha"], LEGACY_SHA)
        self.assertEqual(observed["server_sha256"], "be1e73a27ad2c2aea08a516ffeede6286feb92a70752e964a13bd8567139d713")
        self.assertEqual(observed["refresh_seconds"], 3600)
        self.assertEqual(observed["index_url"], "https://v8std.ru/ai/pages.jsonl")
        self.assertFalse((self.root / "legacy-network.jsonl").exists())
        live_candidates = [p for p in (self.root / "processes").glob("*.json") if p.stem != "legacy"
            and self.adapter.inspect(release.read_record(p)["record"], time.monotonic() + 1)["State"]["Running"]]
        self.assertEqual(live_candidates, [])
        self.assert_static()

    def assert_static(self):
        import http.client
        client = http.client.HTTPConnection("127.0.0.1", int(self.policy["public_url"].rsplit(":", 1)[1]), timeout=2)
        try:
            path = "/indexes/v1/" + self.env["archive_sha256"] + "/snapshot.tar.gz"
            for method in ("GET", "HEAD"):
                client.request(method, path)
                response = client.getresponse()
                data = response.read()
                self.assertEqual(response.status, 200)
                self.assertEqual(int(response.getheader("Content-Length")), len(self.source.archive))
                if method == "GET":
                    self.assertEqual(release.digest(data), self.env["archive_sha256"])
        finally:
            client.close()

    def test_success_only_after_smoke_without_autoactivation(self):
        result = self.invoke()
        self.assertEqual(result["state"], "COMMITTED", result)
        self.assertTrue(result["cleanup_complete"], result)
        self.assertFalse(self.policy["runtime_enabled"])
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])
        self.assertFalse(release.legacy_start_allowed(self.root))
        self.assertFalse(self.adapter.inspect(self.adapter.legacy_record(), time.monotonic() + 1)["State"]["Running"])
        self.assert_static()

    def test_boundary_rejections_preserve_original_endpoint(self):
        for change in ({"end_utc": int(time.time()) - 1}, {"envelope_sha256": "f" * 64}):
            release.write_json(self.root / "window.json", self.window | change)
            self.assertEqual(self.invoke()["state"], "REJECTED")
            self.assertFalse((self.root / "releases/release-1.json").exists())
            self.assert_legacy()
        (self.root / "window.json").unlink()
        self.assertEqual(self.invoke()["state"], "REJECTED")
        release.write_json(self.root / "window.json", self.window)
        release.write_json(self.root / "active.json", {"existing": True})
        self.assertEqual(self.invoke()["error_code"], "bootstrap_already_accepted")
        self.assert_legacy()

    def test_capacity_rejection_no_stop(self):
        result = self.invoke("capacity")
        self.assertEqual(result["state"], "FAILED", result)
        self.assertFalse((self.root / "guard.json").exists())
        self.assert_legacy()

    def test_complete_backup_paths_and_directory_permissions(self):
        self.assertEqual((self.root / "restored-app/scripts").stat().st_mode & 0o777, 0o755)
        release.atomic(self.root / "restored-app/scripts/unlisted.py", b"untrusted code")
        result = self.invoke()
        self.assertEqual(result["state"], "FAILED", result)
        self.assertEqual(result["error_code"], "legacy_unlisted")
        self.assertFalse((self.root / "guard.json").exists())

    def test_accept_persistence_failure_rolls_back(self):
        result = self.invoke("accept_persist_failure")
        self.assertEqual(result["state"], "ROLLED_BACK", result)
        self.assertFalse((self.root / "active.json").exists())
        self.assert_legacy()

    def test_active_persistence_failure_preserves_committed(self):
        result = self.invoke("active_persist_failure")
        self.assertEqual(result["state"], "COMMITTED", result)
        self.assertFalse(result["cleanup_complete"])
        self.assertFalse((self.root / "active.json").exists())
        self.assertFalse(release.legacy_start_allowed(self.root))
        result = self.invoke(mode="bootstrap-recover")
        self.assertTrue(result["cleanup_complete"], result)
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])

    def test_reboot_fence_prevents_enabled_legacy_racing_accepted_recovery(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        active = release.read_record(self.root / "active.json")
        self.adapter.stop(active, time.monotonic() + 5)
        self.assertEqual(self.invoke(mode="bootstrap-legacy-start")["error_code"], "legacy_fenced")
        result = self.invoke(mode="bootstrap-recover")
        self.assertTrue(result["cleanup_complete"], result)
        self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])
        self.assertFalse(self.adapter.inspect(self.adapter.legacy_record(), time.monotonic() + 1)["State"]["Running"])

    def test_rollback_failure_retains_owed_recovery_and_usage_logs(self):
        usage = self.root / "restored-cache/tool-usage.jsonl"
        usage.write_bytes(b"test-private-usage-before\n")
        result = self.invoke("public_dead,legacy_restore")
        self.assertEqual(result["state"], "RECOVERY_REQUIRED", result)
        self.assertFalse(result["cleanup_complete"])
        self.assert_static()
        with usage.open("ab") as stream:
            stream.write(b"test-private-usage-after\n")
        result = self.invoke(mode="bootstrap-recover")
        self.assertEqual(result["state"], "ROLLED_BACK", result)
        self.assertEqual(usage.read_bytes(), b"test-private-usage-before\ntest-private-usage-after\n")
        self.assertNotIn("test-private", json.dumps(result))
        self.assert_legacy()

    def test_retry_rollback_closes_boot_fence_before_rewriting_files(self):
        self.assertEqual(self.invoke("public_dead,legacy_public")["state"], "RECOVERY_REQUIRED")
        self.assertTrue(release.legacy_start_allowed(self.root))
        self.invoke("kill_restore_legacy", mode="bootstrap-recover")
        self.assertFalse(release.legacy_start_allowed(self.root))
        self.assertEqual(self.invoke(mode="bootstrap-recover")["state"], "ROLLED_BACK")
        self.assert_legacy()

    def test_kill_during_file_restore_retries_without_unlisted_temp_blocker(self):
        self.invoke("kill_during_restore,public_dead")
        self.assertFalse(release.legacy_start_allowed(self.root))
        self.assertEqual(self.invoke(mode="bootstrap-recover")["state"], "ROLLED_BACK")
        self.assert_legacy()

    def test_queued_caller_loss_and_expiry_have_no_stop_authority(self):
        with patch.object(release, "schedule", side_effect=release.ReleaseError("command_failed")):
            with self.assertRaises(release.ReleaseError):
                release.BootstrapController(self.root, self.adapter).submit(release.canonical_json(self.env))
        self.assertEqual(release.Controller(self.root, self.adapter).status()["state"], "RECEIVED")
        release.write_json(self.root / "window.json", self.window | {"start_utc": 1, "end_utc": 7201})
        self.assertEqual(self.invoke(mode="bootstrap-recover")["state"], "FAILED")
        self.assertFalse((self.root / "guard.json").exists())
        self.assert_legacy()

    def test_backup_hash_failure_has_no_stop(self):
        (self.root / "legacy/cache/pages.jsonl").write_bytes(b"changed backup")
        result = self.invoke()
        self.assertEqual(result["error_code"], "backup_hash", result)
        self.assertEqual(result["state"], "FAILED")
        self.assertFalse((self.root / "guard.json").exists())
        self.assertEqual(self.health()["sha256"], release.digest(self.files["pages.jsonl"]))

    def test_backup_rejects_traversal_and_external_link_before_restore(self):
        path = self.root / "legacy/manifest.json"
        original = release.read_record(path)
        for attack in ("path", "link"):
            bad = json.loads(json.dumps(original))
            if attack == "path":
                bad["app"]["../outside"] = original["app"]["scripts/v8std_mcp_server.py"]
                bad["directories"]["app"][".."] = original["directories"]["app"]["."]
            else:
                bad["app"]["venv/bin/python"] = {"link": "/etc/shadow"}
            release.write_json(path, bad)
            window = self.window | {"backup_manifest_sha256": release.digest(path.read_bytes())}
            with self.assertRaisesRegex(release.ReleaseError, "backup_path|backup_link"):
                self.adapter.bootstrap_backup(window, time.monotonic() + 3)
        self.assertFalse((self.root / "outside").exists())

    def test_readiness_cancels_actual_worker_and_restores_legacy(self):
        result = self.invoke("ready")
        self.assertEqual(result["state"], "ROLLED_BACK", result)
        self.assert_legacy()

    def test_post_stop_capacity_failure_restores_legacy(self):
        result = self.invoke("capacity_after_stop")
        self.assertEqual(result["state"], "ROLLED_BACK", result)
        self.assert_legacy()

    def test_recovery_readiness_is_capped_and_durable(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        active = release.read_record(self.root / "active.json")
        self.adapter.stop(active, time.monotonic() + 5)
        allowances = []
        def blocked(record, token, deadline, manifest=None):
            allowances.append(deadline - time.monotonic())
            raise release.ReleaseError("deadline")
        with patch.object(self.adapter, "hold", blocked):
            result = release.Controller(self.root, self.adapter).recover()
        self.assertLessEqual(allowances[0], 90)
        self.assertEqual(result["state"], "COMMITTED")
        self.assertFalse(result["cleanup_complete"])
        self.assertFalse(release.legacy_start_allowed(self.root))
        self.assertTrue(self.invoke(mode="bootstrap-recover")["cleanup_complete"])

    def test_overlap_keeps_old_until_public_smoke(self):
        self.window["mode"] = "overlap"
        release.write_json(self.root / "window.json", self.window)
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        operations = [json.loads(line)["operation"] for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertGreater(operations.index("legacy_stop"), operations.index("public"))

    def test_recovery_is_durable_after_accepted_restart_then_kill(self):
        self.assertEqual(self.invoke()["state"], "COMMITTED")
        active = release.read_record(self.root / "active.json")
        self.adapter.stop(active, time.monotonic() + 5)
        self.invoke("kill_after_candidate_start", mode="bootstrap-recover")
        self.assertFalse(release.Controller(self.root, self.adapter).status()["cleanup_complete"])
        result = self.invoke(mode="bootstrap-recover")
        self.assertTrue(result["cleanup_complete"], result)
        self.assertEqual(self.health()["runtime_sha"], active["runtime_source_sha"])
        self.assertIsNone(self.health()["hold_token"])

    def test_caller_loss_guard_recovers_after_window_expiry(self):
        self.invoke("kill_after_legacy_stop")
        self.assertFalse(self.health())
        self.assert_static()
        release.write_json(self.root / "window.json", self.window | {"start_utc": 1, "end_utc": 7201})
        # The durable attempt, not newly revoked window input, drives recovery.
        (self.root / "guard-paused").unlink()
        eventually(lambda: release.Controller(self.root, self.adapter).status().get("state") == "ROLLED_BACK", timeout=12)
        self.assert_legacy()

    def test_actual_old_full_cache_restart_default_urls_without_network(self):
        import shutil
        self.adapter.legacy_stop(time.monotonic() + 5)
        # Generated cache is not tracked in Git. Its bytes become the protected
        # fixture's hash-checked input; only executable legacy code uses history.
        paths = {name: ROOT / "docs" / ("ai" if name.endswith(".jsonl") else "") / name for name in release.LEGACY_CACHE}
        if not all(path.is_file() for path in paths.values()):
            self.skipTest("generated full cache unavailable; tiny-cache regression remains mandatory")
        self.files = {name: path.read_bytes() for name, path in paths.items()}
        self.window["backup_manifest_sha256"] = prepare_legacy(self.root, self.files)
        release.write_json(self.root / "window.json", self.window)
        # Keep the negative control permanently: a preserved stale timestamp
        # attempts remote HTTP even though fallback eventually serves the cache.
        for name in release.LEGACY_CACHE:
            shutil.copy2(self.root / "legacy/cache" / name, self.root / "restored-cache" / name)
        self.adapter.legacy_start(time.monotonic() + 5)
        eventually(lambda: (self.health() or {}).get("row_count") == len(self.files["pages.jsonl"].splitlines()), timeout=15)
        self.assertTrue((self.root / "legacy-network.jsonl").exists())
        self.adapter.legacy_stop(time.monotonic() + 5)
        (self.root / "legacy-network.jsonl").unlink()
        self.adapter.legacy_restore(self.window, time.monotonic() + 10)
        self.adapter.legacy_start(time.monotonic() + 5)
        eventually(lambda: (self.health() or {}).get("row_count") == len(self.files["pages.jsonl"].splitlines()), timeout=15)
        self.assert_legacy()


def bootstrap_crash_case(fault, accepted=False):
    def test(self):
        self.invoke(fault)
        self.assert_static()
        result = self.invoke(mode="bootstrap-recover")
        self.assertEqual(result["state"], "COMMITTED" if accepted else "ROLLED_BACK", result)
        self.assertTrue(result["cleanup_complete"], result)
        if accepted:
            self.assertEqual(self.health()["runtime_sha"], self.env["runtime_source_sha"])
            self.assertFalse(release.legacy_start_allowed(self.root))
        else:
            self.assert_legacy()
        before = (self.root / "calls.jsonl").read_bytes()
        self.assertEqual(self.invoke(), result)
        self.assertEqual((self.root / "calls.jsonl").read_bytes(), before)
        release.write_json(self.root / "envelope.json", self.env | {"trigger_sha": "f" * 40})
        self.assertEqual(self.invoke()["error_code"], "mutated_duplicate")
    return test


for _fault in ("kill_guard_armed", "kill_stop_legacy", "kill_after_legacy_stop", "kill_start_candidate",
               "kill_after_candidate_start", "kill_PREPARED", "kill_READY", "kill_after_switch", "kill_SWITCHED"):
    setattr(BootstrapProcessTests, "test_" + _fault, bootstrap_crash_case(_fault))
for _fault in ("kill_COMMITTED", "kill_after_active", "kill_resume_candidate"):
    setattr(BootstrapProcessTests, "test_" + _fault, bootstrap_crash_case(_fault, accepted=True))


if __name__ == "__main__":
    unittest.main()
