"""Opt-in native logging evidence; exact owned fixtures, never host deployment."""
from collections import Counter
import json
import os
from pathlib import Path
import shlex
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from tests.test_v8std_mcp_distribution import _context_command
from tests.test_v8std_mcp_release import port
from tests.mcp_logging_fixture import release

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = "sha256:bec25fa5b9f240225db206c5e21d35a8c28e2d4ae30b1b878d272eacd9df1031"


class LoggingFixtureCleanupTests(unittest.TestCase):
    def test_failed_removal_keeps_primary_error_and_attempts_other_owned_cleanup(self):
        fixture = LoggingDockerTests("test_native_preparation_and_hostile_files")
        fixture.prefix = "fixture"
        fixture.containers = ["second", "first"]
        fixture.volumes, fixture.networks, fixture.images = [], [], []
        removed = []

        def daemon(*args, **kwargs):
            if args[:2] == ("container", "ls"):
                name = args[args.index("--filter") + 1][7:-1]
                return "" if name in removed else name + "\n"
            if args[0] == "inspect":
                return json.dumps([{"Config": {"Labels": {"pro.v8std.test": "fixture"}}}])
            if args[:2] == ("rm", "-f"):
                if args[2] == "first":
                    raise AssertionError("fixture removal failed")
                removed.append(args[2])
                return ""
            raise AssertionError(args)

        class FailingCheck(unittest.TestCase):
            def runTest(self):
                self.addCleanup(fixture.cleanup)
                raise RuntimeError("primary MCP failure")

        result = unittest.TestResult()
        with patch.object(fixture, "docker", side_effect=daemon):
            FailingCheck().run(result)
        self.assertEqual(removed, ["second"])
        self.assertEqual(len(result.errors), 1)
        self.assertIn("primary MCP failure", result.errors[0][1])
        self.assertEqual(len(result.failures), 1)
        self.assertIn("fixture removal failed", result.failures[0][1])


