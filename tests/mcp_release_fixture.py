"""Disposable real runtime/proxy processes for host-controller fault injection.

This adapter replaces Docker/gh/nginx command boundaries, NOT runtime health or
MCP results. It is not positive registry, signature or native systemd evidence.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delivery.vps.v8std_mcp_release as release

LEGACY_SHA = "b7bef11e145a188b30e7a7b17df2be4cb1acbd0c"


def prepare_legacy(root, files):
    """Pinned historical sources, never mutable main; tiny data in fault matrix."""
    app = root / "legacy/app"
    names = ["scripts/v8std_mcp_server.py", "scripts/v8std_mcp_index.py",
             "scripts/v8std_retrieval_rules.py", "retrieval-rules.yml"]
    export = Path("/legacy-source")  # Only the disposable Docker test mounts this.
    if not export.is_dir():
        tracked = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", LEGACY_SHA], cwd=ROOT).decode().splitlines()
        names[-1] = next(x for x in tracked if x.endswith("retrieval-rules.yml"))
    entries = {}
    def entry(raw, mode=0o644):
        return {"sha256": release.digest(raw), "mode": mode, "uid": os.getuid(), "gid": os.getgid()}
    for name in names:
        raw = (export / name).read_bytes() if export.is_dir() else subprocess.check_output(["git", "show", LEGACY_SHA + ":" + name], cwd=ROOT)
        release.atomic(app / name, raw, mode=0o644)
        entries[name] = entry(raw)
    raw = b"disposable fixture uses the local locked dependencies, not a native backup proof\n"
    release.atomic(app / "venv/pyvenv.cfg", raw)
    entries["venv/pyvenv.cfg"] = entry(raw)
    entries["venv/bin/python"] = {"link": str(release.LEGACY_PYTHON)}
    cache = {}
    for name, raw in files.items():
        release.atomic(root / "legacy/cache" / name, raw)
        os.utime(root / "legacy/cache" / name, (1, 1))
        cache[name] = entry(raw)
    unit = b"original-unit-with-default-remote-urls-and-3600-refresh\n"
    upstream = release.canonical_json({"port": release.read_record(root / "legacy-port.json")["port"]})
    release.atomic(root / "legacy/unit", unit)
    release.atomic(root / "legacy/upstream", upstream)
    directories = {"app": {}, "cache": {".": {"mode": 0o755, "uid": os.getuid(), "gid": os.getgid()}}}
    for name in entries:
        for parent in Path(name).parents:
            directories["app"][str(parent)] = {"mode": 0o755, "uid": os.getuid(), "gid": os.getgid()}
    saved = {"schema_version": 1, "app": entries, "cache": cache, "directories": directories, "unit": entry(unit),
             "upstream": entry(upstream), "interpreter_sha256": "f" * 64}
    # Test temp files are owned by the test user. Host validation is independently
    # exercised under Linux root by Docker; no sudo/host permissions changes.
    saved["unit"].update(uid=0, gid=0)
    saved["upstream"].update(uid=0, gid=0)
    release.write_json(root / "legacy/manifest.json", saved)
    return release.digest((root / "legacy/manifest.json").read_bytes())


class ProcessAdapter(release.HostAdapter):
    def __init__(self, root, policy, fault=""):
        super().__init__(root, policy)
        self.fault = fault
        self.children = []

    def record(self, operation, record=None):
        with (self.root / "calls.jsonl").open("a") as stream:
            stream.write(json.dumps({"operation": operation, "release_id": (record or {}).get("release_id")}) + "\n")
        if operation in self.fault.split(","):
            raise release.ReleaseError("injected_" + operation)

    def verify(self, envelope, deadline):
        self.record("verify", envelope)
        return {envelope["image_digest"]: next(iter(release.INDEX_TYPES)),
                envelope["platform_digest"]: next(iter(release.MANIFEST_TYPES))}

    def capacity(self, deadline):
        self.record("capacity")

    def pull(self, record, deadline):
        self.record("pull", record)

    def inspect(self, record, deadline):
        path = self.root / "processes" / (record["release_id"] + ".json")
        if not path.exists():
            return None
        state = json.loads(path.read_text())
        release.require(state["record"]["envelope_hash"] == record["envelope_hash"], "ownership")
        try:
            os.kill(state["pid"], 0)
            # An orphan zombie on Linux is no longer a running endpoint.
            proc = Path(f"/proc/{state['pid']}/stat")
            if proc.exists():
                running = proc.read_text().split()[2] != "Z"
            else:
                status = subprocess.run(["ps", "-p", str(state["pid"]), "-o", "stat="], capture_output=True).stdout.strip()
                running = bool(status) and not status.startswith(b"Z")
        except (ProcessLookupError, FileNotFoundError):
            # Linux can reap the process between exists() and reading /proc/stat.
            running = False
        return {"State": {"Running": running}, "pid": state["pid"]}

    def start(self, record, deadline):
        self.record("start", record)
        info = self.inspect(record, deadline)
        if info and info["State"]["Running"]:
            return
        directory = self.root / "slots" / record["release_id"]
        config = self.config(record)
        arguments = [sys.executable, "-m", "tests.mcp_release_fixture", "runtime", str(directory),
                     str(record["port"]), config["site_url"], record["runtime_source_sha"],
                     "blocked" if self.fault == "ready" and record["release_id"] != "predecessor" else "normal"]
        with (directory / "runtime.log").open("ab") as log:
            process = subprocess.Popen(arguments, cwd=ROOT, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, start_new_session=True)
        self.children.append(process)
        release.write_json(self.root / "processes" / (record["release_id"] + ".json"),
                           {"pid": process.pid, "record": record})
        if self.fault == "crash_after_start" and record["release_id"] != "predecessor":
            os._exit(93)
        if self.fault == "kill_active_after_start":
            os.kill(os.getpid(), signal.SIGKILL)

    def hold(self, record, token, deadline, manifest=None):
        return super().hold(record, token, min(deadline, time.monotonic() + 5), manifest)

    def switch(self, record, deadline):
        self.record("switch_old" if record["release_id"] == "predecessor" else "switch", record)
        release.write_json(self.root / "edge.json", {"port": record["port"]})
        if self.fault == "crash_after_switch" and record["release_id"] != "predecessor":
            os._exit(92)

    def check(self, record, deadline, *, public=False):
        operation = ("public_old" if record["release_id"] == "predecessor" else "public") if public else "smoke"
        self.record(operation, record)
        # For the public failure case, stop the actual candidate. The edge must
        # fail a real HTTP request before rollback can be claimed.
        if "public_dead" in self.fault.split(",") and public and record["release_id"] != "predecessor":
            self.stop(record, deadline)
        result = super().check(record, min(deadline, time.monotonic() + 5), public=public)
        if self.fault == "kill_active_after_smoke" and public:
            os.kill(os.getpid(), signal.SIGKILL)
        return result

    def resume(self, record, deadline):
        if self.fault == "kill_active_before_resume":
            os.kill(os.getpid(), signal.SIGKILL)
        return super().resume(record, deadline)

    def stop(self, record, deadline):
        self.record("stop", record)
        info = self.inspect(record, deadline)
        if info and info["State"]["Running"]:
            os.kill(info["pid"], signal.SIGTERM)
            while self.inspect(record, deadline)["State"]["Running"]:
                release.remaining(deadline)
                time.sleep(.025)
        try:
            os.waitpid(info["pid"], os.WNOHANG)
        except (ChildProcessError, TypeError):
            pass


class BootstrapAdapter(ProcessAdapter):
    def observe(self):
        live = [p.stem for p in (self.root / "processes").glob("*.json")
                if self.inspect(release.read_record(p)["record"], time.monotonic() + 2)["State"]["Running"]]
        records = self.root / "releases/release-1.json"
        window = release.read_record(records)["window"] if records.exists() else self.bootstrap_window({})
        if window["mode"] == "stop-start":
            release.require(len(live) <= 1, "fixture_overlap")
        with (self.root / "observations.jsonl").open("a") as stream:
            stream.write(json.dumps({"live_runtimes": live}) + "\n")

    def bootstrap_window(self, envelope):
        return release.read_record(self.root / "window.json")

    def bootstrap_backup(self, window, deadline, *, current=False):
        from unittest.mock import patch
        with patch.object(release, "trusted_path"):
            saved = release.backup_inventory(self.root, window, deadline)
        if current:
            self.legacy_files(saved, deadline, restore=False)
        return saved

    def bootstrap_capacity(self, window, envelope, deadline, *, after_stop=False):
        self.record("capacity_after_stop" if after_stop else "capacity")

    def bootstrap_prepared(self, candidate, deadline):
        self.record("prepared")
        self.manifest(candidate)

    def arm_bootstrap_guard(self, deadline):
        self.record("guard")
        # A separate session/process periodically acquires the actual controller
        # lock. Survives killed caller/worker, not a fake successful adapter ack.
        state = self.root / "guard.json"
        if state.exists():
            return
        with (self.root / "guard.log").open("ab") as log:
            process = subprocess.Popen([sys.executable, "-m", "tests.mcp_release_fixture", "guard",
                str(self.root)], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, cwd=ROOT)
        release.write_json(state, {"pid": process.pid})

    def legacy_record(self):
        return {"release_id": "legacy", "envelope_hash": LEGACY_SHA,
                "port": release.read_record(self.root / "legacy-port.json")["port"]}

    def legacy_stop(self, deadline):
        self.record("legacy_stop")
        self.stop(self.legacy_record(), deadline)
        self.observe()
        if self.fault == "kill_after_legacy_stop":
            os.kill(os.getpid(), signal.SIGKILL)

    def legacy_restore(self, window, deadline):
        self.record("legacy_restore")
        saved = self.bootstrap_backup(window, deadline)
        self.legacy_files(saved, deadline, restore=True)
        for name, target in (("unit", self.root / "legacy-unit"), ("upstream", self.root / "edge.json")):
            entry = saved[name] | {"uid": os.getuid(), "gid": os.getgid()}
            release.restore_file(self.root / "legacy" / name, target, entry, deadline)

    def legacy_start(self, deadline):
        self.record("legacy_start")
        release.require(release.legacy_start_allowed(self.root), "legacy_fenced")
        for path in (self.root / "processes").glob("*.json"):
            if path.stem != "legacy":
                release.require(not self.inspect(release.read_record(path)["record"], deadline)["State"]["Running"], "fixture_overlap")
        record = self.legacy_record()
        info = self.inspect(record, deadline)
        if info and info["State"]["Running"]:
            return
        with (self.root / "legacy.log").open("ab") as log:
            process = subprocess.Popen([sys.executable, "-m", "tests.mcp_release_fixture", "legacy",
                str(self.root), str(record["port"])], cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, start_new_session=True)
        self.children.append(process)
        release.write_json(self.root / "processes/legacy.json", {"pid": process.pid, "record": record})
        self.observe()

    def legacy_check(self, window, deadline, *, public=False):
        self.record("legacy_public" if public else "legacy_local")
        # Run the real production hash + MCP checks, only translate loopback port.
        from unittest.mock import patch
        original = release.http
        def http(url, *args, **kwargs):
            return original(url.replace("127.0.0.1:8765", "127.0.0.1:" + str(self.legacy_record()["port"])), *args, **kwargs)
        with patch.object(release, "http", http):
            return super().legacy_check(window, deadline, public=public)

    def legacy_identity(self, deadline):
        record = release.read_record(self.root / "processes/legacy.json")
        release.require(self.inspect(record["record"], deadline)["State"]["Running"], "legacy_process")
        observed = release.read_record(self.root / "legacy-observed.json")
        saved = release.read_record(self.root / "legacy/manifest.json")
        release.require(observed["pid"] == record["pid"] and all(observed["sources"][name] ==
            saved["app"]["scripts/" + name]["sha256"] for name in observed["sources"]), "legacy_process")

    def start(self, record, deadline):
        if self.bootstrap_window(record)["mode"] == "stop-start":
            old = self.inspect(self.legacy_record(), deadline)
            release.require(not old or not old["State"]["Running"], "fixture_overlap")
        super().start(record, deadline)
        self.observe()
        if self.fault == "kill_after_candidate_start":
            os.kill(os.getpid(), signal.SIGKILL)

    def switch(self, record, deadline):
        super().switch(record, deadline)
        if self.fault == "kill_after_switch":
            os.kill(os.getpid(), signal.SIGKILL)


def bootstrap_environment(root):
    from contextlib import ExitStack
    from unittest.mock import patch
    stack = ExitStack()
    for name, value in (("LEGACY_APP", root / "restored-app"), ("LEGACY_DATA", root / "restored-cache")):
        stack.enter_context(patch.object(release, name, value))
    return stack


def run_legacy(root, port):
    # Actual immutable historical modules, default URLs/default refresh3600.
    # RLIMIT_DATA applies to this disposable process only; native cgroup evidence
    # is separate. Do not inherit a monkeypatch of the new server or index.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_DATA, (384 * 1024 * 1024, 384 * 1024 * 1024))
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / "restored-app/scripts"))
    for name in ("v8std_mcp_index", "v8std_retrieval_rules", "v8std_mcp_server"):
        sys.modules.pop(name, None)
    import v8std_mcp_index as old_index
    from v8std_mcp_server import build_server
    def trap(*args, **kwargs):
        with (root / "legacy-network.jsonl").open("a") as stream:
            stream.write('"forbidden-network-attempt"\n')
        raise OSError("network forbidden in legacy regression")
    old_index.urlopen = trap
    index = old_index.V8StdIndex(cache_dir=root / "restored-cache")
    index.load()
    release.write_json(root / "legacy-observed.json", {"source_sha": LEGACY_SHA, "pid": os.getpid(),
        "sources": {name: release.file_hash(root / "restored-app/scripts" / name, time.monotonic() + 2)
                    for name in ("v8std_mcp_server.py", "v8std_mcp_index.py", "v8std_retrieval_rules.py")},
        "server_sha256": release.file_hash(root / "restored-app/scripts/v8std_mcp_server.py", time.monotonic() + 2),
        "refresh_seconds": index.refresh_seconds, "index_url": index.index_url, "vectors_url": index.vectors_url})
    build_server(index, host="127.0.0.1", port=port, mcp_path="/mcp", allowed_hosts=["127.0.0.1:*"],
                 allowed_origins=[]).run(transport="streamable-http")


class CrashController(release.Controller):
    def save(self, journal, state=None, intent=None):
        super().save(journal, state, intent)
        if self.adapter.fault == "crash_" + journal["state"] or self.adapter.fault == "intent_" + journal["intent"]:
            os._exit(91)


def serve_edge(root, port):
    class Edge(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def dispatch(self):
            if self.path.startswith("/indexes/v1/"):
                parts = self.path.split("/")
                if len(parts) != 6 or not release.matches(release.HEX, parts[3]) or parts[4] != "snapshot.tar.gz":
                    # split('/indexes/v1/hash/snapshot.tar.gz') has five entries.
                    if len(parts) != 5 or not release.matches(release.HEX, parts[3]) or parts[4] != "snapshot.tar.gz":
                        self.send_error(404)
                        return
                try:
                    data = (root / "static" / parts[3] / "snapshot.tar.gz").read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    if self.command != "HEAD":
                        self.wfile.write(data)
                except OSError:
                    self.send_error(404)
                return
            connection = None
            try:
                target = json.loads((root / "edge.json").read_text())["port"]
                if target is None:
                    self.send_response(503)
                    self.send_header("Retry-After", "1")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                connection = http.client.HTTPConnection("127.0.0.1", target, timeout=3)
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                connection.request(self.command, self.path, body, dict(self.headers))
                response = connection.getresponse()
                data = response.read()
                self.send_response(response.status)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(data)
            except OSError:
                self.send_error(503)
            finally:
                if connection:
                    connection.close()

        do_GET = do_POST = do_HEAD = dispatch
    ThreadingHTTPServer(("127.0.0.1", port), Edge).serve_forever()


if __name__ == "__main__":
    mode, directory, *args = sys.argv[1:]
    directory = Path(directory)
    if mode == "legacy":
        run_legacy(directory, int(args[0]))
    elif mode == "guard":
        # Release the test gate only when assertions have inspected the crash
        # boundary. Loss-of-caller test leaves gate open from the beginning.
        with bootstrap_environment(directory):
            adapter = BootstrapAdapter(directory, release.read_record(directory / "policy.json"))
            while True:
                if not (directory / "guard-paused").exists():
                    try:
                        release.Controller(directory, adapter).recover()
                    except release.ReleaseError:
                        pass
                time.sleep(.2)
    elif mode.startswith("bootstrap"):
        from unittest.mock import patch
        fault = args[0] if args else ""
        with bootstrap_environment(directory):
            adapter = BootstrapAdapter(directory, release.read_record(directory / "policy.json"), fault)
            class BootstrapCrash(release.BootstrapController):
                def save(self, journal, state=None, intent=None):
                    if fault == "accept_persist_failure" and state == "COMMITTED":
                        raise OSError("injected acceptance persistence failure")
                    super().save(journal, state, intent)
                    if fault == "kill_" + journal["intent"] or fault == "kill_" + journal["state"]:
                        os.kill(os.getpid(), signal.SIGKILL)
            controller = BootstrapCrash(directory, adapter)
            original = release.write_json
            require = release.require
            def fixture_authority(condition, code):
                return require(True if code == "host_privilege" else condition, code)
            replace = os.replace
            def replace_with_fault(source, target):
                if "kill_during_restore" in fault.split(",") and Path(target) == directory / "restored-app/scripts/v8std_mcp_server.py":
                    os.kill(os.getpid(), signal.SIGKILL)
                return replace(source, target)
            def write(path, value, **kwargs):
                if fault in {"active_persist_failure", "kill_after_active"} and path == directory / "active.json":
                    if fault == "active_persist_failure":
                        raise OSError("injected active pointer failure")
                    original(path, value, **kwargs)
                    os.kill(os.getpid(), signal.SIGKILL)
                return original(path, value, **kwargs)
            try:
                with patch.object(release, "write_json", write), patch.object(release.os, "replace", replace_with_fault), \
                     patch.object(release, "schedule"), \
                     patch.object(release, "ROOT", directory), patch.object(release, "trusted_policy", return_value=adapter.policy), \
                     patch.object(release, "HostAdapter", return_value=adapter), patch.object(release, "require", fixture_authority), \
                     patch.object(release, "BootstrapController", BootstrapCrash):
                    if mode == "bootstrap":
                        read_fd, write_fd = os.pipe()
                        os.write(write_fd, (directory / "envelope.json").read_bytes() + b"\n")
                        os.close(write_fd)
                        with os.fdopen(read_fd) as input_stream, patch.object(sys, "stdin", input_stream), \
                             patch.object(sys, "argv", ["fixture", "bootstrap"]):
                            submitted = release.main()
                        with patch.object(sys, "argv", ["fixture", "_bootstrap"]):
                            result = release.main() if submitted["state"] == "RECEIVED" else submitted
                    elif mode == "bootstrap-legacy-start":
                        with patch.object(sys, "argv", ["fixture", "_legacy-allowed"]):
                            release.main()
                        adapter.legacy_start(time.monotonic() + 5)
                        result = {"state": "LEGACY_STARTED"}
                    else:
                        with patch.object(sys, "argv", ["fixture", "bootstrap-recover"]):
                            result = release.main()
                print(json.dumps(result))
            except Exception as error:
                print(json.dumps({"state": "REJECTED", "error_code": getattr(error, "code", "host_failure")}))
    elif mode == "runtime":
        from runtime.v8std_mcp_runtime import SnapshotIndex
        from runtime.v8std_mcp_server import build_server
        port, site_url, sha, behavior = args
        index = SnapshotIndex(site_url=site_url, cache_dir=directory / "cache", runtime_sha=sha,
                              refresh_seconds=1, release_control=directory / "control" / "control.json")
        if behavior == "blocked":
            from tests.test_v8std_mcp_snapshots import blocking_build
            index.coordinator.build = blocking_build
        build_server(index, host="127.0.0.1", port=int(port), mcp_path="/mcp",
                     allowed_hosts=["127.0.0.1:*"], allowed_origins=[]).run(transport="streamable-http")
    elif mode == "edge":
        serve_edge(directory, int(args[0]))
    else:
        adapter = ProcessAdapter(directory, json.loads((directory / "policy.json").read_text()), args[0] if args else "")
        controller = CrashController(directory, adapter)
        if mode == "queued_expired":
            # Execute the actual internal CLI worker against owned local state;
            # replace only host authorization/adapters and wall clock, not logic.
            from unittest.mock import patch
            now = time.time()
            with patch.object(release, "ROOT", directory), patch.object(release, "trusted_policy", return_value=adapter.policy), \
                 patch.object(release, "HostAdapter", return_value=adapter), patch.object(os, "geteuid", return_value=0), \
                 patch.object(sys, "argv", ["fixture", "_deploy"]), patch.object(time, "time", return_value=now + 130):
                result = release.main()
        else:
            result = controller.deploy((directory / "envelope.json").read_bytes()) if mode == "deploy" else controller.recover()
        print(json.dumps(result))
