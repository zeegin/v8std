"""Publication transfer conformance on real files, snapshots and journals."""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from tests import mcp_snapshot_fixtures as fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import delivery.vps.v8std_mcp_release as release


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


@unittest.skip("Archived handoff proposal has no implementation or approved active rule; spec/architecture-review.md")
class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("v8std_mcp_handoff"),
                             "handoff export/import behavior is not implemented")
        self.h = importlib.import_module("v8std_mcp_handoff")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root, self.store, self.output = (self.base / x for x in ("state", "objects", "transfer"))
        self.now = 1_000_000
        self.artifacts, self.headers = {}, {}
        self.reject_sha = None
        self.mutate_source = None
        self.verifier = self.h.HandoffVerifier("linux/amd64")
        for owner in (release, self.h):
            p = patch.object(owner, "run", self.command)
            p.start()
            self.addCleanup(p.stop)
        self.publisher = release.Publisher(self.root, self.store)
        self.publish("collected", 10, 1)
        self.reference("collected", "old-ack", 11, 1)
        self.publish("grace", 20, 10)
        self.reference("grace", "grace-ack", 21, 10)
        self.publish("current", 36, 999_990)
        self.reference("current", "current-ack", 37, 999_990)
        self.publish("uncertain", 39, 999_995)
        self.reject_sha = "c" * 40
        self.publish("failed-latest", 41, 999_996, trigger="c" * 40, failed=True)
        self.reject_sha = None
        # Legitimate maintenance collects the old, unprotected object only.
        release.write_json(self.root / "pins.json", {"archives": []})
        self.assertEqual(self.publisher.gc(now=self.now), [self.key("collected")])
        (self.root / "pins.json").unlink()
        child = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                 "config": {"mediaType": "application/vnd.oci.image.config.v1+json", "digest": "sha256:" + "c" * 64}, "layers": []}
        self.child = encoded(child)
        child_digest = "sha256:" + hashlib.sha256(self.child).hexdigest()
        self.index = encoded({"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [{"mediaType": child["mediaType"], "digest": child_digest,
                           "size": len(self.child), "platform": {"os": "linux", "architecture": "amd64"}}]})
        self.envelope = dict(schema_version=1, release_id="runtime-transfer", sequence=5,
            runtime_source_sha="a" * 40, trigger_sha="b" * 40, image="ghcr.io/zeegin/v8std-mcp",
            image_digest="sha256:" + hashlib.sha256(self.index).hexdigest(), platform_digest=child_digest,
            configuration_digest="3" * 64, corpus_id=self.headers["current"]["manifest"]["corpus_id"],
            archive_sha256=self.key("current"), deadline=100)

    def key(self, name):
        return self.headers[name]["manifest"]["archive"]["sha256"]

    def command(self, argv, deadline, *, cwd=None, **kwargs):
        if argv[:3] == ["gh", "attestation", "download"]:
            self.assertIsNotNone(cwd)
            self.assertEqual(argv[4:], ["--repo", "zeegin/v8std"])
            subject = argv[3]
            key = subject.rsplit("@sha256:", 1)[1] if subject.startswith("oci://") else hashlib.sha256(Path(subject).read_bytes()).hexdigest()
            (Path(cwd) / ("sha256:" + key + ".jsonl")).write_bytes(encoded({"digest": key, "signed": True}) + b"\n")
            return b""
        if argv[:3] == ["gh", "attestation", "verify"]:
            for flag, value in (("--repo", "zeegin/v8std"), ("--signer-workflow", "zeegin/v8std/.github/workflows/ci.yml"),
                                ("--source-ref", "refs/heads/main"), ("--cert-oidc-issuer", "https://token.actions.githubusercontent.com")):
                self.assertEqual(argv[argv.index(flag) + 1], value)
            self.assertIn("--deny-self-hosted-runners", argv)
            source = argv[argv.index("--source-digest") + 1]
            if source not in {"1" * 40, "a" * 40}:
                raise release.ReleaseError("command_failed")
            if "--bundle" in argv:
                subject = argv[3]
                key = subject.rsplit("@sha256:", 1)[1] if subject.startswith("oci://") else hashlib.sha256(Path(subject).read_bytes()).hexdigest()
                proof = json.loads(Path(argv[argv.index("--bundle") + 1]).read_bytes())
                if proof != {"digest": key, "signed": True}:
                    raise release.ReleaseError("command_failed")
            return b"[]"
        if argv[:2] == ["gh", "api"]:
            sha = argv[2].split("/compare/")[1].split("...")[0]
            if self.mutate_source:
                action, self.mutate_source = self.mutate_source, None
                action()
            return encoded({"status": "behind" if sha == self.reject_sha else "identical", "merge_base_commit": {"sha": sha}})
        if argv[:5] == ["docker", "buildx", "imagetools", "inspect", "--raw"]:
            return self.index if argv[5].endswith(self.envelope["image_digest"]) else self.child
        self.fail("unexpected external transport")

    def ingest(self, root, store, header, archive):
        with tempfile.TemporaryFile() as stream:
            stream.write(encoded(header) + b"\n" + (archive if header["action"] == "publish" else b""))
            stream.seek(0)
            return release.ingest(root, store, stream.fileno())

    def publish(self, name, sequence, when, *, trigger="b" * 40, failed=False):
        files = fixture.corpus_files()
        files["llms.txt"] += name.encode()
        archive, manifest = fixture.snapshot_fixture(files=fixture.with_metadata(files))
        manifest["archive"]["path"] = "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["path"]
        header = dict(schema_version=1, publication_id=name, sequence=sequence, trigger_sha=trigger,
                      manifest=manifest, deadline=int(time.time()) + 300, action="publish")
        self.artifacts[name], self.headers[name] = archive, header
        self.ingest(self.root, self.store, header, archive)
        self.assertEqual(self.publisher.recover()["state"], "FAILED" if failed else "COMMITTED")
        if not failed:
            release.write_json(self.root / "references" / (self.key(name) + ".json"), {"last_reference": when})

    def reference(self, name, identity, sequence, when):
        header = self.headers[name] | {"publication_id": identity, "sequence": sequence, "action": "reference"}
        self.ingest(self.root, self.store, header, b"")
        self.assertEqual(self.publisher.recover()["state"], "COMMITTED")
        # Clock-independent fixture of the actual acknowledgement's retention set.
        for path in (self.root / "references").iterdir():
            previous = json.loads(path.read_bytes())["last_reference"]
            if previous > 1 or name == "collected":
                release.write_json(path, {"last_reference": when})

    def export(self):
        return self.h.export_handoff(self.root, self.store, self.output, self.envelope, self.verifier, now=self.now)

    def imported(self, report):
        target, objects = self.base / "new-state", self.base / "new-objects"
        result = self.h.import_handoff(target, objects, self.output, report["handoff_sha256"], self.verifier)
        return target, objects, result

    def rewrite_inventory(self):
        path = self.output / "handoff.json"
        manifest = json.loads(path.read_bytes())
        for name in list(manifest["files"]):
            source = self.output / name
            if not source.exists():
                del manifest["files"][name]
            else:
                raw = source.read_bytes()
                manifest["files"][name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        path.write_bytes(encoded(manifest))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_round_trip_preserves_history_watermark_and_real_gc(self):
        release.write_json(self.root / "active.json", {"private": "must-not-transfer"})
        (self.root / "secret-token").write_text("never transfer")
        report = self.export()
        self.assertEqual(report["publication_sequence"], 41)
        self.assertEqual(report["archives"], 3)
        target, objects, result = self.imported(report)
        self.assertEqual(result, {"state": "IMPORTED", "handoff_sha256": report["handoff_sha256"], "publication_sequence": 41})
        self.assertEqual(release.read_record(target / "current-index.json")["sequence"], 37)
        self.assertEqual(release.read_record(target / "publications/failed-latest.json")["state"], "FAILED")
        self.assertEqual((objects / self.key("uncertain") / "snapshot.tar.gz").read_bytes(), self.artifacts["uncertain"])
        self.assertFalse((objects / self.key("collected")).exists())
        self.assertTrue((target / "manifests" / (self.key("collected") + ".json")).exists())
        self.assertEqual({p.name for p in target.iterdir()}, {"release.lock", "publications", "manifests", "references",
                        "current-index.json", "handoff-import.json", "handoff-proofs"})
        for name in ("current", "grace", "uncertain", "collected"):
            relative = Path("references") / (self.key(name) + ".json")
            self.assertEqual((target / relative).read_bytes(), (self.root / relative).read_bytes())
        with self.assertRaisesRegex(release.ReleaseError, "stale_sequence"):
            self.ingest(target, objects, self.headers["current"] | {"publication_id": "stale-40", "sequence": 40}, self.artifacts["current"])
        self.assertEqual(self.ingest(target, objects, self.headers["failed-latest"], self.artifacts["failed-latest"])["state"], "FAILED")
        self.assertEqual(self.h.import_handoff(target, objects, self.output, report["handoff_sha256"], self.verifier), result)
        release.write_json(target / "pins.json", {"archives": []})
        publisher = release.Publisher(target, objects)
        self.assertEqual(publisher.gc(now=self.now), [])
        self.assertEqual(publisher.gc(now=self.now + 7 * 86400), [self.key("grace")])
        self.assertTrue((objects / self.key("uncertain") / "snapshot.tar.gz").exists())
        # COMMITTED replay does not reconstruct collected objects or reset later state.
        self.assertEqual(self.h.import_handoff(target, objects, self.output, report["handoff_sha256"], self.verifier), result)
        self.assertFalse((objects / self.key("grace")).exists())

    def test_missing_protected_archive_and_unfinished_history_are_rejected(self):
        for name in ("current", "uncertain", "grace"):
            path = self.store / self.key(name) / "snapshot.tar.gz"
            raw = path.read_bytes()
            path.unlink()
            with self.subTest(name=name), self.assertRaises(release.ReleaseError):
                self.export()
            path.write_bytes(raw)
        release.write_json(self.root / "pending-index.json", self.headers["current"])
        with self.assertRaises(release.ReleaseError):
            self.export()

    def test_inventory_hash_and_provenance_are_rechecked_before_target_write(self):
        report = self.export()
        with self.assertRaises(release.ReleaseError):
            self.h.validate_handoff(self.output, "0" * 64, self.verifier)
        self.reject_sha = "a" * 40
        with self.assertRaisesRegex(release.ReleaseError, "main_ancestry"):
            self.imported(report)
        self.assertFalse((self.base / "new-state").exists())
        self.reject_sha = None
        path = self.output / "objects" / self.key("uncertain") / "snapshot.tar.gz"
        path.write_bytes(b"mutated")
        with self.assertRaises(release.ReleaseError):
            self.h.validate_handoff(self.output, self.rewrite_inventory(), self.verifier)


if __name__ == "__main__":
    unittest.main()
