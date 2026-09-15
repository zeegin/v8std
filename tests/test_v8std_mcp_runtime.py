"""Frozen generations and the official SDK lifecycle, with local sources only."""
from functools import partial
import importlib
import importlib.util
import json
import contextlib
import io
import os
from pathlib import Path
import pickle
import queue
import signal
import select
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tests import mcp_snapshot_fixtures as fixture
from tests import test_v8std_mcp_snippet as snippet_compat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
LOCAL = "http://localhost:8080/kb/"


def verified():
    from v8std_mcp_snapshot_format import verify_archive
    return verify_archive(*fixture.snapshot_fixture())


class Current:
    """A deterministic pointer swap exactly when nested search starts."""
    def __init__(self, generation):
        self.generation = generation
        self.calls = 0

    def current(self):
        self.calls += 1
        return self.generation


class RuntimeTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("v8std_mcp_runtime"))
        return importlib.import_module("v8std_mcp_runtime")

    def test_frozen_factory_and_ipc_reconstruction_never_load_sources(self):
        runtime = self.module()
        from v8std_mcp_index import V8StdIndex
        with patch.object(V8StdIndex, "_fetch_url", side_effect=AssertionError("network")):
            generation = runtime.build_generation(verified(), max_snippet_chars=4000)
            encoded = pickle.dumps(generation)
            with patch.object(V8StdIndex, "_parse_pages", side_effect=AssertionError("reparse")), \
                 patch.object(V8StdIndex, "_replace_index", side_effect=AssertionError("rebuild")):
                decoded = pickle.loads(encoded)
            self.assertEqual(decoded.index.search("std437"), generation.index.search("std437"))
            self.assertEqual(decoded.index.page("std437")["page"]["id"], "std437")
            with self.assertRaisesRegex(RuntimeError, "frozen"):
                decoded.index.load()
            self.assertEqual(decoded.corpus_id, generation.corpus_id)
            self.assertEqual(decoded.page_paths, {"std437": {
                "site_path": "std/437/", "markdown_path": "std/437.md"}})

    def test_generation_capture_pins_nested_calls_and_returns_independent_copy(self):
        runtime = self.module()
        from v8std_mcp_index import V8StdIndex
        old = runtime.build_generation(verified(), max_snippet_chars=4000, site_url=LOCAL)
        new = runtime.build_generation(verified(), max_snippet_chars=4000, site_url=LOCAL)
        current = Current(old)
        with tempfile.TemporaryDirectory() as directory:
            facade = runtime.SnapshotIndex(site_url=LOCAL, cache_dir=Path(directory))
            facade.coordinator = current
            original = old.index.search

            def swap(*args, **kwargs):
                current.generation = new
                return original(*args, **kwargs)

            with patch.object(old.index, "search", side_effect=swap), \
                 patch.object(new.index, "search", side_effect=AssertionError("mixed generation")), \
                 patch.object(V8StdIndex, "_fetch_url", side_effect=AssertionError("network")):
                result = facade.explain_snippet("std437")
            self.assertEqual(current.calls, 1)
            self.assertEqual(result["standards"][0]["url"], LOCAL + "std/437/")
            page = facade.page(LOCAL + "std/437/")
            self.assertTrue(page["found"])
            page["page"]["aliases"].append("mutation")
            self.assertNotIn("mutation", facade.page("std437")["page"]["aliases"])
            self.assertIn('`', page["page"]["body_markdown"])
            self.assertEqual(page["page"]["url"], LOCAL + "std/437/")
            self.assertEqual(page["page"]["source_urls"], fixture.page_fixture()["source_urls"])

    def test_validation_before_readiness_for_all_data_boundaries(self):
        runtime = self.module()
        with tempfile.TemporaryDirectory() as directory:
            facade = runtime.SnapshotIndex(site_url=LOCAL, cache_dir=Path(directory))
            for call in (lambda: facade.search("x" * 501), lambda: facade.search("x", mode="invalid"),
                         lambda: facade.page("x" * 1001), lambda: facade.related("std437", relations=["bad"]),
                         lambda: facade.explain_snippet("x" * 4001),
                         lambda: facade.explain_diagnostics([1])):
                with self.assertRaises(ValueError) as caught:
                    call()
                self.assertNotIn("INDEX_NOT_READY", str(caught.exception))
            for call in (lambda: facade.search("std437"), lambda: facade.page("std437"),
                         lambda: facade.related("std437"), lambda: facade.explain_snippet(""),
                         lambda: facade.explain_diagnostics([])):
                with self.assertRaisesRegex(ValueError, "INDEX_NOT_READY"):
                    call()

    def test_full_link_is_rebased_before_existing_body_budget_is_applied(self):
        runtime = self.module()
        from v8std_mcp_snapshot_format import verify_archive
        body = "x" * 965 + " [boundary](https://v8std.ru/std/437/?query=yes#anchor) end"
        page = fixture.page_fixture()
        page["body_markdown"] = body
        vectors = fixture.vector_fixtures()
        vectors[1]["text_sha256"] = fixture.sha256(body.encode())
        files = fixture.with_metadata(fixture.corpus_files(pages=[page], vectors=vectors))
        snapshot = verify_archive(*fixture.snapshot_fixture(files=files))
        generation = runtime.build_generation(snapshot, max_snippet_chars=4000)
        with tempfile.TemporaryDirectory() as directory:
            facade = runtime.SnapshotIndex(site_url=LOCAL, cache_dir=Path(directory))
            facade.coordinator = Current(generation)
            result = facade.page("std437", body_limit=1000)["page"]
            expected = ("x" * 965 + " [boundary](http://localhost:8080/kb/std/437/?query=yes#anchor) end")[:1000] + "\n\n..."
            self.assertEqual(result["body_markdown"], expected)
            self.assertTrue(result["body_truncated"])
            self.assertEqual(len(result["body_markdown"]), 1005)  # Existing five-character marker.
            self.assertEqual(generation.index.resolve("std437")["body_markdown"], body)

    def test_official_http_discovery_before_ready_and_session_end_does_not_close_index(self):
        runtime = self.module()
        from v8std_mcp_server import build_server
        from starlette.testclient import TestClient
        from tests.test_v8std_mcp_snapshots import Source
        source = Source()
        try:
            with tempfile.TemporaryDirectory() as directory:
                facade = runtime.SnapshotIndex(site_url=source.url, cache_dir=Path(directory), refresh_seconds=0)
                server = build_server(facade, host="127.0.0.1", port=8765, mcp_path="/mcp",
                                      allowed_hosts=["testserver"], allowed_origins=[])
                with TestClient(server.streamable_http_app()) as client:
                    self.assertEqual(client.get("/livez").status_code, 200)
                    for number in range(2):
                        response = client.post("/mcp", headers={"Accept": "application/json, text/event-stream"},
                            json={"jsonrpc": "2.0", "id": number, "method": "tools/list", "params": {}})
                        self.assertEqual(len(response.json()["result"]["tools"]), 5)
                    deadline = time.monotonic() + 8
                    while not facade.status()["ok"] and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertTrue(facade.status()["ok"], facade.status())
                    self.assertEqual(facade.status().get("row_count"), 1)
                    self.assertTrue(facade.status().get("semantic_enabled"))
                    self.assertEqual(client.get("/healthz").status_code, 200)
                    response = client.post("/mcp", headers={"Accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                              "params": {"name": "v8std_get_page", "arguments": {"id_or_alias_or_url": "std437"}}})
                    self.assertFalse(response.json()["result"].get("isError", False))
                self.assertFalse(facade.coordinator._thread.is_alive())
        finally:
            source.close()

    def test_tools_serve_warm_page_through_slow_and_corrupt_refresh(self):
        runtime = self.module()
        from v8std_mcp_snapshots import SnapshotStore
        from tests.test_v8std_mcp_snapshots import Source
        from tests.test_v8std_mcp_tools_only import http_rpc, initialize, call_tool, assert_resources_disabled
        for fault in (None, "corrupt"):
            source = Source()
            try:
                with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                    SnapshotStore(source.url, Path(directory)).refresh()
                    page = fixture.page_fixture()
                    page["body_markdown"] = "Обновлённая страница"
                    vectors = fixture.vector_fixtures()
                    vectors[1]["text_sha256"] = fixture.sha256(page["body_markdown"].encode())
                    files = fixture.with_metadata(fixture.corpus_files(pages=[page], vectors=vectors))
                    source.archive, source.manifest = fixture.snapshot_fixture(files=files)
                    source.requested.clear()
                    source.fault = "headers"
                    facade = runtime.SnapshotIndex(site_url=source.url, cache_dir=Path(directory), refresh_seconds=0)
                    with http_rpc(facade) as rpc:
                        initialize(rpc)
                        self.assertTrue(source.requested.wait(5))
                        arguments = {"id_or_alias_or_url": "std437"}
                        old = call_tool(self, rpc, "v8std_get_page", arguments)["page"]
                        self.assertIn("[Стандарт](" + source.url, old["body_markdown"])
                        assert_resources_disabled(self, rpc)
                        source.fault = fault
                        source.release.set()
                        deadline = time.monotonic() + 8
                        while facade.status()["last_checked_at"] is None:
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.02)
                        current = call_tool(self, rpc, "v8std_get_page", arguments)["page"]
                        if fault:
                            self.assertIsNotNone(facade.status()["refresh_error_code"])
                            self.assertEqual(current, old)
                        else:
                            self.assertIsNone(facade.status()["refresh_error_code"])
                            self.assertEqual(current["body_markdown"], "Обновлённая страница")
                        self.assertEqual(current["url"], source.url + "std/437/")
                        assert_resources_disabled(self, rpc)
            finally:
                source.close()

    def test_verified_warm_generation_becomes_ready_with_source_offline(self):
        runtime = self.module()
        from v8std_mcp_snapshots import SnapshotStore
        from tests.test_v8std_mcp_snapshots import Source
        source = Source()
        try:
            with tempfile.TemporaryDirectory() as directory:
                SnapshotStore(source.url, Path(directory)).refresh()
                # A refused loopback connection cannot accidentally hit public data.
                source.server.shutdown()
                source.server.server_close()
                facade = runtime.SnapshotIndex(site_url=source.url, cache_dir=Path(directory), refresh_seconds=0)
                facade.start()
                try:
                    deadline = time.monotonic() + 5
                    while not facade.status()["ok"]:
                        self.assertLess(time.monotonic(), deadline)
                        time.sleep(.02)
                    self.assertEqual(facade.page("std437")["page"]["url"], source.url + "std/437/")
                finally:
                    facade.close()
        finally:
            source.close()

    def test_facade_preserves_preview_budgets_and_captures_each_data_call_once(self):
        runtime = self.module()
        generation = runtime.build_generation(verified(), max_snippet_chars=32000, site_url=LOCAL)
        with tempfile.TemporaryDirectory() as directory:
            facade = runtime.SnapshotIndex(site_url=LOCAL, cache_dir=Path(directory), max_snippet_chars=32000)
            current = Current(generation)
            facade.coordinator = current
            snippet = ('Адрес = "https://v8std.ru/std/437/";\n' + "слово " * 6000)[:32000]
            canonical = generation.index.explain_snippet(snippet, limit=1)
            result = facade.explain_snippet(snippet, limit=1)
            self.assertEqual(result["normalized_text"], canonical["normalized_text"])
            self.assertEqual(result["tokens"], canonical["tokens"])
            self.assertLessEqual(len(result["normalized_text"]), 1000)
            self.assertLessEqual(len(result["tokens"]), 80)
            self.assertLessEqual(sum(map(len, result["tokens"])), 4000)
            self.assertLessEqual(len(result["diagnostics"]) + len(result["standards"]), 1)
            self.assertEqual(current.calls, 1)
            for call in (lambda: facade.search("std437"), lambda: facade.page("std437"),
                         lambda: facade.related("std437"), lambda: facade.explain_diagnostics(["missing"])):
                before = current.calls
                call()
                self.assertEqual(current.calls, before + 1)


class ConfigurationTests(unittest.TestCase):
    def test_cache_cli_env_default_precedence_and_early_invalid_inputs(self):
        from v8std_mcp_server import parse_args, main
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(parse_args([]).cache_dir, Path("/var/lib/v8std-mcp"))
        with patch.dict(os.environ, {"V8STD_MCP_CACHE_DIR": "/tmp/env-cache"}, clear=True):
            self.assertEqual(parse_args([]).cache_dir, Path("/tmp/env-cache"))
            self.assertEqual(parse_args(["--cache-dir", "/tmp/cli-cache"]).cache_dir, Path("/tmp/cli-cache"))
        with patch.dict(os.environ, {"V8STD_MCP_CACHE_DIR": ""}, clear=True):
            self.assertEqual(parse_args(["--cache-dir", "/tmp/cli-cache"]).cache_dir, Path("/tmp/cli-cache"))
        for argv, environment in (([], {"V8STD_MCP_CACHE_DIR": ""}),
                                  ([], {"V8STD_MCP_CACHE_DIR": " \t"}),
                                  (["--cache-dir", ""], {}),
                                  (["--cache-dir", "  "], {}),
                                  (["--port", "-1"], {}), (["--port", "65536"], {})):
            with self.subTest(argv=argv, environment=environment), \
                 patch.dict(os.environ, environment, clear=True), \
                 contextlib.redirect_stderr(io.StringIO()), \
                 patch("v8std_mcp_server.SnapshotIndex", side_effect=AssertionError("source construction")), \
                 patch("v8std_mcp_server.V8StdIndex", side_effect=AssertionError("source construction")):
                with self.assertRaises(SystemExit):
                    main(argv)
        with patch.dict(os.environ, {}, clear=True):
            for port in (0, 1, 65535):
                self.assertEqual(parse_args(["--port", str(port)]).port, port)

    def test_site_default_precedence_and_explicit_legacy_mode(self):
        from v8std_mcp_server import parse_args
        with patch.dict(os.environ, {}, clear=True):
            args = parse_args([])
            self.assertEqual(getattr(args, "site_url", None), "https://v8std.ru/")
            self.assertEqual(args.transport, "streamable-http")
            self.assertEqual((args.host, args.port), ("127.0.0.1", 8765))
            self.assertIsNone(parse_args(["--pages", "/fixture/pages.jsonl"]).site_url)
            self.assertIsNone(parse_args(["--index-url", "http://localhost/pages.jsonl"]).site_url)
        with patch.dict(os.environ, {"V8STD_MCP_SITE_URL": LOCAL}):
            self.assertEqual(parse_args([]).site_url, LOCAL)
            self.assertEqual(parse_args(["--site-url", "https://example.org/kb"]).site_url,
                             "https://example.org/kb/")

    def test_ambiguous_or_empty_configuration_fails_without_loading(self):
        from v8std_mcp_server import main
        for argv in (["--site-url", ""], ["--site-url", LOCAL, "--index-url", "http://secret.invalid/x"],
                     ["--site-url", LOCAL, "--pages", "private-path"], ["--refresh-seconds", "-1"]):
            with self.subTest(argv=argv), patch.dict(os.environ, {}, clear=True), \
                 contextlib.redirect_stderr(io.StringIO()) as stderr, \
                 patch("v8std_mcp_server.V8StdIndex.load", side_effect=AssertionError("source load")):
                with self.assertRaises(SystemExit):
                    main(argv)
                self.assertNotIn("private-path", stderr.getvalue())
                self.assertNotIn("secret.invalid", stderr.getvalue())


def frozen_real_index(maximum=4000):
    from v8std_mcp_index import V8StdIndex
    return V8StdIndex.from_validated_bytes((ROOT / "docs/ai/pages.jsonl").read_bytes(),
        (ROOT / "docs/ai/search-vectors.jsonl").read_bytes(), max_snippet_chars=maximum)


class FrozenSnippetCompatibility(snippet_compat.SnippetRetrievalTests):
    @classmethod
    def setUpClass(cls):
        cls.index = frozen_real_index()


class FrozenLargeSnippetCompatibility(snippet_compat.LargeSnippetTests):
    @classmethod
    def setUpClass(cls):
        cls.default = frozen_real_index()
        cls.large = frozen_real_index(32000)


class StdioProcess:
    def __init__(self, site, cache, *extra):
        self.process = subprocess.Popen([sys.executable, str(ROOT / "scripts/v8std_mcp_server.py"),
            "--transport", "stdio", "--site-url", site, "--cache-dir", str(cache),
            "--refresh-seconds", "0", *extra], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env={**os.environ, "NO_PROXY": "127.0.0.1,localhost"})
        self.lines = queue.Queue()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        self.number = 0

    def _read(self):
        for line in self.process.stdout:
            self.lines.put(line)

    def call(self, method, params=None):
        self.number += 1
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.number,
                                            "method": method, "params": params or {}}) + "\n")
        self.process.stdin.flush()
        result = json.loads(self.lines.get(timeout=5))
        if result.get("id") != self.number:
            raise AssertionError(result)
        return result

    def notify(self, method, params=None):
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method,
                                            "params": params or {}}) + "\n")
        self.process.stdin.flush()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(3)
            raise
        self.thread.join(1)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


