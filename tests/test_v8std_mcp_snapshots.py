"""Loader conformance using real HTTP, independent archives and spawned builders."""

from dataclasses import dataclass
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import importlib.util
import io
import errno
import fcntl
import json
import multiprocessing
import os
import random
from pathlib import Path
import socket
import signal
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tests import mcp_snapshot_fixtures as fixture

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@dataclass(frozen=True)
class Generation:
    corpus_id: str
    pid: int
    start_method: str


def build(snapshot):
    return Generation(snapshot.metadata["corpus_id"], os.getpid(),
                      multiprocessing.get_start_method())


def fail_build(snapshot):
    raise RuntimeError("https://secret:password@example.invalid/private-corpus")


def blocking_build(snapshot):
    time.sleep(120)
    return build(snapshot)


def ignores_termination_build(snapshot):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    return blocking_build(snapshot)


def unpickleable_build(snapshot):
    return threading.RLock()


def large_build(snapshot):
    return (build(snapshot), b"x" * (8 * 1024 * 1024))


def blocking_ipc_build(snapshot, *, corpus_id):
    if snapshot.metadata["corpus_id"] == corpus_id:
        original = socket.socket.sendall

        def sendall(channel, payload, *args):
            if len(payload) > 8:
                original(channel, payload[:8], *args)
                time.sleep(120)
            else:
                original(channel, payload, *args)

        socket.socket.sendall = sendall
    return build(snapshot)


@dataclass
class CleanupFault:
    namespace: Path

    def __call__(self, snapshot):
        original = Path.iterdir
        active = snapshot.archive_sha256
        namespace = self.namespace

        def iterdir(path):
            if path == namespace and json.loads((path / "state.json").read_bytes())["active"] == active:
                raise OSError(errno.EACCES, "injected postcommit cleanup failure")
            return original(path)

        Path.iterdir = iterdir
        return build(snapshot)


class RecordingStop:
    """Replace the actual scheduling wait, not refresh/store behavior."""

    def __init__(self, count):
        self.event = threading.Event()
        self.delays = []
        self.count = count

    def is_set(self):
        return self.event.is_set()

    def set(self):
        self.event.set()

    def wait(self, timeout):
        self.delays.append(timeout)
        if len(self.delays) >= self.count:
            self.set()
        return self.is_set()


class SlowRetirement:
    def __init__(self, started, release):
        self.started = started
        self.release = release

    def __del__(self):
        self.started.set()
        self.release.wait(3)


@dataclass
class CommitFault:
    number: int
    crash: bool = False

    def __call__(self, snapshot):
        # Inject at the actual OS fsync boundary, after successful preparation.
        original = os.fsync
        calls = 0

        def fsync(fd):
            nonlocal calls
            calls += 1
            if calls == self.number:
                if self.crash:
                    os._exit(91)
                raise OSError(errno.ENOSPC, "injected disk full")
            return original(fd)

        os.fsync = fsync
        return build(snapshot)


def blocking_dns_transport(*args, **kwargs):
    import v8std_mcp_snapshots as loader

    def blocked(*args, **kwargs):
        time.sleep(120)

    with patch("socket.getaddrinfo", blocked):
        return loader._download(*args, **kwargs)


def store_in_process(site_url, cache, output):
    import v8std_mcp_snapshots as loader
    try:
        output.send(loader.SnapshotStore(site_url, cache).refresh(prepare=build))
    except (loader.LoaderError, loader.SnapshotError) as error:
        output.send(error.code)
    finally:
        output.close()