@unittest.skipUnless(os.environ.get("V8STD_TASK6_LOGGING_DOCKER") == "1", "explicit native logging fixtures")
class LoggingDockerTests(unittest.TestCase):
    def setUp(self):
        self.prefix = "v8std-task6-logging-" + uuid.uuid4().hex[:16]
        self.containers = []
        self.volumes = []
        self.networks = []
        self.images = []
        self.addCleanup(self.cleanup)

    def docker(self, *args, timeout=30):
        result = _context_command(["docker", *map(str, args)], timeout=timeout)
        self.assertEqual(result.returncode, 0, result.stdout)
        return result.stdout

    def cleanup(self):
        failures = []
        for kind, names in (("container", self.containers), ("volume", self.volumes),
                            ("network", self.networks), ("image", self.images)):
            for name in reversed(names):
                try:
                    if kind == "container":
                        query = [kind, "ls", "-a", "--filter", "name=^/" + name + "$", "--format", "{{.Names}}"]
                    else:
                        query = [kind, "ls", "--filter", ("reference=" if kind == "image" else "name=") + name,
                                 "--format", "{{.Repository}}:{{.Tag}}" if kind == "image" else "{{.Name}}"]
                    rows = self.docker(*query).splitlines()
                    if not rows:
                        continue
                    self.assertEqual(rows, [name])
                    info = json.loads(self.docker(*(["inspect", name] if kind == "container" else [kind, "inspect", name])))[0]
                    labels = info["Config"]["Labels"] if kind in {"image", "container"} else info["Labels"]
                    self.assertEqual(labels["pro.v8std.test"], self.prefix)
                    self.docker(*(["rm", "-f", name] if kind == "container" else [kind, "rm", name]))
                    self.assertFalse(self.docker(*query).strip())
                except Exception as error:
                    failures.append(f"{kind} {name}: {error}")
        if failures:
            self.fail("owned logging fixture cleanup failed: " + "; ".join(failures))

    def test_native_preparation_and_hostile_files(self):
        name = self.prefix + "-permissions"
        self.containers.append(name)
        result = self.docker("run", "--name", name, "--pull=never", "--network=none",
            "--read-only", "--cap-drop=ALL", "--cap-add=CHOWN", "--cap-add=DAC_OVERRIDE", "--cap-add=FOWNER",
            "--security-opt=no-new-privileges", "--init", "--user=0:0", "--memory=256m", "--cpus=1", "--pids-limit=64",
            "--label", "pro.v8std.test=" + self.prefix,
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--tmpfs=/native-tests:rw,noexec,nosuid,size=32m,mode=0700",
            "--mount", f"type=bind,source={ROOT / 'scripts'},target=/work/scripts,readonly",
            "--mount", f"type=bind,source={ROOT / 'tests'},target=/work/tests,readonly",
            "--workdir=/work", "--env=V8STD_LOGGING_NATIVE=1", "--entrypoint=python", RUNTIME,
            "-m", "unittest", "tests.test_v8std_mcp_logging.NativeLoggingPreparationTests", "-v", timeout=60)
        print(result, flush=True)

    def test_native_mcp_restart_rollback_and_both_logrotate_stanzas(self):
        # Build only a labelled logrotate helper from the retained local fixture.
        # No runtime release/candidate/source-SHA claim is made by this image.
        base = json.loads(self.docker("image", "inspect", "v8std-task4-mcp:arm64"))[0]
        self.assertEqual(base["Id"], RUNTIME)
        helper_image = self.prefix + ":rotation"
        self.images.append(helper_image)  # Track before even an uncertain build.
        with tempfile.TemporaryDirectory(prefix="v8std-logging-build-") as context:
            built = _context_command(["docker", "build", "--pull=false", "--progress=plain", "--file", "-",
                                      "--tag", helper_image, context], timeout=600,
                input=("FROM v8std-task4-mcp:arm64\nUSER 0:0\n"
                       "RUN apt-get update && apt-get install -y --no-install-recommends logrotate "
                       "&& groupadd -g 10002 v8std-mcp && useradd -u 10002 -g 10002 -M v8std-mcp\n"
                       "LABEL pro.v8std.test=" + self.prefix + "\n"))
            self.assertEqual(built.returncode, 0, built.stdout)
        volume, network, helper = [self.prefix + "-" + suffix for suffix in ("data", "net", "root")]
        self.volumes.append(volume)
        self.docker("volume", "create", "--label", "pro.v8std.test=" + self.prefix, volume)
        mountpoint = json.loads(self.docker("volume", "inspect", volume))[0]["Mountpoint"]
        # A dedicated ordinary bridge supports the launcher's loopback-only
        # published port; Docker Desktop's internal bridge does not publish it.
        self.networks.append(network)
        self.docker("network", "create", "--label", "pro.v8std.test=" + self.prefix, network)
        self.containers.append(helper)
        self.docker("run", "-d", "--name", helper, "--pull=never", "--network", network, "--network-alias=source",
            "--read-only", "--cap-drop=ALL", "--cap-add=CHOWN", "--cap-add=DAC_OVERRIDE", "--cap-add=FOWNER",
            "--cap-add=SETUID", "--cap-add=SETGID", "--security-opt=no-new-privileges", "--init", "--user=0:0",
            "--memory=256m", "--memory-swap=256m", "--cpus=1", "--pids-limit=64", "--label", "pro.v8std.test=" + self.prefix,
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--mount", f"type=volume,source={volume},target=/fixture",
            "--mount", f"type=bind,source={ROOT / 'scripts'},target=/work/scripts,readonly",
            "--mount", f"type=bind,source={ROOT / 'tests'},target=/work/tests,readonly",
            "--workdir=/work", "--entrypoint=python", helper_image,
            "-m", "http.server", "8080", "--directory", "/fixture/source")

        def native(expression, timeout=30):
            return json.loads(self.docker("exec", helper, "python", "-c",
                "import json,os; os.umask(0o077); from tests import mcp_logging_fixture as f; print(json.dumps(" + expression + "))", timeout=timeout))

        manifest = native("f.native_initialize()")
        rotation_version = self.docker("exec", helper, "logrotate", "--version")
        self.assertIn("logrotate", rotation_version)
        old, candidate = self.prefix + "-old", self.prefix + "-candidate"
        ports = {old: port(), candidate: port()}
        health = {}

        def check(name, query):
            endpoint = f"http://127.0.0.1:{ports[name]}"
            deadline = time.monotonic() + 30
            while True:
                try:
                    state = json.loads(release.http(endpoint + "/healthz", deadline))
                    if state.get("ready"):
                        break
                except release.ReleaseError:
                    if time.monotonic() >= deadline:
                        self.fail("health deadline\n" + self.docker("logs", name))
                time.sleep(min(.1, release.remaining(deadline)))
            self.assertTrue(state["ok"] and state["ready"])
            self.assertEqual(state["corpus_id"], manifest["corpus_id"])
            health[name] = state
            result = release.rpc(endpoint, "initialize", {"protocolVersion": "2025-03-26",
                "capabilities": {}, "clientInfo": {"name": "logging-fixture", "version": "1"}}, deadline, 1)
            self.assertIn("serverInfo", result)
            for number, tool, arguments in ((2, "v8std_search", {"query": query}),
                    (3, "v8std_get_page", {"id_or_alias_or_url": "std437"})):
                result = release.rpc(endpoint, "tools/call", {"name": tool, "arguments": arguments}, deadline, number)
                self.assertFalse(result.get("isError"), result)
                content = result.get("structuredContent")
                if content is None:
                    content = json.loads(next(item["text"] for item in result["content"] if item["type"] == "text"))
                if tool == "v8std_get_page":
                    self.assertTrue(content["found"])
                    self.assertEqual(content["page"]["id"], "std437")
                    self.assertIn("Запросы", content["page"]["body_markdown"])
                else:
                    self.assertEqual(content["normalized_query"], query)

        for name, query in ((old, "before-rotation-old"), (candidate, "before-rotation-candidate")):
            command = native(f"f.native_plan({name!r}, {ports[name]})")
            # Keep the production flag/profile/destination argv. Translate only
            # the fixture's native volume paths and unverified image identity.
            self.assertIn("--usage-log", command)
            command = [arg.replace("source=/fixture/", "source=" + mountpoint + "/") for arg in command]
            image_at = next(i for i, arg in enumerate(command) if arg.startswith(release.IMAGE + "@"))
            command[image_at] = RUNTIME
            overlays = []
            definition = (ROOT / "delivery/mcp/Dockerfile").read_text().replace("\\\n", " ")
            for line in definition.splitlines():
                if line.startswith(("COPY scripts/", "COPY runtime/")):
                    for source in shlex.split(line)[1:-1]:
                        overlays += ["--mount", f"type=bind,source={ROOT / source},target=/opt/v8std/{source},readonly"]
            command[image_at:image_at] = ["--network", network, "--label", "pro.v8std.test=" + self.prefix, *overlays]
            self.containers.append(name)
            self.docker(*command[1:])
            check(name, query)
            info = json.loads(self.docker("inspect", name))[0]
            self.assertEqual(info["Config"]["User"], "10001:10001")
            self.assertTrue(info["HostConfig"]["ReadonlyRootfs"])
            self.assertEqual(info["HostConfig"]["CapDrop"], ["ALL"])
            log_mount = next(m for m in info["Mounts"] if m["Destination"] == "/var/log/v8std-mcp-usage.jsonl")
            self.assertEqual(log_mount["Source"], mountpoint + "/logs/tool-usage.jsonl")
            self.assertTrue(log_mount["RW"])
            # Native user cannot unlink the file-bind pathname.
            denied = _context_command(["docker", "exec", name, "python", "-c",
                "import os; os.unlink('/var/log/v8std-mcp-usage.jsonl')"], timeout=10)
            self.assertNotEqual(denied.returncode, 0)

        before = native("f.native_observe()")
        self.assertEqual((before["logs"]["uid"], before["logs"]["gid"], before["logs"]["mode"], before["logs"]["parent_mode"]),
                         (10001, 0, 0o640, 0o700))
        # Exact controlled inventory, not an exactly-once concurrent-rotation promise.
        self.assertEqual(Counter(e["tool"] for e in before["logs"]["events"]),
                         {"v8std_search": 2, "v8std_get_page": 2})
        self.assertEqual({e.get("query") for e in before["logs"]["events"] if e["tool"] == "v8std_search"},
                         {"before-rotation-old", "before-rotation-candidate"})
        rotated = native("f.native_rotate()")
        for kind in ("logs", "legacy"):
            self.assertEqual(rotated["files"][kind]["inode"], before[kind]["inode"])
            self.assertEqual(rotated["files"][kind]["events"], [])
            archives = rotated["files"][kind]["archives"]
            self.assertEqual(len(archives), 1)
            self.assertEqual([json.loads(line) for line in next(iter(archives.values())).splitlines()], before[kind]["events"])
        self.docker("stop", "--time=5", old)
        check(candidate, "after-rotation-candidate")
        self.docker("restart", "--time=5", candidate)
        check(candidate, "after-restart-candidate")
        # Bounded runtime rollback leg, not a complete controller/nginx switch.
        self.docker("stop", "--time=5", candidate)
        self.docker("start", old)
        check(old, "after-rollback-old")
        after = native("f.native_observe()")
        for field in ("inode", "uid", "gid", "mode", "parent_mode"):
            self.assertEqual(after["logs"][field], before["logs"][field])
        self.assertEqual(Counter(e["tool"] for e in after["logs"]["events"]),
                         {"v8std_search": 3, "v8std_get_page": 3})
        self.assertEqual({e.get("query") for e in after["logs"]["events"] if e["tool"] == "v8std_search"},
                         {"after-rotation-candidate", "after-restart-candidate", "after-rollback-old"})
        self.assertEqual(after["legacy"], rotated["files"]["legacy"])
        print("TASK6_LOGGING_EVIDENCE=" + json.dumps({"fixture": self.prefix, "base_image": RUNTIME,
            "helper_image": json.loads(self.docker("image", "inspect", helper_image))[0]["Id"],
            "logrotate_version": rotation_version, "logrotate": rotated["logrotate"],
            "before": before, "after": after, "health": health}, sort_keys=True), flush=True)


if __name__ == "__main__":
    unittest.main()
