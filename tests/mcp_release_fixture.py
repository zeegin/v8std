"""Disposable real runtime/proxy processes for host-controller fault injection.

This adapter replaces Docker/gh/nginx command boundaries, NOT runtime health or
MCP results. It is not positive registry, signature or native systemd evidence.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v8std_mcp_release as release


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
        except ProcessLookupError:
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
                    self.wfile.write(data)
                except OSError:
                    self.send_error(404)
                return
            connection = None
            try:
                target = json.loads((root / "edge.json").read_text())["port"]
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

        do_GET = do_POST = dispatch
    ThreadingHTTPServer(("127.0.0.1", port), Edge).serve_forever()


if __name__ == "__main__":
    mode, directory, *args = sys.argv[1:]
    directory = Path(directory)
    if mode == "runtime":
        from v8std_mcp_runtime import SnapshotIndex
        from v8std_mcp_server import build_server
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
