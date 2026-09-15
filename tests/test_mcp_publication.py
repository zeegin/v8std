"""Publication behavior at the real helper/transport and Pages-file boundaries."""
import copy
import importlib
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import zipfile
import yaml

from tests import mcp_snapshot_fixtures as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("publish_mcp_artifacts"))
        self.p = importlib.import_module("publish_mcp_artifacts")
        self.temp = tempfile.TemporaryDirectory(prefix="v8std-publication-test-")
        self.addCleanup(self.temp.cleanup)
        self.pages = Path(self.temp.name) / "site/ai/mcp/v1/manifest.json"
        self.pages.parent.mkdir(parents=True)
        self.pages.write_bytes(b"previous Pages tree")
        self.archive, self.manifest = fixture.snapshot_fixture()
        self.manifest["archive"]["path"] = (
            "https://ai.v8std.ru/indexes/v1/" + self.manifest["archive"]["sha256"] + "/snapshot.tar.gz")
        self.context = dict(event="push", repository="zeegin/v8std", ref="refs/heads/main",
                            sha=fixture.SOURCE_SHA, main_sha=fixture.SOURCE_SHA,
                            run_id=123, run_number=8, attempt=1,
                            gates={"architecture": "success", "build": "success",
                                   "tests": "success", "benchmark": "success"})
        self.adapter = Transport(self.archive, self.manifest)

    def pipeline(self):
        return self.p.Publication(self.context, self.adapter)

    def test_publish_receipt_bytes_pages_reference_default_digest_then_promotion(self):
        publication = self.pipeline()
        prepared = publication.prepare(self.pages, self.manifest, self.archive, enabled=True)
        self.assertEqual(json.loads(self.pages.read_bytes()), self.manifest)
        self.assertEqual(self.adapter.effects, ["upload:publish", "status", "status", "archive"])
        # The deploy-pages action is the only caller that makes the staged tree public.
        self.adapter.public_manifest = self.pages.read_bytes()
        publication.finish(prepared, image="ghcr.io/zeegin/v8std-mcp@sha256:" + "a" * 64,
                           runtime_sha=fixture.SOURCE_SHA, promote=True)
        self.assertEqual(self.adapter.effects, ["upload:publish", "status", "status", "archive",
                                               "manifest", "archive", "upload:reference",
                                               "status", "status", "anonymous-smoke", "promote"])
        publish, reference = self.adapter.uploads
        self.assertNotEqual(publish[0]["publication_id"], reference[0]["publication_id"])
        self.assertGreater(reference[0]["sequence"], publish[0]["sequence"])
        self.assertEqual(publish[1], self.archive)
        self.assertEqual(reference[1], b"")

    def test_disallowed_main_pr_fork_tag_stale_malformed_and_failed_gates_have_no_effects(self):
        cases = [{"event": "pull_request"}, {"repository": "fork/v8std"},
                 {"ref": "refs/tags/v1"}, {"ref": "refs/heads/topic"},
                 {"main_sha": "2" * 40}, {"sha": "malformed"}, {"attempt": True},
                 {"event": "workflow_run"}, {"run_number": 0},
                 {"gates": {"build": "success"}}]
        for gate in self.context["gates"]:
            for outcome in ("failure", "cancelled", "skipped", "pending"):
                cases.append({"gates": {**self.context["gates"], gate: outcome}})
        for changes in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(self.p.PublicationError):
                    self.p.Publication({**self.context, **changes}, self.adapter).prepare(
                        self.pages, self.manifest, self.archive, enabled=True)
                self.assertEqual(self.adapter.effects, [])
                self.assertEqual(self.pages.read_bytes(), b"previous Pages tree")

    def test_dispatch_main_is_allowed_but_cannot_supply_an_alternative_ref(self):
        self.context["event"] = "workflow_dispatch"
        self.pipeline().prepare(self.pages, self.manifest, self.archive, enabled=True)
        self.assertEqual(json.loads(self.pages.read_bytes()), self.manifest)

    def test_exact_receipt_mismatch_failure_or_timeout_never_changes_pages(self):
        for field, value in [("state", "FAILED"), ("state", "RECOVERY_REQUIRED"),
                             ("state", "QUEUED"), ("sequence", 1), ("action", "reference"),
                             ("trigger_sha", "2" * 40), ("corpus_source_sha", "3" * 40),
                             ("corpus_id", "a" * 64), ("archive_sha256", "b" * 64),
                             ("publication_id", "another-run"), ("error_code", "cleanup_failed"),
                             ("cleanup_complete", False)]:
            with self.subTest(field=field, value=value):
                self.adapter = Transport(self.archive, self.manifest)
                self.adapter.receipt_override = {field: value}
                with self.assertRaises(self.p.PublicationError):
                    self.pipeline().prepare(self.pages, self.manifest, self.archive, enabled=True)
                self.assertEqual(self.pages.read_bytes(), b"previous Pages tree")
                self.assertNotIn("archive", self.adapter.effects)
                self.assertLessEqual(self.adapter.now, 301)

    def test_corrupt_local_archive_rejected_before_upload(self):
        with self.assertRaises(ValueError):
            self.pipeline().prepare(self.pages, self.manifest, b"corrupt", enabled=True)
        self.assertEqual(self.adapter.effects, [])

    def test_external_archive_failure_after_ack_never_changes_pages(self):
        self.adapter.archive = b"corrupt"
        with self.assertRaises(ValueError):
            self.pipeline().prepare(self.pages, self.manifest, self.archive, enabled=True)
        self.assertEqual(self.pages.read_bytes(), b"previous Pages tree")

    def test_disabled_publication_preserves_verified_manifest_without_host_effects(self):
        self.adapter.public_manifest = fixture.json_bytes(self.manifest)
        prepared = self.pipeline().prepare(self.pages, self.manifest, self.archive, enabled=False)
        self.assertEqual(json.loads(self.pages.read_bytes()), self.manifest)
        self.assertEqual(self.adapter.effects, ["manifest", "archive"])
        self.assertIsNone(prepared["header"])

    def test_only_initial_404_means_no_manifest_not_network_failure_or_later_absence(self):
        for failure, previously_published in [(OSError("network"), False),
                                              (FileNotFoundError(), True)]:
            with self.subTest(failure=failure, previous=previously_published):
                self.adapter.manifest_failure = failure
                with self.assertRaises((OSError, self.p.PublicationError)):
                    self.pipeline().prepare(self.pages, self.manifest, self.archive, enabled=False,
                                            previously_published=previously_published)
                self.assertEqual(self.pages.read_bytes(), b"previous Pages tree")
        self.adapter.manifest_failure = FileNotFoundError()
        self.pipeline().prepare(self.pages, self.manifest, self.archive, enabled=False)
        self.assertFalse(self.pages.exists())

    def test_reference_and_default_readiness_failure_prevent_stable_promotion(self):
        for failure in ("reference", "default"):
            with self.subTest(failure=failure):
                self.adapter = Transport(self.archive, self.manifest)
                publication = self.pipeline()
                prepared = publication.prepare(self.pages, self.manifest, self.archive, enabled=True)
                self.adapter.public_manifest = self.pages.read_bytes()
                if failure == "reference":
                    self.adapter.receipt_override = {"state": "FAILED"}
                else:
                    self.adapter.smoke_error = RuntimeError("default unavailable")
                with self.assertRaises((self.p.PublicationError, RuntimeError)):
                    publication.finish(prepared, image="ghcr.io/zeegin/v8std-mcp@sha256:" + "a" * 64,
                                       runtime_sha=fixture.SOURCE_SHA, promote=True)
                self.assertNotIn("promote", self.adapter.effects)

    def test_real_host_ingress_journals_and_separate_reference_receipt(self):
        import v8std_mcp_release as host
        root = Path(self.temp.name) / "controller"
        static = Path(self.temp.name) / "static"
        adapter = self.adapter
        verified = []
        publisher = host.Publisher(root, static,
            verifier=lambda archive, header, deadline: verified.append(header["action"]))
        # Only SSH delivery and attestation authority are substituted. Upload
        # framing/ingress, static publication, status and retention are real.
        def deliver(command, payload, *, seconds=30):
            with tempfile.TemporaryFile() as wire:
                wire.write(payload)
                wire.seek(0)
                if command == "publish-index":
                    initial = host.ingest(root, static, wire.fileno())
                    self.assertEqual(initial["state"], "QUEUED")
                    publisher.recover()
                    return initial
                query = host.read_status_query(wire.fileno())
                return host.query_status(root, None, query)
        def get(url, limit):
            if url == self.p.MANIFEST_URL:
                return adapter.public_manifest
            return (static / self.manifest["archive"]["sha256"] / "snapshot.tar.gz").read_bytes()
        adapter.command, adapter.get = deliver, get
        adapter.time = time.time
        publication = self.pipeline()
        prepared = publication.prepare(self.pages, self.manifest, self.archive, enabled=True)
        self.assertEqual(verified, ["publish"])
        self.assertFalse((root / "current-index.json").exists())
        adapter.public_manifest = self.pages.read_bytes()
        publication.finish(prepared)
        self.assertEqual(verified, ["publish", "reference"])
        current = host.read_record(root / "current-index.json")
        self.assertEqual(current["action"], "reference")
        self.assertEqual(current["manifest"], self.manifest)
        self.assertNotEqual(current["publication_id"], prepared["header"]["publication_id"])
        receipts = [host.read_record(path) for path in (root / "publications").glob("*.json")]
        self.assertEqual(len(receipts), 2)
        self.assertTrue(all(record["state"] == "COMMITTED" and not record["cleanup_pending"] for record in receipts))

    def test_actual_cli_prepare_then_finish_uses_same_verified_plan_and_separate_reference(self):
        directory = Path(self.temp.name) / ".ci"
        directory.mkdir()
        plan = {"trigger_sha": fixture.SOURCE_SHA, "corpus_sha": fixture.SOURCE_SHA,
                "runtime_sha": fixture.SOURCE_SHA, "runtime_changed": True, "corpus_changed": True,
                "identities": {"runtime": "b" * 64, "corpus": "c" * 64},
                "published": {"runtime": None, "corpus": None}}
        self.p.save(directory / "plan.json", plan)
        self.p.save(directory / "snapshot/manifest.json", self.manifest)
        archive = directory / "snapshot" / self.manifest["archive"]["sha256"] / "snapshot.tar.gz"
        archive.parent.mkdir(parents=True)
        archive.write_bytes(self.archive)
        local = copy.deepcopy(self.manifest)
        local["archive"]["path"] = self.manifest["archive"]["sha256"] + "/snapshot.tar.gz"
        self.p.save(directory / "local-site/ai/mcp/v1/manifest.json", local)
        local_archive = directory / "local-site/ai/mcp/v1" / local["archive"]["path"]
        local_archive.parent.mkdir(parents=True)
        local_archive.write_bytes(self.archive)
        environ = {"MCP_CORPUS_PUBLICATION_ENABLED": "true", "MCP_IMAGE_PUBLICATION_ENABLED": "false"}
        with patch.dict(os.environ, environ), patch.object(self.p, "fresh_context", return_value=self.context), \
                patch.object(self.p, "CITransport", return_value=self.adapter):
            self.assertEqual(self.p.main(["prepare-pages", "--directory", str(directory),
                                         "--root", self.temp.name]), 0)
            staged = Path(self.temp.name) / "site/ai/mcp/v1/manifest.json"
            self.assertEqual(json.loads(staged.read_bytes()), self.manifest)
            self.assertEqual(self.adapter.effects, ["upload:publish", "status", "status", "archive"])
            state = self.p.load(directory / "corpus-state/state.json")
            self.assertEqual(state["source_sha"], fixture.SOURCE_SHA)
            self.assertEqual(state["manifest"], self.manifest)
            self.adapter.public_manifest = staged.read_bytes()
            self.assertEqual(self.p.main(["finish", "--directory", str(directory),
                                         "--root", self.temp.name]), 0)
        self.assertEqual([header["action"] for header, _ in self.adapter.uploads], ["publish", "reference"])
        accepted = self.p.load(directory / "accepted.json")
        self.assertEqual(accepted["manifest"], self.manifest)
        self.assertIsNone(accepted["runtime"])
        self.assertEqual(accepted["trigger_sha"], fixture.SOURCE_SHA)
        self.assertNotIn("promote", self.adapter.effects)

    def test_actual_image_cli_connects_digest_outputs_to_verified_milestone(self):
        directory = Path(self.temp.name) / ".ci"
        plan = {"trigger_sha": fixture.SOURCE_SHA, "runtime_sha": fixture.SOURCE_SHA,
                "runtime_changed": True, "identities": {"runtime": "d" * 64},
                "published": {"runtime": None}}
        self.p.save(directory / "plan.json", plan)
        output = Path(self.temp.name) / "github-output"
        environ = {"MCP_IMAGE_PUBLICATION_ENABLED": "true", "GITHUB_OUTPUT": str(output),
                   "MCP_BUILT_DIGEST": "sha256:" + "a" * 64, "MCP_SITE_BUILT_DIGEST": "sha256:" + "b" * 64}
        with patch.dict(os.environ, environ, clear=True), \
                patch.object(self.p, "fresh_context", return_value=self.context), \
                patch.object(self.p, "registry_manifest", return_value=None), \
                patch.object(self.p, "bounded_command"), \
                patch.object(self.p, "verify_build", return_value=(self.manifest, self.archive)), \
                patch.object(self.p.CITransport, "local_smoke") as smoke, \
                patch.object(self.p.CITransport, "tag") as tag:
            self.assertEqual(self.p.main(["image-plan", "--directory", str(directory)]), 0)
            self.assertEqual(output.read_text(), "build=true\nsite_build=true\n")
            self.assertEqual(self.p.main(["record-image", "--directory", str(directory)]), 0)
            self.assertEqual(smoke.call_count, 1)
            self.assertEqual(tag.call_count, 2)
        state = self.p.load(directory / "runtime-state/state.json")
        self.assertEqual(state["source_sha"], fixture.SOURCE_SHA)
        self.assertEqual(state["input_id"], "d" * 64)
        self.assertEqual(state["image_digest"], "sha256:" + "a" * 64)


