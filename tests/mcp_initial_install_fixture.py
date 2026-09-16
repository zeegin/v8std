"""Local process fixture; substitutes OS/gh/Docker/systemd, never MCP smoke.

The inventory uses Docker-shaped records backed by real runtime processes.
Missing, stopped, foreign and failed inspection are distinct outcomes.
No Docker daemon, registry or privileged host is touched.
"""
from contextlib import ExitStack, contextmanager
import http.client
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from tests.mcp_release_fixture import ProcessAdapter, ROOT, release
from tests.test_v8std_mcp_release import envelope, port
from tests.test_v8std_mcp_snapshots import Source

HostAdapter = release.HostAdapter


class InitialAdapter(ProcessAdapter):
    def point(self, name):
        if self.fault == "kill_" + name:
            os.kill(os.getpid(), signal.SIGKILL)
        if name in self.fault.split(","):
            raise release.ReleaseError("injected_" + name)

    def command(self, argv, deadline, **kwargs):
        release.remaining(deadline)
        argv = [str(x) for x in argv]
        self.record("command", {"release_id": argv[0]})
        if argv[:2] == ["systemctl", "show"]:
            return (b"LoadState=loaded\nActiveState=active\nSubState=running\nMainPID=123\nFragmentPath=/fixture/unit\n"
                    if (self.root / "legacy-unit-present").exists() else
                    b"LoadState=not-found\nActiveState=inactive\nSubState=dead\nMainPID=0\nFragmentPath=\n")
        if argv[:2] == ["gh", "attestation"]:
            self.point("attestation")
            return b"[]"
        if argv[:2] == ["gh", "api"]:
            sha = argv[2].split("/compare/")[1].split("...")[0]
            return release.canonical_json({"status": "diverged" if self.fault == "ancestry" else "ahead",
                                            "merge_base_commit": {"sha": sha}})
        if argv[:4] == ["docker", "buildx", "imagetools", "inspect"]:
            name = "index.json" if argv[-1].endswith(self.image_digest) else "child.json"
            raw = (self.root / name).read_bytes()
            return raw + b"corrupt" if self.fault == "descriptor" else raw
        if argv[:3] == ["docker", "image", "inspect"]:
            env = release.read_record(self.root / "envelope.json")
            self.point("image_missing")
            return json.dumps([{"Id": "sha256:" + "c" * 64, "Os": "linux", "Architecture": "amd64",
                "Config": {"Labels": {"org.opencontainers.image.revision": env["runtime_source_sha"]}}}]).encode()
        if argv[:3] == ["docker", "ps", "-a"]:
            return "".join(name + "\n" for name in self.inventory()).encode()
        if argv[:2] == ["docker", "inspect"]:
            name = argv[-1]
            if self.fault == "inspect_error":
                # Real run() reports failed inspect as command_failed; a
                # successful ps still proves that this container is not absent.
                raise release.ReleaseError("command_failed")
            inventory = self.inventory()
            release.require(name in inventory, "command_failed")
            return json.dumps([inventory[name]]).encode()
        if argv == ["nginx", "-t"]:
            self.point("nginx_test")
            return b""
        if argv == ["nginx", "-s", "reload"]:
            self.point("nginx_reload")
            data = Path(self.policy["nginx_include"]).read_bytes()
            port_value = None if data == b"server 127.0.0.1:9 down;\n" else int(re.search(rb":(\d+) ", data)[1])
            release.write_json(self.root / "edge.json", {"port": port_value})
            return b""
        if argv[0] == "systemd-run":
            self.point("schedule_failure")
            return b""
        raise AssertionError("unexpected host command: " + repr(argv))

    @property
    def image_digest(self):
        return "sha256:" + release.digest((self.root / "index.json").read_bytes())

    def inventory(self):
        values = {}
        for path in (self.root / "processes").glob("*.json"):
            state = release.read_record(path)
            record = state["record"]
            running = ProcessAdapter.inspect(self, record, time.monotonic() + 2)["State"]["Running"]
            values[record["name"]] = {"Name": "/" + record["name"], "State": {"Running": running},
                "Config": {"Image": release.IMAGE + "@" + record["platform_digest"], "Labels": {
                    "pro.v8std.release": record["release_id"], "pro.v8std.envelope": record["envelope_hash"],
                    "org.opencontainers.image.revision": record["runtime_source_sha"]}}, "Image": "sha256:" + "c" * 64,
                "pid": state["pid"]}
        foreign = self.root / "foreign-containers.json"
        if foreign.exists():
            values.update(release.read_record(foreign))
        return values

    @contextmanager
    def boundaries(self):
        # Real permission rejection is tested separately. Positive unprivileged
        # fixtures translate only ownership/OS roots, not authorization content.
        original = release.read_file
        def read_file(path, *args, **kwargs):
            if path == Path("/proc/meminfo"):
                return b"MemAvailable: 1048576 kB\n"
            return original(path, *args, **kwargs)
        with ExitStack() as stack:
            for name, value in (("INITIAL_INSTALL_AUTH", self.root / "authorization.json"),
                                ("LEGACY_APP", self.root / "legacy-app"),
                                ("LEGACY_CONFIG", self.root / "legacy-config"),
                                ("LEGACY_DATA", self.root / "legacy-data")):
                stack.enter_context(patch.object(release, name, value))
            stack.enter_context(patch.object(release, "trusted_path", lambda path: None))
            stack.enter_context(patch.object(os, "geteuid", return_value=0))
            stack.enter_context(patch.object(release, "run", self.command))
            stack.enter_context(patch.object(release, "read_file", read_file))
            yield

    def verify(self, envelope, deadline):
        return HostAdapter.verify(self, envelope, deadline)

    def inspect(self, record, deadline):
        return HostAdapter.inspect(self, record, deadline)

    def start(self, record, deadline):
        self.point("before_start")
        super().start(record, deadline)
        self.point("after_start")

    def switch(self, record, deadline):
        self.point("before_switch")
        HostAdapter.switch(self, record, deadline)
        self.point("after_switch")

    def maintenance(self, deadline):
        self.point("maintenance")
        HostAdapter.maintenance(self, deadline)

    def stop(self, record, deadline):
        self.point("stop")
        super().stop(record, deadline)


class HostFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v8std-initial-")
        self.root = Path(self.temp.name)
        self.source = Source()
        config = {"site_url": self.source.url, "refresh_seconds": 1, "max_snippet_chars": 4000,
                  "memory_bytes": 536870912, "cpus": 1}
        config_hash = release.digest(release.canonical_json(config))
        self.policy = {"enabled": True, "runtime_enabled": False, "platform": "linux/amd64",
            "configs": {config_hash: config}, "ports": [port(), port()],
            "public_url": f"http://127.0.0.1:{port()}", "nginx_include": str(self.root / "upstream.conf"),
            "static_root": str(self.root / "static"),
            "capacity": {"disk_bytes": 1, "file_descriptors": 16, "available_memory_bytes": 2**40,
                         "network_evidence": None}}
        child = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"mediaType": "application/vnd.oci.image.config.v1+json", "digest": "sha256:" + "c" * 64}}
        child_raw = release.canonical_json(child)
        index = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json", "manifests": [{
            "mediaType": child["mediaType"], "digest": "sha256:" + release.digest(child_raw), "size": len(child_raw),
            "platform": {"os": "linux", "architecture": "amd64"}}]}
        release.atomic(self.root / "child.json", child_raw)
        release.atomic(self.root / "index.json", release.canonical_json(index))
        self.env = envelope() | {"configuration_digest": config_hash,
            "image_digest": "sha256:" + release.digest(release.canonical_json(index)),
            "platform_digest": "sha256:" + release.digest(child_raw),
            "corpus_id": self.source.manifest["corpus_id"], "archive_sha256": self.source.manifest["archive"]["sha256"]}
        self.adapter = InitialAdapter(self.root, self.policy)
        for name, value in (("policy.json", self.policy), ("envelope.json", self.env), ("edge.json", {"port": None}),
                            ("manifests/" + self.env["archive_sha256"] + ".json", self.source.manifest)):
            release.write_json(self.root / name, value)
        release.atomic(self.root / "static" / self.env["archive_sha256"] / "snapshot.tar.gz", self.source.archive)
        release.atomic(self.root / "upstream.conf", b"server 127.0.0.1:9 down;\n")
        self.authorize(self.env)
        with (self.root / "edge.log").open("wb") as log:
            self.edge = subprocess.Popen([sys.executable, "-m", "tests.mcp_release_fixture", "edge",
                str(self.root), self.policy["public_url"].rsplit(":", 1)[1]], cwd=ROOT,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        until = time.monotonic() + 5
        while True:
            try:
                self.request("/mcp", "POST")
                break
            except OSError:
                release.remaining(until)
                time.sleep(.025)

    def authorize(self, envelope):
        release.write_json(self.root / "authorization.json", {"schema_version": 1, "mode": "clean-host",
            "envelope_sha256": release.digest(release.canonical_json(envelope)), "allow_no_predecessor": True})

    def request(self, path, method="GET"):
        connection = http.client.HTTPConnection("127.0.0.1", int(self.policy["public_url"].rsplit(":", 1)[1]), timeout=2)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def close(self):
        self.adapter.fault = ""
        with self.adapter.boundaries():
            for path in (self.root / "processes").glob("*.json"):
                # Ownership mutation tests restore their foreign inventory first.
                record = release.read_record(path)["record"]
                ProcessAdapter.stop(self.adapter, record, time.monotonic() + 5)
        for child in self.adapter.children:
            child.poll()
        self.edge.terminate()
        self.edge.wait(5)
        self.source.close()
        self.temp.cleanup()

    def invoke(self, fault="", mode="execute"):
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
            process = subprocess.run([sys.executable, "-m", "tests.mcp_initial_install_fixture", str(self.root), mode, fault],
                cwd=ROOT, stdout=output, stderr=error, timeout=40)
            output.seek(0)
            error.seek(0)
            return process.returncode, output.read(), error.read()


def worker(root, mode, fault):
    adapter = InitialAdapter(root, release.read_record(root / "policy.json"), fault)
    controller_type = release.InitialInstallController
    class CrashController(controller_type):
        def save(self, journal, state=None, intent=None):
            super().save(journal, state, intent)
            adapter.point("state_" + journal["state"])
            adapter.point("intent_" + journal["intent"])
    original = release.write_json
    fired = False
    def write(path, value, **kwargs):
        nonlocal fired
        boundary = "commit" if path.parent.name == "releases" and value.get("state") == "COMMITTED" else (
            "pointer" if path == root / "active.json" else "")
        if boundary and not fired:
            adapter.point("before_" + boundary)
            if fault == "error_before_" + boundary:
                fired = True
                replace = os.replace
                def fail_rename(source, target):
                    if target == path:
                        raise OSError("injected before rename")
                    return replace(source, target)
                with patch.object(release.os, "replace", fail_rename):
                    return original(path, value, **kwargs)
        original(path, value, **kwargs)
        if boundary and not fired:
            adapter.point("after_" + boundary)
            if fault == "error_after_" + boundary:
                fired = True
                raise OSError("injected after durable rename")
    with adapter.boundaries(), patch.object(release, "write_json", write), \
         patch.object(release, "InitialInstallController", CrashController):
        controller = CrashController(root, adapter)
        try:
            if mode.startswith("cli_"):
                command = {"cli_submit": "initial-install", "cli_execute": "_initial-install",
                           "cli_recover": "initial-install-recover"}[mode]
                with tempfile.TemporaryFile() as stream:
                    stream.write((root / "envelope.json").read_bytes() + b"\n")
                    stream.seek(0)
                    with patch.object(release, "ROOT", root), patch.object(release, "trusted_policy", return_value=adapter.policy), \
                         patch.object(release, "HostAdapter", return_value=adapter), patch.object(sys, "stdin", stream), \
                         patch.object(sys, "argv", ["fixture", command]):
                        result = release.main()
            else:
                result = (controller.submit((root / "envelope.json").read_bytes()) if mode == "submit" else
                          release.Controller(root, adapter).recover() if mode == "recover" else controller.execute())
            print(json.dumps(result))
        except Exception as error:
            print(json.dumps({"state": "REJECTED", "error_code": getattr(error, "code", "host_failure")}))


if __name__ == "__main__":
    worker(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
