"""Host-only hold uses real snapshot workers and a changing HTTP source."""
from functools import partial
import importlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from tests.test_v8std_mcp_snapshots import Source, build, blocking_ipc_build
from tests import mcp_snapshot_fixtures as fixture
from runtime.v8std_mcp_snapshots import SnapshotStore, SnapshotCoordinator


def eventually(check, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(.025)
    raise AssertionError("observed condition timed out")


class HoldTests(unittest.TestCase):
    def test_same_hold_reacknowledges_after_transient_control_read_failure(self):
        for selected in (False, True):
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as directory:
                source = Source()
                store = SnapshotStore(source.url, Path(directory) / "cache")
                control = Path(directory) / "control.json"
                command = {"schema_version": 1, "token": "a" * 32, "mode": "hold", "manifest": source.manifest}
                control.write_text(json.dumps(command))
                coordinator = SnapshotCoordinator(store, build, release_control=control)
                coordinator._delay = lambda failures: .15  # Production backoff is not changed.
                coordinator.start()
                try:
                    eventually(lambda: coordinator.status()["hold_token"] == command["token"])
                    if not selected:
                        command.update(token="b" * 32, manifest=None)
                        control.write_text(json.dumps(command))
                        eventually(lambda: coordinator.status()["hold_token"] == command["token"])
                    old = coordinator.current()
                    control.unlink()  # Actual transient unreadable command, not a forged ack.
                    eventually(lambda: coordinator.status()["hold_token"] is None)
                    self.assertTrue(coordinator.status()["ready"])
                    control.write_text(json.dumps(command))
                    eventually(lambda: coordinator.status()["hold_token"] == command["token"], timeout=2)
                    self.assertEqual(coordinator.status()["release_control_token"], command["token"])
                    self.assertEqual(coordinator.current().corpus_id, old.corpus_id)
                finally:
                    coordinator.close()
                    source.close()

    def test_hold_selects_delivery_identity_even_when_corpus_is_equal(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Source()
            self.addCleanup(source.close)
            store = SnapshotStore(source.url, Path(directory) / "cache")
            first = store.refresh()
            control = Path(directory) / "control.json"
            command = {"schema_version": 1, "token": "a" * 32, "mode": "hold", "manifest": source.manifest}
            control.write_text(json.dumps(command))
            coordinator = SnapshotCoordinator(store, build, release_control=control)
            self.addCleanup(coordinator.close)
            coordinator.start()
            eventually(lambda: coordinator.status().get("hold_token") == "a" * 32)
            archive = bytearray(source.archive)
            archive[9] ^= 1
            source.archive = bytes(archive)
            source.manifest = fixture.manifest_for(source.archive, first.files)
            self.assertEqual(source.manifest["corpus_id"], first.metadata["corpus_id"])
            command.update(token="b" * 32, manifest=source.manifest)
            control.write_text(json.dumps(command))
            eventually(lambda: coordinator.status().get("hold_token") == "b" * 32)
            self.assertEqual(coordinator.status()["archive_sha256"], source.manifest["archive"]["sha256"])
            self.assertNotEqual(coordinator.status()["archive_sha256"], first.archive_sha256)

    def test_selected_hold_ignores_advancing_manifest_then_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Source()
            self.addCleanup(source.close)
            store = SnapshotStore(source.url, Path(directory) / "cache")
            selected = dict(source.manifest)
            store.refresh()
            source.next_generation()
            control = Path(directory) / "control.json"
            command = {"schema_version": 1, "token": "a" * 32,
                       "mode": "hold", "manifest": selected}
            control.write_text(json.dumps(command))
            coordinator = SnapshotCoordinator(store, build, refresh_seconds=1, release_control=control)
            self.addCleanup(coordinator.close)
            coordinator.start()
            state = eventually(lambda: coordinator.status() if coordinator.status().get("hold_token") else None)
            self.assertEqual(state["corpus_id"], selected["corpus_id"])
            self.assertEqual(state["archive_sha256"], selected["archive"]["sha256"])
            requests = len(source.requests)
            time.sleep(.3)
            self.assertEqual(len(source.requests), requests)
            command.update(token="b" * 32, mode="resume", manifest=None)
            control.write_text(json.dumps(command))
            eventually(lambda: coordinator.status()["corpus_id"] == source.manifest["corpus_id"])
            self.assertIsNone(coordinator.status()["hold_token"])

    def test_capture_after_worker_commit_failure_and_restart_selected_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Source()
            self.addCleanup(source.close)
            store = SnapshotStore(source.url, Path(directory) / "cache")
            first = dict(source.manifest)
            store.refresh()
            source.next_generation()
            second = dict(source.manifest)
            store._attempt_seconds = 1.2
            control = Path(directory) / "control.json"
            command = {"schema_version": 1, "token": "a" * 32, "mode": "resume", "manifest": None}
            control.write_text(json.dumps(command))
            coordinator = SnapshotCoordinator(store, partial(blocking_ipc_build, corpus_id=second["corpus_id"]),
                                              refresh_seconds=1, release_control=control)
            self.addCleanup(coordinator.close)
            coordinator.start()
            eventually(lambda: coordinator.status()["ready"])
            eventually(lambda: (store.namespace / "state.json").exists() and json.loads(
                (store.namespace / "state.json").read_text())["active"] == second["archive"]["sha256"])
            command.update(token="b" * 32, mode="hold")
            control.write_text(json.dumps(command))
            state = eventually(lambda: coordinator.status() if coordinator.status().get("hold_token") == "b" * 32 else None)
            self.assertEqual(state["corpus_id"], first["corpus_id"])
            self.assertEqual(state["archive_sha256"], first["archive"]["sha256"])
            coordinator.close()
            command.update(token="c" * 32, manifest=first)
            control.write_text(json.dumps(command))
            restarted = SnapshotCoordinator(store, build, release_control=control)
            self.addCleanup(restarted.close)
            restarted.start()
            eventually(lambda: restarted.status().get("hold_token") == "c" * 32)
            self.assertEqual(restarted.current().corpus_id, first["corpus_id"])


if __name__ == "__main__":
    unittest.main()