class Transport:
    """Controlled external boundary; all verification and sequencing are production code."""
    def __init__(self, archive, manifest):
        self.archive, self.manifest = archive, manifest
        self.public_manifest = None
        self.manifest_failure = None
        self.receipt_override = {}
        self.effects, self.uploads = [], []
        self.now = 0
        self.smoke_error = None

    def monotonic(self):
        return self.now

    def time(self):
        return 1_800_000_000 + self.now

    def sleep(self, seconds):
        self.now += seconds

    def command(self, command, payload, *, seconds=30):
        if command == "publish-index":
            line, archive = payload.split(b"\n", 1)
            header = json.loads(line)
            self.effects.append("upload:" + header["action"])
            self.uploads.append((header, archive))
            self.polls = 0
            return {"publication_id": header["publication_id"], "state": "QUEUED"}
        assert command == "status"
        self.effects.append("status")
        header = self.uploads[-1][0]
        assert json.loads(payload) == {"schema_version": 1, "kind": "publication", "id": header["publication_id"]}
        self.polls += 1
        manifest = header["manifest"]
        return {"publication_id": header["publication_id"], "sequence": header["sequence"],
                "action": header["action"], "trigger_sha": header["trigger_sha"],
                "corpus_source_sha": manifest["source_sha"], "corpus_id": manifest["corpus_id"],
                "archive_sha256": manifest["archive"]["sha256"],
                "state": "COMMITTED" if self.polls > 1 else "RECEIVED", "error_code": None,
                "cleanup_complete": self.polls > 1, **self.receipt_override}

    def get(self, url, limit):
        if url == "https://v8std.ru/ai/mcp/v1/manifest.json":
            self.effects.append("manifest")
            if self.manifest_failure:
                raise self.manifest_failure
            return self.public_manifest
        assert url == self.manifest["archive"]["path"]
        self.effects.append("archive")
        return self.archive

    def smoke(self, image, runtime_sha, manifest):
        self.effects.append("anonymous-smoke")
        if self.smoke_error:
            raise self.smoke_error

    def promote(self, image):
        self.effects.append("promote")