@contextlib.contextmanager
def measured_output_pipe():
    """Measure the actual test pipe to EAGAIN, then hand its drained writer to the child."""
    read_fd, write_fd = os.pipe()
    with os.fdopen(read_fd, "rb", buffering=0) as output, os.fdopen(write_fd, "wb", buffering=0) as writer:
        os.set_blocking(write_fd, False)
        capacity = 0
        try:
            while capacity < 16 * 1024 * 1024:
                capacity += os.write(write_fd, b"x" * 65536)
            raise AssertionError("test pipe did not reach backpressure")
        except BlockingIOError:
            pass
        remaining = capacity
        while remaining:
            remaining -= len(os.read(read_fd, remaining))
        os.set_blocking(write_fd, True)
        yield output, writer, capacity


class WireTests(unittest.TestCase):
    def test_stdio_large_response_drained_and_backpressured_shutdown_cleans_workers(self):
        from tests.test_v8std_mcp_snapshots import Source
        from v8std_mcp_snapshots import SnapshotStore
        source = Source()
        payload = "\U0001f600" * 12000
        page = fixture.page_fixture()
        page["body_markdown"] = payload
        vectors = fixture.vector_fixtures()
        vectors[1]["text_sha256"] = fixture.sha256(payload.encode())
        files = fixture.corpus_files(pages=[page], vectors=vectors)
        source.archive, source.manifest = fixture.snapshot_fixture(files=fixture.with_metadata(files))
        try:
            for shutdown in ("drained-eof", "eof", "sigterm"):
                with self.subTest(shutdown=shutdown), tempfile.TemporaryDirectory() as directory, \
                     measured_output_pipe() as (output, writer, capacity):
                    source.fault = None
                    SnapshotStore(source.url, Path(directory)).refresh()
                    source.requested.clear()
                    source.release.clear()
                    source.fault = "headers"
                    process = subprocess.Popen([sys.executable, str(ROOT / "scripts/v8std_mcp_server.py"),
                        "--transport", "stdio", "--site-url", source.url, "--cache-dir", directory,
                        "--refresh-seconds", "0"], stdin=subprocess.PIPE, stdout=writer,
                        stderr=subprocess.PIPE, bufsize=0, start_new_session=True)
                    writer.close()
                    number, buffer = 0, bytearray()

                    def send(method, params):
                        nonlocal number
                        number += 1
                        process.stdin.write((json.dumps({"jsonrpc": "2.0", "id": number,
                            "method": method, "params": params}) + "\n").encode())

                    def response():
                        deadline = time.monotonic() + 8
                        while b"\n" not in buffer:
                            remaining = deadline - time.monotonic()
                            self.assertGreater(remaining, 0, "protocol response timeout")
                            self.assertTrue(select.select([output], [], [], remaining)[0])
                            block = os.read(output.fileno(), 65536)
                            self.assertTrue(block, "unexpected protocol EOF")
                            buffer.extend(block)
                        end = buffer.index(b"\n") + 1
                        line = bytes(buffer[:end])
                        del buffer[:end]
                        result = json.loads(line)
                        self.assertEqual(result["id"], number, "stdout must contain only SDK frames")
                        return result, len(line)

                    try:
                        send("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                            "clientInfo": {"name": "backpressure", "version": "1"}})
                        self.assertIn("serverInfo", response()[0]["result"])
                        process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
                        self.assertTrue(source.requested.wait(5))
                        # Warm-cache generation is ready before the blocked refresh.
                        send("tools/call", {"name": "v8std_search", "arguments": {"query": "std437"}})
                        self.assertFalse(response()[0]["result"].get("isError", False))
                        children = [int(row.split(None, 2)[0])
                            for row in subprocess.check_output(["ps", "-axo", "pid=,ppid=,command="], text=True).splitlines()
                            if row.split(None, 2)[1] == str(process.pid) and "spawn_main" in row]
                        self.assertTrue(children, "exercise shutdown with an active spawn worker")
                        arguments = {"name": "v8std_get_page", "arguments": {"id_or_alias_or_url": "std437"}}
                        send("tools/call", arguments)
                        reply, encoded_bytes = response()
                        result = reply["result"]
                        self.assertFalse(result.get("isError", False))
                        self.assertEqual(result["structuredContent"]["page"]["body_markdown"], payload)
                        self.assertFalse(result["structuredContent"]["page"]["body_truncated"])
                        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
                        self.assertGreater(encoded_bytes, capacity + 64,
                                           "real SDK tool frame must exceed the measured pipe capacity")
                        if shutdown != "drained-eof":
                            send("tools/call", arguments)
                            self.assertTrue(select.select([output], [], [], 5)[0])
                            # Drain only 64 bytes of the same measured response; the rest cannot fit.
                            self.assertTrue(os.read(output.fileno(), 64).startswith(b'{"jsonrpc"'))
                            time.sleep(.1)
                        started = time.monotonic()
                        if shutdown == "sigterm":
                            process.send_signal(signal.SIGTERM)
                        else:
                            process.stdin.close()
                        try:
                            process.wait(3)
                        except subprocess.TimeoutExpired:
                            self.fail("backpressured tool response prevented bounded " + shutdown + " shutdown")
                        self.assertEqual(process.returncode, 0)
                        self.assertLess(time.monotonic() - started, 3)
                        for pid in children:
                            with self.assertRaises(ProcessLookupError):
                                os.kill(pid, 0)
                    finally:
                        source.release.set()
                        if process.poll() is None:
                            # Only this test's new session; no worker orphan on RED.
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(3)
                        for stream in (process.stdin, process.stderr):
                            stream.close()
        finally:
            source.close()

    def test_stdio_initialize_not_ready_eof_and_sigterm_clean_workers(self):
        from tests.test_v8std_mcp_snapshots import Source
        from tests.test_v8std_mcp_tools_only import initialize, assert_resources_disabled
        source = Source()
        source.fault = "headers"
        try:
            for shutdown in ("eof", "sigterm"):
                with self.subTest(shutdown=shutdown), tempfile.TemporaryDirectory() as directory:
                    client = StdioProcess(source.url, Path(directory))
                    try:
                        started = time.monotonic()
                        init = initialize(client, "task3-fixture")
                        self.assertEqual(init["result"]["serverInfo"]["name"], "v8std")
                        self.assertLess(time.monotonic() - started, 3)
                        self.assertEqual(len(client.call("tools/list")["result"]["tools"]), 5)
                        self.assertNotIn("resources", init["result"]["capabilities"])
                        assert_resources_disabled(self, client)
                        result = client.call("tools/call", {"name": "v8std_search", "arguments": {"query": "std437"}})
                        self.assertTrue(result["result"]["isError"])
                        self.assertIn("INDEX_NOT_READY", str(result))
                        self.assertTrue(source.requested.wait(3))
                        child_rows = subprocess.check_output(["ps", "-axo", "pid=,ppid=,command="], text=True)
                        children = [int(row.split(None, 2)[0]) for row in child_rows.splitlines()
                                    if row.split(None, 2)[1] == str(client.process.pid)
                                    and "spawn_main" in row]
                        self.assertTrue(children)
                        started = time.monotonic()
                        if shutdown == "eof":
                            client.process.stdin.close()
                        else:
                            client.process.send_signal(signal.SIGTERM)
                        self.assertEqual(client.process.wait(4), 0)
                        self.assertLess(time.monotonic() - started, 3)
                        for pid in children:
                            with self.assertRaises(ProcessLookupError):
                                os.kill(pid, 0)
                        self.assertTrue(client.lines.empty(), "stdout contains non-protocol output")
                    finally:
                        client.close()
        finally:
            source.close()

    def test_loopback_http_slow_bootstrap_then_two_agents_with_tools_only(self):
        import httpx
        from tests.test_v8std_mcp_snapshots import Source
        from tests.test_v8std_mcp_tools_only import HttpRpc, initialize, assert_resources_disabled, assert_tool_catalog
        source = Source()
        source.fault = "headers"
        try:
            with tempfile.TemporaryDirectory() as directory, socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
                reservation.close()
                process = subprocess.Popen([sys.executable, str(ROOT / "scripts/v8std_mcp_server.py"),
                    "--site-url", source.url, "--cache-dir", directory, "--port", str(port),
                    "--refresh-seconds", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=3, trust_env=False) as client:
                        deadline = time.monotonic() + 5
                        while True:
                            try:
                                live = client.get("/livez")
                                break
                            except httpx.ConnectError:
                                if time.monotonic() > deadline:
                                    self.fail("HTTP startup timeout")
                                time.sleep(.02)
                        self.assertEqual(live.status_code, 200)
                        self.assertEqual(client.get("/healthz").status_code, 503)
                        agents = []
                        for name in ("agent-one", "agent-two"):
                            agent = HttpRpc(client)
                            agents.append(agent)
                            initialized = initialize(agent, name)
                            self.assertIn("serverInfo", initialized["result"])
                            self.assertNotIn("resources", initialized["result"]["capabilities"])
                            assert_tool_catalog(self, agent)
                            assert_resources_disabled(self, agent)
                        self.assertIn("INDEX_NOT_READY", str(agents[0].call("tools/call", {"name": "v8std_search",
                                                                "arguments": {"query": "std437"}})))
                        source.release.set()
                        deadline = time.monotonic() + 8
                        while client.get("/healthz").status_code != 200:
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.025)
                        for agent in agents:
                            self.assertFalse(agent.call("tools/call", {"name": "v8std_get_page",
                                "arguments": {"id_or_alias_or_url": "std437"}})["result"].get("isError", False))
                            assert_resources_disabled(self, agent)
                        self.assertEqual(client.get("/version").json()["api"], "v2")
                        self.assertEqual(client.get("/version").json()["api_profiles"], ["legacy-tools"])
                finally:
                    process.terminate()
                    process.communicate(timeout=5)
        finally:
            source.close()


if __name__ == "__main__":
    unittest.main()