class Source:
    """HTTP dependency: handlers can delay headers/body and count actual GETs."""

    def __init__(self):
        self.archive, self.manifest = fixture.snapshot_fixture()
        self.requests = []
        self.fault = None
        self.headers = {}
        self.redirect = None
        self.redirects = {}
        self.requested = threading.Event()
        self.release = threading.Event()
        source = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                source.requests.append((self.path, dict(self.headers)))
                source.requested.set()
                is_manifest = self.path.endswith("manifest.json")
                if source.fault == "headers":
                    source.release.wait(10)
                location = source.redirects.get(self.path, source.redirect)
                if location:
                    self.send_response(302)
                    self.send_header("Location", location)
                    self.end_headers()
                    return
                if source.fault == "missing":
                    self.send_error(404)
                    return
                if is_manifest and (source.fault == "304" or (
                        source.fault == "conditional" and self.headers.get("If-None-Match"))):
                    self.send_response(304)
                    self.end_headers()
                    return
                payload = fixture.json_bytes(source.manifest) if is_manifest else source.archive
                if not is_manifest and source.fault == "corrupt":
                    payload = bytes([payload[0] ^ 1]) + payload[1:]
                self.send_response(200)
                self.send_header("Content-Type", "application/json" if is_manifest else "application/gzip")
                self.send_header("ETag", '"fixture-v1"')
                self.send_header("Last-Modified", "Thu, 10 Sep 2026 00:00:00 GMT")
                if "Content-Length" not in source.headers:
                    self.send_header("Content-Length", str(len(payload)))
                for key, value in source.headers.items():
                    if value is not None:
                        self.send_header(key, value)
                self.end_headers()
                try:
                    if source.fault == "body":
                        self.wfile.write(payload[:1])
                        self.wfile.flush()
                        source.release.wait(10)
                        self.wfile.write(payload[1:])
                    elif source.fault == "drip":
                        for byte in payload:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            if source.release.wait(.08):
                                break
                    else:
                        self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/knowledge/"

    def next_generation(self, label="Next release"):
        files = fixture.corpus_files()
        files["llms.txt"] += ("\n" + label + "\n").encode()
        self.archive, self.manifest = fixture.snapshot_fixture(files=fixture.with_metadata(files))

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)


class SnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("v8std_mcp_snapshots"),
                             "Task2 snapshot loader is not implemented")
        self.loader = importlib.import_module("v8std_mcp_snapshots")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name) / "cache"
        self.source = Source()
        self.addCleanup(self.source.close)
        self.store = self.loader.SnapshotStore(self.source.url, self.cache)