class InputIdentityTests(unittest.TestCase):
    def setUp(self):
        self.p = importlib.import_module("publish_mcp_artifacts")
        self.temp = tempfile.TemporaryDirectory(prefix="v8std-input-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Input Test")
        self.git("config", "user.email", "input@example.invalid")
        files = {"Dockerfile.mcp": "FROM pinned\nCOPY requirements-mcp.lock ./\nCOPY scripts/server.py scripts/imported.py ./scripts/\n",
                 ".dockerignore": "**\n!scripts/\n", "requirements-mcp.lock": "runtime==1",
                 ".github/workflows/ci.yml": "pinned tools\n",
                 "scripts/server.py": "import imported\n", "scripts/imported.py": "VALUE = 1\n",
                 "scripts/v8std_mcp_release.py": "host only", "docs/article.md": "article",
                 "scripts/generate_ai_artifacts.py": "from generator_dep import VALUE\n",
                 "scripts/generator_dep.py": "VALUE = 1\n",
                 "scripts/generate_search_vectors.py": "", "scripts/generate_mcp_snapshot.py": "",
                 "scripts/zensical_docs.sh": '"${PYTHON_BIN}" "${SCRIPT_DIR}/publish_license_texts.py"\n',
                 "scripts/publish_license_texts.py": "# producer\n", "scripts/build_local_site.py": "# local profile\n",
                 "scripts/zensical-version.sh": "",
                 "Dockerfile.ci": "FROM compression-pinned", "deploy/ci/fonts.sha256": "font",
                 "requirements-build.lock": "builder==1", "zensical.toml": "config",
                 "retrieval-rules.yml": "rules", "LICENSE": "license", "LICENSES/a.txt": "attribution"}
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True,
                              text=True, timeout=10).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def test_pending_runtime_survives_failed_release_then_docs_only_successor(self):
        base = self.p.input_identities(self.root, self.base)
        (self.root / "scripts/imported.py").write_text("VALUE = 2\n")
        failed = self.commit()
        (self.root / "docs/article.md").write_text("new article")
        successor = self.commit()
        current = self.p.input_identities(self.root, successor)
        self.assertNotEqual(base["runtime"], current["runtime"])
        self.assertNotEqual(base["corpus"], current["corpus"])
        state = {"runtime": {"input_id": base["runtime"], "source_sha": self.base},
                 "corpus": {"input_id": base["corpus"], "source_sha": self.base}}
        decision = self.p.choose_sources(successor, current, state)
        self.assertEqual(decision, {"runtime_sha": successor, "corpus_sha": successor,
                                    "runtime_changed": True, "corpus_changed": True})
        self.assertNotEqual(failed, successor)

    def test_runtime_only_and_host_only_reuse_corpus_source_and_rerun_is_stable(self):
        base = self.p.input_identities(self.root, self.base)
        (self.root / "scripts/server.py").write_text("import imported\n# runtime edit\n")
        runtime_sha = self.commit()
        current = self.p.input_identities(self.root, runtime_sha)
        self.assertEqual(base["corpus"], current["corpus"])
        state = {"runtime": {"input_id": current["runtime"], "source_sha": runtime_sha},
                 "corpus": {"input_id": base["corpus"], "source_sha": self.base}}
        (self.root / "scripts/v8std_mcp_release.py").write_text("host change, not an image input")
        successor = self.commit()
        decision = self.p.choose_sources(successor, self.p.input_identities(self.root, successor), state)
        self.assertEqual(decision, {"runtime_sha": runtime_sha, "corpus_sha": self.base,
                                    "runtime_changed": False, "corpus_changed": False})
        self.assertEqual(self.p.choose_sources(successor, current, state), decision)

    def test_corpus_generator_import_closure_and_builder_change_are_content_inputs(self):
        base = self.p.input_identities(self.root, self.base)
        for name in ("scripts/generator_dep.py", "deploy/ci/fonts.sha256", "Dockerfile.ci"):
            with self.subTest(name=name):
                with (self.root / name).open("a") as stream:
                    stream.write("\n# changed\n")
                changed = self.p.input_identities(self.root, self.commit())
                self.assertNotEqual(changed["corpus"], base["corpus"])
                self.assertEqual(changed["runtime"], base["runtime"])
                base = changed

    def test_wrapper_invoked_producer_and_local_profile_are_in_source_closure(self):
        base = self.p.input_identities(self.root, self.base)
        for name in ("scripts/publish_license_texts.py", "scripts/build_local_site.py"):
            with self.subTest(name=name):
                with (self.root / name).open("a") as stream:
                    stream.write("# changed\n")
                changed = self.p.input_identities(self.root, self.commit())
                self.assertNotEqual(changed["corpus"], base["corpus"])
                self.assertEqual(changed["runtime"], base["runtime"])
                base = changed

    def test_missing_runtime_copy_input_fails_closed(self):
        (self.root / "scripts/imported.py").unlink()
        with self.assertRaises(self.p.PublicationError):
            self.p.input_identities(self.root, self.commit())

    def test_build_toolchain_pins_affect_both_artifact_input_identities(self):
        before = self.p.input_identities(self.root, self.base)
        (self.root / ".github/workflows/ci.yml").write_text("updated pinned buildx and emulation\n")
        after = self.p.input_identities(self.root, self.commit())
        self.assertNotEqual(before["runtime"], after["runtime"])
        self.assertNotEqual(before["corpus"], after["corpus"])

    def test_pending_corpus_survives_failed_publication_and_runtime_only_successor(self):
        base = self.p.input_identities(self.root, self.base)
        (self.root / "docs/article.md").write_text("not yet published")
        self.commit()
        (self.root / "scripts/server.py").write_text("# new runtime")
        successor = self.commit()
        state = {"runtime": {"input_id": base["runtime"], "source_sha": self.base},
                 "corpus": {"input_id": base["corpus"], "source_sha": self.base}}
        decision = self.p.choose_sources(successor, self.p.input_identities(self.root, successor), state)
        self.assertTrue(decision["runtime_changed"])
        self.assertTrue(decision["corpus_changed"])

    def test_independent_success_record_survives_overall_failed_run_and_rejects_forged_state(self):
        identities = self.p.input_identities(self.root, self.base)
        state = {"schema_version": 1, "kind": "runtime", "sequence": 4001,
                 "trigger_sha": self.base, "source_sha": self.base, "input_id": identities["runtime"],
                 "image_digest": "sha256:" + "a" * 64}
        artifact = {"id": 80, "name": "mcp-runtime-state-v1-1", "expired": False, "workflow_run": {"id": 70, "head_branch": "main",
                    "head_sha": self.base, "repository_id": 1, "head_repository_id": 1}}
        run = {"id": 70, "head_sha": self.base, "head_branch": "main", "event": "push",
               "path": ".github/workflows/ci.yml", "run_number": 4, "run_attempt": 1,
               "repository": {"full_name": "zeegin/v8std"}, "head_repository": {"full_name": "zeegin/v8std"},
               "status": "completed", "conclusion": "failure"}
        def api(path):
            if "/artifacts?" in path:
                names = parse_qs(urlsplit(path).query).get("name", [artifact["name"]])
                found = [artifact] if artifact["name"] in names else []
                return {"total_count": len(found), "artifacts": found}
            if path.endswith("/runs/70/attempts/1"):
                return run
            if path.endswith("/runs/70"):
                # A later failed rerun must not rewrite the successful first
                # attempt's artifact identity. Use the exact attempt endpoint.
                return {**run, "run_attempt": 2}
            raise AssertionError(path)
        def download(path):
            self.assertTrue(path.endswith("/artifacts/80/zip"))
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w") as archive:
                archive.writestr("state.json", fixture.json_bytes(state))
            return output.getvalue()
        found = self.p.last_published(self.root, self.base, 5001, "runtime", api, download)
        self.assertEqual(found, state)
        # The later runtime job sees this attempt's own milestone while the
        # overall run is still in progress. It is not previous history.
        run["status"] = "in_progress"
        self.assertIsNone(self.p.last_published(self.root, self.base, 4001, "runtime", api, download))
        run["status"] = "completed"
        for change in ({"input_id": "b" * 64}, {"trigger_sha": "c" * 40}, {"image_digest": "latest"}):
            original = dict(state)
            state.update(change)
            with self.subTest(change=change), self.assertRaises(self.p.PublicationError):
                self.p.last_published(self.root, self.base, 5001, "runtime", api, download)
            state.clear()
            state.update(original)
        with self.assertRaises(self.p.PublicationError):
            self.p.last_published(self.root, self.base, 3001, "runtime", api, download)
        artifact["expired"] = True
        with self.assertRaises(self.p.PublicationError):
            self.p.last_published(self.root, self.base, 5001, "runtime", api, download)

    def test_actual_pr_cli_builds_source_plan_without_credentials_or_network(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/publish_mcp_artifacts.py"), "plan",
                                 "--root", str(self.root), "--directory", str(self.root / ".ci")],
                                env={**os.environ, "GITHUB_EVENT_NAME": "pull_request", "GITHUB_SHA": self.base,
                                     "GITHUB_REPOSITORY": "zeegin/v8std", "GITHUB_REF": "refs/pull/1/merge",
                                     "GITHUB_RUN_ID": "50", "GITHUB_RUN_NUMBER": "5", "GITHUB_RUN_ATTEMPT": "1",
                                     "GH_TOKEN": "", "GITHUB_TOKEN": ""},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root / ".ci/plan.json"
        self.assertTrue(path.is_file(), "actual helper CLI must write its source plan, not exit as a no-op")
        plan = json.loads(path.read_bytes())
        self.assertEqual(plan["corpus_sha"], self.base)
        self.assertEqual(plan["runtime_sha"], self.base)
        self.assertEqual(plan["published"], {"runtime": None, "corpus": None})

    def test_missing_ci_history_reuses_attested_content_identity_after_docs_only_edit(self):
        before = self.p.input_identities(self.root, self.base)
        (self.root / "docs/article.md").write_text("docs-only successor after artifact deletion")
        current = self.commit()
        identities = self.p.input_identities(self.root, current)
        raw = fixture.json_bytes({"schemaVersion": 2, "manifests": []})
        with patch.object(self.p, "registry_tags", return_value=["sha-" + self.base]), \
                patch.object(self.p, "registry_manifest", return_value=raw), \
                patch.object(self.p, "bounded_command") as attest:
            recovered = self.p.equivalent_runtime(self.root, current, identities["runtime"])
        self.assertEqual(recovered["source_sha"], self.base)
        self.assertEqual(recovered["input_id"], before["runtime"])
        self.assertEqual(recovered["image_digest"], "sha256:" + fixture.sha256(raw))
        self.assertIn(self.base, attest.call_args.args[0])
        selected = self.p.choose_sources(current, identities, {"runtime": recovered, "corpus": None})
        self.assertFalse(selected["runtime_changed"])
        self.assertEqual(selected["runtime_sha"], self.base)
        with patch.object(self.p, "registry_tags", return_value=["sha-" + self.base]), \
                patch.object(self.p, "registry_manifest") as registry:
            self.assertIsNone(self.p.equivalent_runtime(self.root, current, "0" * 64))
            registry.assert_not_called()

    def test_expired_corpus_history_never_turns_later_404_into_initial_absence(self):
        environ = {"GITHUB_EVENT_NAME": "push", "GITHUB_SHA": self.base, "GITHUB_REPOSITORY": "zeegin/v8std",
                   "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ID": "50", "GITHUB_RUN_NUMBER": "5",
                   "GITHUB_RUN_ATTEMPT": "1", "GITHUB_WORKFLOW_REF": "zeegin/v8std/.github/workflows/ci.yml@refs/heads/main"}
        with patch.object(self.p, "api", return_value={"commit": {"sha": self.base}}), \
                patch.object(self.p, "last_published", side_effect=self.p.PublicationError("published_state_expired")), \
                patch.object(self.p.CITransport, "get", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(self.p.PublicationError, "published_manifest_missing"):
                self.p.plan_sources(self.root, environ)


class TransportBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.p = importlib.import_module("publish_mcp_artifacts")

    def test_command_has_real_wall_clock_and_output_bounds(self):
        start = time.monotonic()
        with self.assertRaises(self.p.PublicationError):
            self.p.bounded_command([sys.executable, "-c", "import time; time.sleep(10)"], seconds=.15)
        self.assertLess(time.monotonic() - start, 3)
        with self.assertRaises(self.p.PublicationError):
            self.p.bounded_command([sys.executable, "-c", "print('x'*10000)"], limit=100)
        self.assertEqual(self.p.bounded_command([sys.executable, "-c", "print('ok')"]), b"ok\n")

    def test_ssh_uses_only_typed_forced_commands_pinned_host_key_and_exact_stdin(self):
        transport = self.p.CITransport(release_host="v8std-release@ai.v8std.ru", key="/tmp/key",
                                       known_hosts="/tmp/known-hosts")
        with patch.object(self.p, "bounded_command", return_value=b'{"state":"QUEUED"}') as command:
            payload = b'{"header":"exact"}\narchive'
            transport.command("publish-index", payload)
            argv = command.call_args.args[0]
            self.assertEqual(argv[-2:], ["v8std-release@ai.v8std.ru", "publish-index"])
            self.assertIn("StrictHostKeyChecking=yes", argv)
            self.assertIn("UserKnownHostsFile=/tmp/known-hosts", argv)
            self.assertIn("IdentitiesOnly=yes", argv)
            self.assertEqual(command.call_args.kwargs["payload"], payload)
            command.reset_mock()
            for name in ("bootstrap", "bash", "deploy --anything", "rm"):
                with self.assertRaises(self.p.PublicationError):
                    transport.command(name, b"{}\n")
            command.assert_not_called()

    def test_state_artifact_zip_requires_exact_bounded_regular_state_member(self):
        def archive(name, payload):
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipped:
                zipped.writestr(name, payload)
            return output.getvalue()
        self.assertEqual(self.p.read_state_artifact(archive("state.json", b'{"kind":"runtime"}')), {"kind": "runtime"})
        for name, payload in [("../state.json", b"{}"), ("state.json", b"x" * (128 * 1024 + 1))]:
            with self.subTest(name=name), self.assertRaises(self.p.PublicationError):
                self.p.read_state_artifact(archive(name, payload))

    def test_protection_name_or_protected_branches_selector_is_not_activation(self):
        branch = {"protected": True}
        environment = {"deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}}
        policies = {"branch_policies": [{"type": "branch", "name": "main"}]}
        self.p.check_external_protection(branch, environment, policies)
        for b, e, p in [({"protected": False}, environment, policies),
                        (branch, {"name": "mcp-production"}, policies),
                        (branch, {"deployment_branch_policy": {"protected_branches": True,
                                                               "custom_branch_policies": False}}, policies),
                        (branch, environment, {"branch_policies": [{"type": "tag", "name": "main"}]}),
                        (branch, environment, {"branch_policies": [{"type": "branch", "name": "*"}]})]:
            with self.subTest(branch=b, environment=e, policies=p), self.assertRaises(self.p.PublicationError):
                self.p.check_external_protection(b, e, p)

    def test_registry_absence_is_only_404_not_auth_or_network_failure(self):
        for status in (401, 403, 500):
            with self.subTest(status=status), patch.object(self.p, "registry_request", return_value=(status, b"{}")):
                with self.assertRaises(self.p.PublicationError):
                    self.p.registry_manifest(self.p.IMAGE, "sha-" + "a" * 40)
        with patch.object(self.p, "registry_request", return_value=(404, b"{}")):
            self.assertIsNone(self.p.registry_manifest(self.p.IMAGE, "sha-" + "a" * 40))
        raw = fixture.json_bytes({"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json",
                                  "manifests": []})
        with patch.object(self.p, "registry_request", return_value=(200, raw)):
            self.assertEqual(self.p.registry_manifest(self.p.IMAGE, "sha-" + "a" * 40), raw)

    def test_bootstrap_success_never_enables_runtime_and_unchanged_active_image_does_not_restart(self):
        transport = Transport(*fixture.snapshot_fixture())
        accepted = {"runtime": {"image_digest": "sha256:" + "a" * 64, "source_sha": "b" * 40},
                    "manifest": fixture.snapshot_fixture()[1]}
        accepted["manifest"]["archive"]["path"] = "https://ai.v8std.ru/indexes/v1/" + accepted["manifest"]["archive"]["path"]
        context = dict(event="push", repository="zeegin/v8std", ref="refs/heads/main",
                       sha="c" * 40, main_sha="c" * 40, run_id=1, run_number=2, attempt=1,
                       gates={name: "success" for name in self.p.GATES})
        with patch.object(transport, "command") as command:
            self.p.deploy_runtime(context, transport, accepted, enabled=False, configuration_digest="d" * 64,
                                  platform="linux/amd64")
            command.assert_not_called()
            command.return_value = {"state": "COMMITTED", "image_digest": "sha256:" + "a" * 64,
                                    "runtime_source_sha": "b" * 40, "configuration_digest": "d" * 64,
                                    "cleanup_complete": True, "error_code": None}
            with patch.object(self.p, "verify_running_runtime") as live:
                self.p.deploy_runtime(context, transport, accepted, enabled=True, configuration_digest="d" * 64,
                                      platform="linux/amd64")
                live.assert_called_once_with("b" * 40)
            self.assertEqual(command.call_count, 1)
            self.assertEqual(command.call_args.args, ("status", b""))

    def test_immutable_image_selection_reuses_original_sha_and_never_rebuilds_existing_tag(self):
        previous = {"source_sha": "a" * 40, "image_digest": "sha256:" + "b" * 64}
        plan = {"runtime_sha": "a" * 40, "runtime_changed": False, "published": {"runtime": previous}}
        with patch.object(self.p, "registry_manifest") as registry:
            selected = self.p.select_image(plan)
            self.assertEqual(selected, {"build": False, "source_sha": "a" * 40,
                                        "image_digest": "sha256:" + "b" * 64})
            registry.assert_not_called()
        plan.update(runtime_changed=True, runtime_sha="c" * 40)
        raw = b'{"schemaVersion":2,"manifests":[]}'
        with patch.object(self.p, "registry_manifest", return_value=raw), \
                patch.object(self.p, "bounded_command") as attest:
            selected = self.p.select_image(plan)
            self.assertFalse(selected["build"])
            self.assertEqual(selected["source_sha"], "c" * 40)
            self.assertEqual(selected["image_digest"], "sha256:" + fixture.sha256(raw))
            self.assertIn("c" * 40, attest.call_args.args[0])
        with patch.object(self.p, "registry_manifest", return_value=None):
            self.assertTrue(self.p.select_image(plan)["build"])

    def test_image_pair_is_verified_before_any_immutable_tag_or_state_write(self):
        context = dict(event="push", repository="zeegin/v8std", ref="refs/heads/main",
                       sha="c" * 40, main_sha="c" * 40, run_id=1, run_number=2, attempt=1,
                       gates={name: "success" for name in self.p.GATES})
        runtime = {"build": True, "source_sha": "c" * 40, "image_digest": None}
        site = {"build": True, "source_sha": "c" * 40, "image_digest": None}
        effects = []
        class Adapter:
            def local_smoke(self, *args):
                effects.append("smoke")
                if fail:
                    raise self_error("local smoke failed")
            def tag(self, image, source):
                effects.append("tag:" + image.split("@", 1)[0])
        self_error = self.p.PublicationError
        _, manifest = fixture.snapshot_fixture()
        for fail in (True, False):
            effects.clear()
            with patch.object(self.p, "bounded_command", side_effect=lambda *a, **k: effects.append("attest")):
                call = lambda: self.p.record_images(context, Adapter(), runtime, site, manifest,
                    runtime_digest="sha256:" + "a" * 64, site_digest="sha256:" + "b" * 64)
                if fail:
                    with self.assertRaises(self_error):
                        call()
                    self.assertEqual(effects, ["attest", "attest", "smoke"])
                else:
                    result = call()
                    self.assertEqual(result["source_sha"], "c" * 40)
                    self.assertEqual(result["image_digest"], "sha256:" + "a" * 64)
                    self.assertEqual(effects, ["attest", "attest", "smoke", "tag:ghcr.io/zeegin/v8std-mcp",
                                               "tag:ghcr.io/zeegin/v8std-site"])

    def test_anonymous_default_fixture_cleans_up_after_client_timeout_and_preserves_primary_failure(self):
        calls = []
        names = []
        def command(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[:2] == ["docker", "run"]:
                names.append(argv[argv.index("--name") + 1])
                raise self.p.PublicationError("command_timeout")
            if argv[:3] == ["docker", "container", "ls"]:
                return (names[-1] + "\n").encode()
            if argv[:2] == ["docker", "inspect"]:
                return json.dumps([{"Config": {"Labels": {"pro.v8std.ci": names[-1]}}}]).encode()
            if argv[:2] == ["docker", "rm"]:
                raise self.p.PublicationError("cleanup_denied")
            return b"{}"
        with patch.dict(os.environ, {"DOCKER_AUTH_CONFIG": "synthetic", "DOCKER_CONTEXT": "synthetic-remote",
                                     "REGISTRY_AUTH_FILE": "/synthetic/auth"}, clear=True), \
                patch.object(self.p, "bounded_command", side_effect=command):
            with self.assertRaisesRegex(self.p.PublicationError, "command_timeout") as raised:
                self.p.CITransport().smoke(self.p.IMAGE + "@sha256:" + "a" * 64, "b" * 40, {})
        self.assertIn("cleanup_denied", " ".join(raised.exception.__notes__))
        docker = [(argv, kw) for argv, kw in calls if argv[0] == "docker"]
        self.assertIn(["docker", "rm", "--force", names[0]], [argv for argv, _ in docker])
        for _, kwargs in docker:
            for name in ("DOCKER_AUTH_CONFIG", "DOCKER_CONTEXT", "REGISTRY_AUTH_FILE"):
                self.assertFalse(name in kwargs["env"], "anonymous environment retains key: " + name)
            self.assertFalse(Path(kwargs["env"]["DOCKER_CONFIG"]).exists())

    def test_release_exact_queue_identity_capacity_failure_and_malformed_platform_fail_closed(self):
        context = dict(event="push", repository="zeegin/v8std", ref="refs/heads/main",
                       sha="c" * 40, main_sha="c" * 40, run_id=1, run_number=2, attempt=1,
                       gates={name: "success" for name in self.p.GATES})
        archive, manifest = fixture.snapshot_fixture()
        manifest["archive"]["path"] = "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["path"]
        accepted = {"runtime": {"source_sha": "b" * 40, "image_digest": "sha256:" + "a" * 64}, "manifest": manifest}
        for failure in ("queue_identity", "capacity", "platform"):
            with self.subTest(failure=failure):
                adapter = Transport(archive, manifest)
                calls = []
                def command(name, payload, **kwargs):
                    calls.append(name)
                    if not payload:
                        return {"state": "COMMITTED", "cleanup_complete": True, "image_digest": "sha256:" + "f" * 64}
                    data = json.loads(payload)
                    if name == "validate-envelope":
                        return data
                    if name == "deploy":
                        adapter.envelope = data
                        return {"state": "QUEUED", "release_id": "wrong" if failure == "queue_identity" else data["release_id"]}
                    return {**adapter.envelope, "state": "FAILED", "error_code": "overlap_capacity", "cleanup_complete": True}
                adapter.command = command
                index = {"manifests": [{"digest": "sha256:" + "e" * 64,
                                       "platform": {} if failure == "platform" else {"os": "linux", "architecture": "amd64"}}]}
                with patch.object(self.p, "registry_manifest", return_value=fixture.json_bytes(index)), \
                        patch.object(self.p, "verify_running_runtime") as live:
                    with self.assertRaises(self.p.PublicationError):
                        self.p.deploy_runtime(context, adapter, accepted, enabled=True,
                                              configuration_digest="d" * 64, platform="linux/amd64")
                    live.assert_not_called()
                if failure == "queue_identity":
                    self.assertEqual(calls, ["status", "validate-envelope", "deploy"])
                if failure == "platform":
                    self.assertEqual(calls, ["status"])

    def test_immutable_tag_never_overwrites_conflict_and_rechecks_main_before_write(self):
        digest = "sha256:" + "a" * 64
        image = self.p.IMAGE + "@" + digest
        with patch.object(self.p, "registry_manifest", return_value=b"different digest"), \
                patch.object(self.p, "bounded_command") as command:
            with self.assertRaisesRegex(self.p.PublicationError, "immutable_tag_conflict"):
                self.p.CITransport().tag(image, "b" * 40)
            command.assert_not_called()

    def test_external_archive_head_must_itself_be_successful_not_just_match_length(self):
        archive, manifest = fixture.snapshot_fixture()
        url = "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["path"]
        def command(argv, **kwargs):
            status = b"500 Internal Server Error" if "--head" in argv else b"200 OK"
            headers = (b"HTTP/2 " + status + b"\r\nContent-Length: " + str(len(archive)).encode()
                       + b"\r\nContent-Type: application/gzip\r\nETag: fixture\r\nCache-Control: public, immutable\r\n\r\n")
            Path(argv[argv.index("--dump-header") + 1]).write_bytes(headers)
            return headers if "--head" in argv else archive
        with patch.object(self.p, "bounded_command", side_effect=command):
            with self.assertRaisesRegex(self.p.PublicationError, "http_status"):
                self.p.CITransport().get(url, self.p.MAX_ARCHIVE_BYTES)

    def test_stale_main_stops_immutable_tag_before_write(self):
        image = self.p.IMAGE + "@sha256:" + "a" * 64
        with patch.object(self.p, "registry_manifest", return_value=None), \
                patch.object(self.p, "fresh_context", side_effect=self.p.PublicationError("stale_or_invalid_sha")), \
                patch.object(self.p, "bounded_command") as command:
            with self.assertRaisesRegex(self.p.PublicationError, "stale_or_invalid_sha"):
                self.p.CITransport().tag(image, "b" * 40)
            command.assert_not_called()

    def test_initial_manifest_404_does_not_download_an_unbounded_html_error_page(self):
        methods = []
        def command(argv, **kwargs):
            methods.append("HEAD" if "--head" in argv else "GET")
            header = b"HTTP/2 404 Not Found\r\nContent-Length: 1000000\r\n\r\n"
            Path(argv[argv.index("--dump-header") + 1]).write_bytes(header)
            if "--head" not in argv:
                raise self.p.PublicationError("command_failed")
            return header
        with patch.object(self.p, "bounded_command", side_effect=command):
            with self.assertRaises(FileNotFoundError):
                self.p.CITransport().get(self.p.MANIFEST_URL, self.p.MAX_MANIFEST_BYTES)
        self.assertEqual(methods, ["HEAD"])


class WorkflowTests(unittest.TestCase):
    def workflow(self):
        return yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)

    def test_pinned_fail_closed_dag_has_secretless_pr_and_independent_activation(self):
        workflow = self.workflow()
        self.assertIn("pull_request", workflow["on"])
        self.assertNotIn("pull_request_target", workflow["on"])
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(workflow["concurrency"]["cancel-in-progress"], "false")
        jobs = workflow["jobs"]
        self.assertEqual(set(jobs), {"validate", "publish", "runtime"})
        self.assertEqual(jobs["publish"]["needs"], "validate")
        self.assertEqual(jobs["runtime"]["needs"], ["validate", "publish"])
        self.assertNotIn("secrets.", json.dumps(jobs["validate"]))
        for name in ("publish", "runtime"):
            condition = jobs[name]["if"]
            self.assertIn("github.repository == 'zeegin/v8std'", condition)
            self.assertIn("github.ref == 'refs/heads/main'", condition)
            self.assertIn("needs.validate.result == 'success'", condition)
            self.assertIn("github.event_name == 'push'", condition)
            self.assertIn("github.event_name == 'workflow_dispatch'", condition)
        self.assertIn("vars.MCP_RUNTIME_DEPLOY_ENABLED == 'true'", jobs["runtime"]["if"])
        self.assertNotIn("MCP_RUNTIME_DEPLOY_ENABLED", jobs["publish"]["if"])
        for job in jobs.values():
            self.assertIn("timeout-minutes", job)
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], r"^[\w/-]+@[0-9a-f]{40}$")
                if step.get("uses", "").startswith("actions/checkout@"):
                    self.assertEqual(step["with"]["persist-credentials"], "false")
        publication = json.dumps(jobs["publish"])
        self.assertIn("MCP_IMAGE_PUBLICATION_ENABLED", publication)
        self.assertIn("MCP_CORPUS_PUBLICATION_ENABLED", publication)
        self.assertIn("publish_mcp_artifacts.py", publication)
        self.assertIn("type=sbom,generator=", publication)
        self.assertIn("moby/buildkit@sha256:", publication)
        self.assertIn("tonistiigi/binfmt@sha256:", publication)

    def test_workflow_actual_actionlint(self):
        result = subprocess.run(["actionlint", "-color", ".github/workflows/ci.yml"], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