class SnapshotStoreTests(SnapshotTestCase):
    def test_verified_archive_is_streamed_into_staging_before_compressed_input_ends(self):
        extract = getattr(self.store, "_extract_verified", None)
        self.assertIsNotNone(extract, "Task2 must stream extraction into private staging")
        files = fixture.corpus_files()
        files["llms-full.txt"] = random.Random(37).randbytes(256 * 1024).hex().encode()
        archive, manifest = fixture.snapshot_fixture(files=fixture.with_metadata(files))
        fmt = importlib.import_module("v8std_mcp_snapshot_format")
        verified = fmt.verify_archive(archive, manifest)
        self.store.namespace.mkdir(parents=True)
        with tempfile.TemporaryDirectory(prefix=".stage-", dir=self.store.namespace) as directory:
            stage = Path(directory)

            class ObservedStream(io.BytesIO):
                output_before_eof = False

                def read(self, size=-1):
                    if not 0 < size <= 64 * 1024:
                        raise AssertionError("compressed input must be read in bounded chunks")
                    output = stage / "llms-full.txt"
                    if output.exists() and output.stat().st_size > 0 and self.tell() < len(archive):
                        self.output_before_eof = True
                    return super().read(size)

            source = ObservedStream(archive)
            extract(source, verified, stage, time.monotonic() + 60)
            self.assertTrue(source.output_before_eof,
                            "expanded bytes must reach staging before all compressed input is consumed")
            self.assertEqual({p.name: p.read_bytes() for p in stage.iterdir()}, verified.files)

    def test_prefix_real_archive_and_spawn_builder_survive_offline_restart(self):
        result = self.store.refresh(prepare=build)
        self.assertEqual(result.corpus_id, self.source.manifest["corpus_id"])
        self.assertNotEqual(result.pid, os.getpid())
        self.assertEqual(result.start_method, "spawn")
        self.assertEqual([p for p, _ in self.source.requests], [
            "/knowledge/ai/mcp/v1/manifest.json",
            "/knowledge/ai/mcp/v1/" + self.source.manifest["archive"]["path"],
        ])
        self.source.fault = "missing"
        restarted = self.loader.SnapshotStore(self.source.url, self.cache)
        cached = restarted.cached()
        self.assertEqual(cached.metadata["corpus_id"], result.corpus_id)
        self.assertIn(b"std437", cached.files["pages.jsonl"])

    def test_normalized_source_reuses_cache_and_other_sources_never_do(self):
        first = self.store.refresh()
        alias = self.loader.SnapshotStore("  " + self.source.url.rstrip("/") + "  ", self.cache)
        self.assertEqual(alias.cached().archive_sha256, first.archive_sha256)
        other = self.loader.SnapshotStore(self.source.url + "other/", self.cache)
        self.assertIsNone(other.cached())

    def test_different_sources_on_shared_volume_download_and_cache_independently(self):
        first = self.store.refresh()
        other = self.loader.SnapshotStore(self.source.url + "other/", self.cache)
        second = other.refresh()
        self.assertEqual(first.archive_sha256, second.archive_sha256)
        self.assertNotEqual(self.store.namespace, other.namespace)
        self.assertEqual(len([p for p, _ in self.source.requests if p.endswith(".tar.gz")]), 2)
        self.assertEqual(other.cached().archive_sha256, second.archive_sha256)

    def test_prepare_failure_does_not_activate_disk_generation(self):
        before = self.store.refresh()
        self.source.next_generation()
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh(prepare=fail_build)
        self.assertEqual(caught.exception.code, "prepare_failed")
        self.assertEqual(str(caught.exception), "prepare_failed")
        self.assertEqual(self.store.cached().archive_sha256, before.archive_sha256)

    def test_invalid_selected_archive_preserves_cache_without_public_fallback(self):
        before = self.store.refresh()
        self.source.next_generation()
        self.source.fault = "corrupt"
        with self.assertRaises(self.loader.SnapshotError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "archive_hash")
        self.assertEqual(self.store.cached().archive_sha256, before.archive_sha256)
        self.assertTrue(all(p.startswith("/knowledge/") for p, _ in self.source.requests))

    def test_local_manifest_cannot_select_public_archive(self):
        self.source.manifest["archive"]["path"] = (
            "https://ai.v8std.ru/indexes/v1/" + self.source.manifest["archive"]["path"])
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "url_policy")
        self.assertEqual(len(self.source.requests), 1)
        self.assertIsNone(self.store.cached())

    def test_redirects_reject_foreign_traversal_credentials_and_outside_prefix(self):
        for location in ("//example.invalid/", "../escape", "/elsewhere/", "%2e%2e/x",
                         "http://user:secret@127.0.0.1/x", "http://example.invalid/x"):
            with self.subTest(location=location):
                self.source.redirect = location
                with self.assertRaises(self.loader.LoaderError) as caught:
                    self.store.refresh()
                self.assertEqual(caught.exception.code, "url_policy")
        self.assertEqual(len(self.source.requests), 6)

    def test_redirect_loop_stops_after_three_hops(self):
        self.source.redirect = "/knowledge/ai/mcp/v1/manifest.json"
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "redirect_limit")
        self.assertEqual(len(self.source.requests), 4)

    def test_conditional_get_and_same_hash_never_redownload_archive(self):
        before = self.store.refresh()
        self.source.fault = "conditional"
        self.assertEqual(self.store.refresh().archive_sha256, before.archive_sha256)
        self.source.fault = None
        self.assertEqual(self.store.refresh().archive_sha256, before.archive_sha256)
        manifests = [h for p, h in self.source.requests if p.endswith("manifest.json")]
        archives = [p for p, h in self.source.requests if p.endswith(".tar.gz")]
        self.assertEqual(len(archives), 1)
        self.assertNotIn("If-None-Match", manifests[0])
        self.assertEqual(manifests[1]["If-None-Match"], '"fixture-v1"')
        self.assertEqual(manifests[1]["If-Modified-Since"], "Thu, 10 Sep 2026 00:00:00 GMT")

    def test_304_without_valid_cache_retries_unconditionally_once(self):
        self.source.fault = "304"
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "http_status")
        self.assertEqual(len(self.source.requests), 2)
        self.assertTrue(all("If-None-Match" not in h for _, h in self.source.requests))

    def test_encoding_length_and_stream_byte_caps(self):
        for headers in ({"Content-Encoding": "gzip"}, {"Content-Length": "99999999"},
                        {"Content-Length": "-1"}, {"Content-Length": "not-a-number"}):
            with self.subTest(headers=headers):
                self.source.headers = headers
                with self.assertRaises(self.loader.LoaderError):
                    self.store.refresh()
                self.assertIsNone(self.store.cached())
        self.source.headers = {"Content-Length": None}
        self.source.manifest["extra"] = "x" * (64 * 1024)
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "http_size")

    def test_whole_deadline_reaps_slow_headers_body_and_drip(self):
        for fault in ("headers", "body", "drip"):
            with self.subTest(fault=fault):
                self.source.fault = fault
                self.store._attempt_seconds = .65
                start = time.monotonic()
                with self.assertRaises(self.loader.LoaderError) as caught:
                    self.store.refresh()
                self.assertEqual(caught.exception.code, "deadline")
                self.assertLess(time.monotonic() - start, 2)
                self.assertFalse(multiprocessing.active_children())

    def test_current_corruption_falls_back_to_previous_same_source(self):
        first = self.store.refresh()
        self.source.next_generation()
        second = self.store.refresh()
        for path in self.cache.rglob("snapshot.tar.gz"):
            if fixture.sha256(path.read_bytes()) == second.archive_sha256:
                path.write_bytes(b"corrupt")
        self.assertEqual(self.store.cached().archive_sha256, first.archive_sha256)

    def test_verified_redownload_repairs_corrupt_current_directory(self):
        self.store.refresh()
        self.source.next_generation()
        second = self.store.refresh()
        directory = self.store.namespace / "generations" / second.archive_sha256
        (directory / "pages.jsonl").write_bytes(b"corrupt expanded member")
        self.assertNotEqual(self.store.cached().archive_sha256, second.archive_sha256)
        self.assertEqual(self.store.refresh().archive_sha256, second.archive_sha256)
        self.assertEqual(self.store.cached().archive_sha256, second.archive_sha256)

    def test_manifest_reactivates_previous_verified_archive_without_download(self):
        original_archive, original_manifest = self.source.archive, self.source.manifest
        first = self.store.refresh()
        self.source.next_generation()
        second = self.store.refresh()
        self.source.archive, self.source.manifest = original_archive, original_manifest
        self.assertEqual(self.store.refresh().archive_sha256, first.archive_sha256)
        state = json.loads((self.store.namespace / "state.json").read_bytes())
        self.assertEqual(state["previous"], second.archive_sha256)
        self.assertEqual(len([p for p, _ in self.source.requests if p.endswith(".tar.gz")]), 2)

    def test_new_cache_namespace_directory_entries_are_durable_before_activation(self):
        synced = set()
        observed = []
        original_sync, original_replace = os.fsync, os.replace

        def fsync(fd):
            info = os.fstat(fd)
            synced.add((info.st_dev, info.st_ino))
            return original_sync(fd)

        def replace(source, target):
            if Path(target).name == "state.json":
                for directory in (self.cache.parent, self.cache, self.store.namespace):
                    info = directory.stat()
                    observed.append((info.st_dev, info.st_ino) in synced)
            return original_replace(source, target)

        with patch("os.fsync", fsync), patch("os.replace", replace):
            self.store._refresh(build, time.monotonic() + 60)
        self.assertEqual(self.store.cached().metadata["corpus_id"], self.source.manifest["corpus_id"])
        self.assertEqual(observed, [True, True, True])

    def test_existing_cache_volume_does_not_require_writable_parent_filesystem(self):
        before = self.store.refresh()
        parent = self.cache.parent.stat()
        original = os.fsync

        def fsync(fd):
            info = os.fstat(fd)
            if (info.st_dev, info.st_ino) == (parent.st_dev, parent.st_ino):
                raise OSError(errno.EROFS, "read-only container root")
            return original(fd)

        with patch("os.fsync", fsync):
            self.store._refresh(build, time.monotonic() + 60)
        self.assertEqual(self.store.cached().archive_sha256, before.archive_sha256)

    def test_postcommit_cleanup_failure_does_not_report_failed_activation(self):
        self.store.refresh()
        self.source.next_generation()
        result = self.store.refresh(prepare=CleanupFault(self.store.namespace))
        self.assertEqual(result.corpus_id, self.source.manifest["corpus_id"])
        self.assertEqual(self.store.cached().metadata["corpus_id"], result.corpus_id)

    def test_unpickleable_result_is_preparation_failure_before_disk_activation(self):
        first = self.store.refresh()
        pointer = (self.store.namespace / "state.json").read_bytes()
        self.source.next_generation()
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh(prepare=unpickleable_build)
        self.assertEqual(caught.exception.code, "prepare_failed")
        self.assertEqual((self.store.namespace / "state.json").read_bytes(), pointer)
        self.assertEqual(self.store.cached().archive_sha256, first.archive_sha256)

    def test_large_prepared_result_crosses_real_ipc_and_returns_after_commit(self):
        generation, payload = self.store.refresh(prepare=large_build)
        self.assertEqual(payload, b"x" * (8 * 1024 * 1024))
        self.assertNotEqual(generation.pid, os.getpid())
        self.assertEqual(self.store.cached().metadata["corpus_id"], generation.corpus_id)
        self.assertFalse(multiprocessing.active_children())

    def test_prepare_and_dns_are_terminated_at_whole_attempt_deadline(self):
        self.store._attempt_seconds = .65
        for prepare, transport in ((blocking_build, self.loader._download),
                                   (build, blocking_dns_transport)):
            with self.subTest(prepare=prepare.__name__):
                self.store._transport = transport
                start = time.monotonic()
                with self.assertRaises(self.loader.LoaderError) as caught:
                    self.store.refresh(prepare=prepare)
                self.assertEqual(caught.exception.code, "deadline")
                self.assertLess(time.monotonic() - start, 2)
                self.assertFalse(multiprocessing.active_children())
                self.assertIsNone(self.store.cached())

    def test_uncooperative_worker_is_killed_and_reaped_after_terminate_grace(self):
        self.store._attempt_seconds = .65
        start = time.monotonic()
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh(prepare=ignores_termination_build)
        self.assertEqual(caught.exception.code, "deadline")
        self.assertLess(time.monotonic() - start, 2)
        self.assertFalse(multiprocessing.active_children())

    def test_each_commit_fsync_failure_keeps_old_disk_pointer(self):
        before = self.store.refresh()
        pointer = (self.store.namespace / "state.json").read_bytes()
        self.source.next_generation()
        for number in range(1, 7):
            with self.subTest(fsync=number):
                with self.assertRaises(self.loader.LoaderError) as caught:
                    self.store.refresh(prepare=CommitFault(number))
                self.assertEqual(caught.exception.code, "cache_io")
                self.assertEqual((self.store.namespace / "state.json").read_bytes(), pointer)
                self.assertEqual(self.store.cached().archive_sha256, before.archive_sha256)

    def test_crash_at_commit_stages_recovers_complete_old_or_new_generation(self):
        first = self.store.refresh()
        self.source.next_generation()
        for number in range(1, 7):
            with self.subTest(fsync=number):
                with self.assertRaises(self.loader.LoaderError) as caught:
                    self.store.refresh(prepare=CommitFault(number, crash=True))
                self.assertEqual(caught.exception.code, "worker_failed")
                recovered = self.store.cached()
                expected = first.archive_sha256 if number < 6 else self.source.manifest["archive"]["sha256"]
                self.assertEqual(recovered.archive_sha256, expected)
                self.assertFalse(multiprocessing.active_children())
        self.assertEqual(self.store.refresh().archive_sha256, self.source.manifest["archive"]["sha256"])

    def test_corrupt_pointer_uses_durable_rollback_record(self):
        first = self.store.refresh()
        self.source.next_generation()
        self.store.refresh()
        (self.store.namespace / "state.json").write_bytes(b"broken JSON")
        self.assertEqual(self.store.cached().archive_sha256, first.archive_sha256)

    def test_gc_preserves_last_verified_rollback_when_newer_pointer_targets_are_bad(self):
        first = self.store.refresh()
        self.source.next_generation()
        second = self.store.refresh()
        namespace = self.store.namespace
        state = json.loads((namespace / "state.json").read_bytes())
        # Damaged newest pointer still has a valid schema; rollback.json retains
        # the only usable generation. A failed refresh must not GC that fallback.
        state["active"], state["previous"] = "a" * 64, second.archive_sha256
        (namespace / "state.json").write_bytes(fixture.json_bytes(state))
        (namespace / "generations" / second.archive_sha256 / "pages.jsonl").write_bytes(b"bad")
        self.assertEqual(self.store.cached().archive_sha256, first.archive_sha256)
        self.source.fault = "missing"
        with self.assertRaises(self.loader.LoaderError):
            self.store.refresh()
        self.assertIsNotNone(self.store.cached(), "GC removed the only verified rollback")
        self.assertEqual(self.store.cached().archive_sha256, first.archive_sha256)

    def test_deadline_covers_partial_trusted_ipc_result_and_reaps_sender(self):
        self.store._attempt_seconds = .65
        start = time.monotonic()
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh(prepare=partial(blocking_ipc_build, corpus_id=self.source.manifest["corpus_id"]))
        self.assertEqual(caught.exception.code, "deadline")
        self.assertLess(time.monotonic() - start, 2)
        self.assertFalse(multiprocessing.active_children())
        # Commit completed before this injected partial-send crash window.
        self.assertEqual(self.store.cached().metadata["corpus_id"], self.source.manifest["corpus_id"])

    def test_pins_retain_predecessor_until_unpinned_and_gc_keeps_other_namespace(self):
        first = self.store.refresh()
        pins = self.store.namespace / "pins.json"
        pins.write_bytes(fixture.json_bytes({"archives": [first.archive_sha256]}))
        foreign = self.cache / "v1-other-source" / ".stage-owned-by-another-process"
        foreign.mkdir(parents=True)
        (foreign / "keep").write_bytes(b"foreign source")
        self.source.next_generation("second")
        second = self.store.refresh()
        self.source.next_generation("third")
        third = self.store.refresh()
        generations = self.store.namespace / "generations"
        self.assertEqual({p.name for p in generations.iterdir()},
                         {first.archive_sha256, second.archive_sha256, third.archive_sha256})
        pins.write_bytes(fixture.json_bytes({"archives": []}))
        self.store.refresh()
        self.assertEqual({p.name for p in generations.iterdir()},
                         {second.archive_sha256, third.archive_sha256})
        self.assertEqual((foreign / "keep").read_bytes(), b"foreign source")

    def test_volume_budget_counts_foreign_staging_pins_and_never_evicts_them(self):
        first = self.store.refresh()
        pins = self.store.namespace / "pins.json"
        pins.write_bytes(fixture.json_bytes({"archives": [first.archive_sha256]}))
        other = self.cache / "v1-other-source" / ".stage-foreign"
        other.mkdir(parents=True)
        blob = other / "reserved"
        with blob.open("wb") as stream:
            stream.truncate(256 * 1024 * 1024 - 32 * 1024)
        before = sum(p.stat().st_size for p in self.cache.rglob("*") if p.is_file())
        self.assertLess(before, 256 * 1024 * 1024)
        self.source.next_generation()
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "cache_budget")
        self.assertEqual(blob.stat().st_size, 256 * 1024 * 1024 - 32 * 1024)
        self.assertEqual(self.store.cached().archive_sha256, first.archive_sha256)
        self.assertEqual(before, sum(p.stat().st_size for p in self.cache.rglob("*") if p.is_file()))

    def test_symlinks_and_invalid_pins_fail_closed_without_deleting_targets(self):
        first = self.store.refresh()
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "keep").write_bytes(b"external")
        (self.store.namespace / ".stage-link").symlink_to(outside, target_is_directory=True)
        (self.store.namespace / "pins.json").write_bytes(b'{"archives":["../outside"]}')
        self.source.next_generation()
        with self.assertRaises(self.loader.LoaderError):
            self.store.refresh()
        self.assertEqual((outside / "keep").read_bytes(), b"external")
        self.assertEqual(self.store.cached().archive_sha256, first.archive_sha256)

    def test_two_processes_share_download_and_each_builds_own_generation(self):
        self.source.fault = "headers"
        context = multiprocessing.get_context("spawn")
        parents = []
        processes = []
        for _ in range(2):
            parent, child = context.Pipe(duplex=False)
            process = context.Process(target=store_in_process, args=(self.source.url, self.cache, child))
            parents.append(parent)
            processes.append(process)
            process.start()
            child.close()
        try:
            self.assertTrue(self.source.requested.wait(4))
            time.sleep(.35)  # second process reaches the contended namespace flock
            self.source.release.set()
            results = []
            for parent in parents:
                self.assertTrue(parent.poll(5))
                results.append(parent.recv())
            self.assertTrue(all(isinstance(result, Generation) for result in results), results)
            self.assertNotEqual(results[0].pid, results[1].pid)
            self.assertEqual(results[0].corpus_id, results[1].corpus_id)
            self.assertEqual(len(self.source.requests), 2)
        finally:
            self.source.release.set()
            for process in processes:
                process.join(2)
                if process.is_alive():
                    process.kill()
                    process.join(2)
                process.close()
            for parent in parents:
                parent.close()

    def test_lock_wait_is_bounded_and_does_not_touch_network(self):
        self.store.refresh()
        self.source.requests.clear()
        self.store._attempt_seconds = .65
        with (self.store.namespace / ".lock").open("rb") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            with self.assertRaises(self.loader.LoaderError) as caught:
                self.store.refresh()
            self.assertIn(caught.exception.code, {"lock_timeout", "deadline"})
        self.assertFalse(self.source.requests)
        self.assertFalse(multiprocessing.active_children())

    def test_read_timeout_is_distinct_from_whole_attempt_and_empty_length_is_validated(self):
        self.store._read_seconds = .12
        self.source.fault = "body"
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "network")
        self.source.fault = None
        self.source.headers = {"Content-Length": "0"}
        with self.assertRaises(self.loader.SnapshotError):
            self.store.refresh()

    def test_allowed_redirect_preserves_selected_base_and_limits_archive_redirects(self):
        manifest_path = "/knowledge/ai/mcp/v1/manifest.json"
        self.source.redirects[manifest_path] = "/knowledge/mirror/manifest.json"
        self.store.refresh()
        self.assertEqual(self.source.requests[-1][0],
                         "/knowledge/mirror/" + self.source.manifest["archive"]["path"])
        self.source.next_generation()
        archive_path = "/knowledge/mirror/" + self.source.manifest["archive"]["path"]
        self.source.redirects[archive_path] = "/outside/snapshot.tar.gz"
        with self.assertRaises(self.loader.LoaderError) as caught:
            self.store.refresh()
        self.assertEqual(caught.exception.code, "url_policy")

    def test_public_delivery_exception_and_https_downgrade_policy(self):
        _, manifest = fixture.snapshot_fixture()
        manifest["archive"]["path"] = "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["path"]
        url, boundary = self.loader._archive_url(manifest, "https://v8std.ru/ai/mcp/v1/manifest.json", "https://v8std.ru/")
        self.assertEqual(url, manifest["archive"]["path"])
        self.assertEqual(boundary, "https://ai.v8std.ru/indexes/v1/")
        for location in (url.replace("https:", "http:"), "https://v8std.ru/ai/mcp/v1/x",
                         "https://ai.v8std.ru/indexes/v2/x"):
            with self.assertRaises(self.loader.LoaderError) as caught:
                self.loader._allowed_url(location, url, boundary)
            self.assertEqual(caught.exception.code, "url_policy")


class SnapshotCoordinatorTests(SnapshotTestCase):
    def coordinator(self, **kwargs):
        coordinator = self.loader.SnapshotCoordinator(self.store, build, **kwargs)
        self.addCleanup(coordinator.close)
        return coordinator

    def wait_until(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.01)
        self.fail("background coordinator did not reach expected state")

    def test_cold_failure_is_explicit_and_status_does_not_expose_raw_errors(self):
        self.source.fault = "missing"
        coordinator = self.coordinator(refresh_seconds=0)
        coordinator.start()
        self.wait_until(lambda: coordinator.status()["refresh_error_code"] is not None)
        with self.assertRaises(self.loader.LoaderError) as caught:
            coordinator.current()
        self.assertEqual(caught.exception.code, "INDEX_NOT_READY")
        self.assertEqual(coordinator.status()["refresh_error_code"], "http_status")
        self.assertNotIn(self.source.url, json.dumps(coordinator.status()))

    def test_warm_current_and_status_are_fast_while_network_blocks_then_close_reaps(self):
        self.store.refresh()
        self.source.requested.clear()
        self.source.fault = "headers"
        coordinator = self.coordinator(refresh_seconds=0)
        coordinator.start()
        self.wait_until(lambda: coordinator.status()["ready"])
        before = coordinator.current()
        self.assertTrue(self.source.requested.wait(3))
        start = time.monotonic()
        for _ in range(1000):
            self.assertIs(coordinator.current(), before)
            self.assertTrue(coordinator.status()["ready"])
        self.assertLess(time.monotonic() - start, .25)
        start = time.monotonic()
        coordinator.close()
        self.assertLess(time.monotonic() - start, 2)
        self.assertFalse(multiprocessing.active_children())

    def test_close_reaps_partial_ipc_sender_and_preserves_process_generation(self):
        original = self.store.refresh()
        self.source.next_generation()
        target = self.source.manifest["corpus_id"]
        coordinator = self.loader.SnapshotCoordinator(
            self.store, partial(blocking_ipc_build, corpus_id=target), refresh_seconds=0)
        self.addCleanup(coordinator.close)
        coordinator.start()
        self.wait_until(lambda: coordinator.status()["ready"])
        before = coordinator.current()
        self.assertEqual(before.corpus_id, original.metadata["corpus_id"])
        self.wait_until(lambda: self.store.cached().metadata["corpus_id"] == target)
        start = time.monotonic()
        coordinator.close()
        self.assertLess(time.monotonic() - start, 2)
        self.assertIs(coordinator.current(), before)
        self.assertFalse(multiprocessing.active_children())

    def test_zero_refresh_stops_after_successful_bootstrap(self):
        coordinator = self.coordinator(refresh_seconds=0)
        coordinator.start()
        coordinator.start()
        self.wait_until(lambda: coordinator.status()["last_success_at"] is not None)
        self.source.next_generation()
        time.sleep(.15)
        self.assertEqual(len(self.source.requests), 2)
        self.assertEqual(coordinator.current().start_method, "spawn")
        self.assertIsNotNone(coordinator.status()["loaded_at"])
        self.assertIsNotNone(coordinator.status()["last_checked_at"])

    def test_generation_retirement_does_not_hold_query_state_lock(self):
        coordinator = self.coordinator(refresh_seconds=0)
        retiring, release, queried = threading.Event(), threading.Event(), threading.Event()
        coordinator._accept(SlowRetirement(retiring, release),
                            {"archive_sha256": "a", "corpus_id": "old"}, checked=True)
        swap = threading.Thread(target=coordinator._accept,
                                args=("new", {"archive_sha256": "b", "corpus_id": "new"}),
                                kwargs={"checked": True})
        swap.start()
        values = []

        def query():
            values.append(coordinator.current())
            queried.set()

        reader = threading.Thread(target=query)
        try:
            self.assertTrue(retiring.wait(1))
            reader.start()
            self.assertTrue(queried.wait(.25), "retiring generation holds query lock")
            self.assertEqual(values, ["new"])
        finally:
            release.set()
            swap.join(2)
            if reader.ident:
                reader.join(2)

    def test_repeated_cold_faults_back_off_without_becoming_ready(self):
        self.source.fault = "missing"
        coordinator = self.coordinator(refresh_seconds=0)
        schedule = RecordingStop(4)
        coordinator._stop = schedule
        with patch("v8std_mcp_snapshots.random.uniform", return_value=1.2):
            coordinator.start()
            self.wait_until(schedule.is_set)
        self.assertEqual(schedule.delays, [36, 72, 144, 288])
        self.assertEqual(len(self.source.requests), 4)
        self.assertFalse(coordinator.status()["ready"])

    def test_same_hash_preserves_generation_and_success_interval_uses_jitter(self):
        coordinator = self.coordinator()
        schedule = RecordingStop(2)
        coordinator._stop = schedule
        with patch("v8std_mcp_snapshots.random.uniform", side_effect=[.8, 1.2]):
            coordinator.start()
            self.wait_until(schedule.is_set)
        self.assertEqual(schedule.delays, [2880, 4320])
        self.assertEqual(len([p for p, _ in self.source.requests if p.endswith(".tar.gz")]), 1)
        state = coordinator.status()
        self.assertLess(state["loaded_at"], state["last_success_at"])
        self.assertEqual(state["last_checked_at"], state["last_success_at"])

    def test_backoff_extremes_stay_within_contract(self):
        coordinator = self.coordinator()
        with patch("v8std_mcp_snapshots.random.uniform", return_value=.8):
            self.assertEqual(coordinator._delay(1), 30)
        with patch("v8std_mcp_snapshots.random.uniform", return_value=1.2):
            self.assertEqual(coordinator._delay(10000), 3600)


if __name__ == "__main__":
    unittest.main()
