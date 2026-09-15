"""Focused distribution checks; real Docker/browser acceptance is opt-in."""
import hashlib
from contextlib import contextmanager
import html as html_module
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_mcp_container as harness


def _context_group_running(pgid):
    # Orphaned zombies cannot run or retain descriptors. Their reap belongs to
    # init; waiting on killpg(0) alone can never finish under a non-reaping PID1.
    states = subprocess.run(["ps", "-A", "-o", "pgid=,stat="], check=True,
                            capture_output=True, text=True, timeout=1).stdout
    return any(fields[0] == str(pgid) and not fields[1].startswith("Z")
               for line in states.splitlines() if len(fields := line.split()) == 2)


def _signal_context_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        # macOS can report EPERM for an already vanished group. A live group
        # still makes signal denial a real cleanup failure, never a success.
        if _context_group_running(pgid):
            raise


def _stop_context_group(process):
    stopped = False
    try:
        for sig, grace in ((signal.SIGTERM, 1), (signal.SIGKILL, 2)):
            _signal_context_group(process.pid, sig)
            deadline = time.monotonic() + grace
            while True:
                process.poll()  # Reap the leader, independently of descendants.
                if not _context_group_running(process.pid):
                    stopped = True
                    return
                if time.monotonic() >= deadline:
                    break
                time.sleep(.02)
        raise AssertionError(f"owned process group {process.pid} did not terminate")
    finally:
        try:
            if not stopped:
                _signal_context_group(process.pid, signal.SIGKILL)
        finally:
            process.wait(timeout=2)


def _context_command(args, *, input=None, timeout):
    """Bound a CLI and its group; inherited output descriptors never delay EOF."""
    with tempfile.TemporaryFile(mode="w+") as source, tempfile.TemporaryFile(mode="w+") as log:
        if input is not None:
            source.write(input)
            source.seek(0)
        process = subprocess.Popen(args, cwd=ROOT, stdin=source, stdout=log,
                                   stderr=subprocess.STDOUT, text=True, start_new_session=True)
        primary = None
        try:
            process.wait(timeout=timeout)
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                _stop_context_group(process)
            except BaseException as error:
                if primary is None:
                    raise
                primary.add_note(f"process cleanup failed: {error}")
        log.seek(0)
        output = log.read(2 * 1024 * 1024 + 1)
        if len(output) > 2 * 1024 * 1024:
            raise AssertionError("fixture command output exceeded 2MiB")
        return subprocess.CompletedProcess(args, process.returncode, output, "")


class _ContextImage:
    """Own only a fresh UUID tag and the named containers launched from it."""
    def __init__(self):
        self.name = "v8std-task6-context-" + uuid.uuid4().hex
        self.tag = self.name + ":fixture"
        self.containers = []

    def __enter__(self):
        return self

    def run(self, args):
        name = self.name + "-" + str(len(self.containers) + 1)
        self.containers.append(name)  # Record ownership before the daemon call.
        return _context_command(
            ["docker", "run", "--name", name, "--network", "none", "--read-only",
             "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--init",
             "--memory", "256m", "--pids-limit", "64", "--tmpfs", "/tmp:size=16m",
             "--entrypoint", "python", self.tag, *args], timeout=30)

    @staticmethod
    def present(kind, name):
        selector = "name=^/" + name + "$" if kind == "container" else "reference=" + name
        format = "{{.Names}}" if kind == "container" else "{{.Repository}}:{{.Tag}}"
        result = _context_command(["docker", kind, "ls", "--all", "--filter", selector,
                                   "--format", format], timeout=10)
        if result.returncode:
            raise AssertionError(f"cannot verify {kind} {name}: {result.stdout.strip()}")
        names = result.stdout.splitlines()
        if any(value != name for value in names):
            raise AssertionError(f"unexpected inventory for exact {kind} {name}")
        return bool(names)

    def __exit__(self, exception_type, primary, traceback):
        failures = []
        for kind, name in [("container", name) for name in self.containers] + [("image", self.tag)]:
            try:
                if not self.present(kind, name):
                    continue
                command = ["docker", "rm", "--force", name] if kind == "container" else ["docker", "image", "rm", name]
                result = _context_command(command, timeout=30)
                if result.returncode:
                    failures.append(f"{kind} {name}: {result.stdout.strip()}")
                if self.present(kind, name):
                    failures.append(f"{kind} {name} still exists")
            except Exception as error:
                failures.append(f"{kind} {name}: {error}")
        if failures:
            error = AssertionError("fixture cleanup failed: " + "; ".join(failures))
            if primary is None:
                raise error
            primary.add_note(str(error))
        return False


_DOCKER_FAULT_CLI = r'''
import hashlib, json, os, pathlib, subprocess, sys, time
state_path = pathlib.Path(os.environ["CONTEXT_FAULT_STATE"])
state = json.loads(state_path.read_text())
args = sys.argv[1:]
state["calls"].append(args)
def save():
    state_path.write_text(json.dumps(state))
def option(name):
    return args[args.index(name) + 1]
if args[0] == "build":
    if state.get("orphan"):
        helper = subprocess.Popen([sys.executable, "-c", """
import json, os, pathlib, signal, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
pathlib.Path(os.environ['CONTEXT_HELPER_PID']).write_text(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp()}))
while True: time.sleep(1)
"""])
        deadline = time.monotonic() + 2
        while not pathlib.Path(os.environ["CONTEXT_HELPER_PID"]).exists():
            if time.monotonic() >= deadline: raise RuntimeError("helper failed to start")
            time.sleep(.01)
        print("fixture build refused", file=sys.stderr, flush=True)
        sys.exit(17)
    state["images"].append(option("--tag"))
elif args[0] == "run":
    name = option("--name") if "--name" in args else "anonymous-fixture"
    state["containers"].append(name)
    if state.get("timeout"):
        save()
        time.sleep(60)
    if "-c" in args:
        root = pathlib.Path(os.environ["CONTEXT_FAULT_ROOT"])
        print(json.dumps({p:hashlib.sha256((root / pathlib.Path(p).relative_to('/opt/v8std')).read_bytes()).hexdigest()
                          for p in json.loads(args[-1])}))
    else:
        print("No broken requirements found.")
    if "--rm" in args: state["containers"].remove(name)
elif args[:2] == ["container", "ls"]:
    name = option("--filter").removeprefix("name=^/").removesuffix("$")
    sys.stdout.write("".join(x + "\n" for x in state["containers"] if x == name))
elif args[0] == "rm":
    if state.get("container_rm_error"):
        print("fixture container removal refused", file=sys.stderr)
        save()
        sys.exit(1)
    state["containers"].remove(args[-1])
elif args[:2] == ["image", "ls"]:
    tag = option("--filter").removeprefix("reference=")
    sys.stdout.write("".join(x + "\n" for x in state["images"] if x == tag))
elif args[:2] == ["image", "rm"]:
    if state.get("image_rm_error"):
        print("fixture image removal refused", file=sys.stderr)
        save()
        sys.exit(1)
    if not state.get("image_rm_lies") and args[-1] in state["images"]:
        state["images"].remove(args[-1])
else:
    raise AssertionError("unexpected Docker operation: " + repr(args))
save()
'''


@contextmanager
def _docker_fault_cli(**faults):
    """External CLI seam; daemon state outlives a timed-out client process."""
    with tempfile.TemporaryDirectory(prefix="v8std-context-fault-") as temporary:
        directory = Path(temporary)
        cli = directory / "docker"
        cli.write_text("#!" + sys.executable + "\n" + _DOCKER_FAULT_CLI)
        cli.chmod(0o700)
        state = directory / "daemon.json"
        state.write_text(json.dumps({"images": ["foreign:image"], "containers": ["foreign-container"],
                                     "calls": [], **faults}))
        with patch.dict(os.environ, {"PATH": str(directory) + os.pathsep + os.environ["PATH"],
                                     "CONTEXT_FAULT_STATE": str(state),
                                     "CONTEXT_FAULT_ROOT": str(ROOT),
                                     "CONTEXT_HELPER_PID": str(directory / "helper.json")}):
            yield state, directory / "helper.json"


def _test_process_running(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="],
                            capture_output=True, text=True, timeout=2)
    return bool(result.stdout.strip()) and not result.stdout.strip().startswith("Z")


class ContextHarnessLifecycleTests(unittest.TestCase):
    def test_command_timeout_reaps_leader_without_cleanup_error(self):
        with self.assertRaises(subprocess.TimeoutExpired) as raised:
            _context_command([sys.executable, "-c", "import time; time.sleep(10)"], timeout=.2)
        self.assertEqual(getattr(raised.exception, "__notes__", []), [])

    def test_all_build_paths_stop_term_ignoring_helper_after_leader_exit(self):
        methods = (
            "test_retained_dev_copy_context_includes_requirements_and_entrypoint_dependencies",
            "test_every_runtime_copy_survives_actual_buildkit_context_filter",
            "test_fresh_runtime_build_contains_every_copy_input_and_imports_locked_runtime",
        )
        for method in methods:
            with self.subTest(method=method), _docker_fault_cli(orphan=True) as (_, pid_path), \
                    tempfile.TemporaryFile(mode="w+") as output:
                driver = (
                    "from tests.test_v8std_mcp_distribution import ImageContextClosureTests\n"
                    "try: ImageContextClosureTests()." + method + "()\n"
                    "except AssertionError as error:\n"
                    " assert 'fixture build refused' in str(error), str(error)\n"
                    "else: raise AssertionError('missing build failure')\n"
                )
                process = subprocess.Popen([sys.executable, "-c", driver], cwd=ROOT,
                                           stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.fail("build caller waited on a descendant's inherited descriptor")
                    output.seek(0)
                    self.assertEqual(process.returncode, 0, output.read())
                    self.assertTrue(pid_path.exists(), "real helper did not start")
                    helper = json.loads(pid_path.read_text())
                    self.assertFalse(_test_process_running(helper["pid"]),
                                     "TERM-ignoring helper survived its build leader")
                finally:
                    # RED must not leak the deliberately hostile fixture either.
                    if pid_path.exists():
                        try:
                            os.kill(json.loads(pid_path.read_text())["pid"], signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=2)

    @contextmanager
    def short_runtime_timeout(self):
        real_run, real_wait = subprocess.run, subprocess.Popen.wait
        observed = []
        def run(args, **kwargs):
            if args[:2] == ["docker", "run"]:
                kwargs["timeout"] = .3
            try:
                return real_run(args, **kwargs)
            except subprocess.TimeoutExpired as error:
                if args[:2] == ["docker", "run"]:
                    observed.append(error)
                raise
        def wait(process, timeout=None):
            if process.args[:2] == ["docker", "run"] and timeout == 30:
                timeout = .3
            try:
                return real_wait(process, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                if process.args[:2] == ["docker", "run"]:
                    observed.append(error)
                raise
        with patch.object(subprocess, "run", run), patch.object(subprocess.Popen, "wait", wait):
            yield observed

    def test_runtime_timeout_removes_exact_daemon_container_then_image(self):
        with _docker_fault_cli(timeout=True) as (path, _), self.short_runtime_timeout() as observed:
            with self.assertRaises(subprocess.TimeoutExpired) as raised:
                ImageContextClosureTests().test_fresh_runtime_build_contains_every_copy_input_and_imports_locked_runtime()
            state = json.loads(path.read_text())
            self.assertIs(raised.exception, observed[0])
            self.assertEqual(getattr(raised.exception, "__notes__", []), [])
            self.assertEqual(state["containers"], ["foreign-container"])
            self.assertEqual(state["images"], ["foreign:image"])
            removed = [x for x in state["calls"] if x[0] == "rm" or x[:2] == ["image", "rm"]]
            self.assertEqual([x[0] for x in removed], ["rm", "image"])

    def test_image_removal_failure_is_visible_after_successful_assertions(self):
        with _docker_fault_cli(image_rm_error=True) as (path, _):
            with self.assertRaisesRegex(AssertionError, "cleanup.*fixture image removal refused"):
                ImageContextClosureTests().test_fresh_runtime_build_contains_every_copy_input_and_imports_locked_runtime()
            self.assertEqual(json.loads(path.read_text())["containers"], ["foreign-container"])

    def test_successful_remove_exit_cannot_hide_a_retained_fixture_tag(self):
        with _docker_fault_cli(image_rm_lies=True):
            with self.assertRaisesRegex(AssertionError, "cleanup.*still exists"):
                ImageContextClosureTests().test_fresh_runtime_build_contains_every_copy_input_and_imports_locked_runtime()

    def test_cleanup_failures_preserve_primary_timeout_and_attempt_both_removals(self):
        with _docker_fault_cli(timeout=True, container_rm_error=True, image_rm_error=True) as (path, _), \
                self.short_runtime_timeout() as observed:
            with self.assertRaises(subprocess.TimeoutExpired) as raised:
                ImageContextClosureTests().test_fresh_runtime_build_contains_every_copy_input_and_imports_locked_runtime()
            self.assertIs(raised.exception, observed[0])
            notes = " ".join(getattr(raised.exception, "__notes__", []))
            self.assertIn("fixture container removal refused", notes)
            self.assertIn("fixture image removal refused", notes)
            state = json.loads(path.read_text())
            self.assertIn("foreign-container", state["containers"])
            self.assertIn("foreign:image", state["images"])


@unittest.skipUnless(os.environ.get("V8STD_TEST_CI_BUILD"), "explicit pinned builder acceptance")
class PinnedCiBuilderTests(unittest.TestCase):
    def test_builder_has_locked_dependencies_compression_and_real_dejavu_fonts(self):
        with _ContextImage() as owned:
            built = _context_command(["docker", "build", "--progress=plain", "-f", "Dockerfile.ci",
                                      "-t", owned.tag, "."], timeout=300)
            self.assertEqual(built.returncode, 0, built.stdout)
            probe = (
                "import importlib.metadata as m,json,sys,zlib; from PIL import ImageFont; "
                "names=[ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+n,20).getname() "
                "for n in ['DejaVuSans.ttf','DejaVuSans-Bold.ttf']]; "
                "print(json.dumps({'python':sys.version.split()[0],'zlib':zlib.ZLIB_RUNTIME_VERSION,"
                "'fonts':names,'zensical':m.version('zensical'),'pillow':m.version('pillow')}))")
            result = owned.run(["-c", probe])
            self.assertEqual(result.returncode, 0, result.stdout)
            info = json.loads(result.stdout)
            self.assertEqual(info["python"], "3.12.14")
            self.assertEqual(info["zensical"], "0.0.47")
            self.assertEqual(info["pillow"], "12.3.0")
            self.assertEqual(info["fonts"], [["DejaVu Sans", "Book"], ["DejaVu Sans", "Bold"]])
            self.assertTrue(info["zlib"])
            print("pinned builder:", json.dumps(info, sort_keys=True))


@unittest.skipUnless(os.environ.get("V8STD_TEST_IMAGE_BUILD"), "explicit fresh image build acceptance")
class ImageContextClosureTests(unittest.TestCase):
    def test_retained_dev_copy_context_includes_requirements_and_entrypoint_dependencies(self):
        definition = (ROOT / "docker-compose/docker/Dockerfile").read_text().replace("\\\n", " ")
        copies = [line for line in definition.splitlines() if line.startswith("COPY ")]
        with tempfile.TemporaryDirectory(prefix="v8std-task6-dev-context-") as output:
            result = _context_command(
                ["docker", "build", "--progress=plain", "--file", "-",
                 "--output", "type=local,dest=" + output, "."],
                input="FROM scratch\n" + "\n".join(copies) + "\n", timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout)
            required = ["requirements.txt", "requirements-mcp.txt"] + ["scripts/" + name for name in (
                "generate_social_cards.py", "generate_search_vectors.py", "generate_ai_artifacts.py",
                "install_zensical.sh", "run_v8std_mcp.sh", "zensical_docs.sh", "zensical-version.sh",
                "v8std_mcp_server.py", "check_article_html.py", "publish_diagnostic_sitemap.py",
                "publish_license_texts.py")]
            for relative in required:
                self.assertEqual((Path(output) / "opt/v8std" / relative).read_bytes(),
                                 (ROOT / relative).read_bytes(), relative)

    def test_every_runtime_copy_survives_actual_buildkit_context_filter(self):
        definition = (ROOT / "Dockerfile.mcp").read_text().replace("\\\n", " ")
        copies = [line for line in definition.splitlines() if line.startswith("COPY ")]
        # Execute the real COPY closure through the real ignore file. Scratch
        # isolates context failure from registry availability and dependency I/O.
        with tempfile.TemporaryDirectory(prefix="v8std-task6-context-") as output:
            result = _context_command(
                ["docker", "build", "--progress=plain", "--file", "-",
                 "--output", "type=local,dest=" + output, "."],
                input="FROM scratch\nWORKDIR /opt/v8std\n" + "\n".join(copies) + "\n", timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout)
            for line in copies:
                *sources, destination = shlex.split(line)[1:]
                for source in sources:
                    path = ROOT / source
                    files = path.rglob("*") if path.is_dir() else [path]
                    for item in files:
                        if item.is_file():
                            relative = item.relative_to(path) if path.is_dir() else Path(item.name)
                            copied = Path(output) / "opt/v8std" / destination / relative
                            self.assertEqual(copied.read_bytes(), item.read_bytes(), str(item))

    def test_fresh_runtime_build_contains_every_copy_input_and_imports_locked_runtime(self):
        # Catch missing dockerignore entries using BuildKit's actual context, not
        # a second implementation of ignore-pattern semantics. This is a fixture
        # image; the all-zero revision deliberately makes no release claim.
        expected = {}
        definition = (ROOT / "Dockerfile.mcp").read_text().replace("\\\n", " ")
        for line in definition.splitlines():
            if not line.startswith("COPY "):
                continue
            *sources, destination = shlex.split(line)[1:]
            for source in sources:
                path = ROOT / source
                files = sorted(path.rglob("*")) if path.is_dir() else [path]
                for item in files:
                    if item.is_file():
                        relative = item.relative_to(path) if path.is_dir() else Path(item.name)
                        target = str(Path("/opt/v8std") / destination / relative)
                        expected[target] = hashlib.sha256(item.read_bytes()).hexdigest()
        with _ContextImage() as fixture:
            built = _context_command(
                ["docker", "build", "--progress=plain", "--file", "Dockerfile.mcp",
                 "--build-arg", "SOURCE_SHA=" + "0" * 40, "--tag", fixture.tag, "."], timeout=600)
            self.assertEqual(built.returncode, 0, built.stdout)
            probe = (
                "import hashlib,json,os,pathlib,sys; "
                "sys.path.insert(0,'/opt/v8std/scripts'); import v8std_mcp_server,v8std_mcp_hold; "
                "assert os.getuid()==10001; "
                "print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() "
                "for p in json.loads(sys.argv[1])}))"
            )
            result = fixture.run(["-c", probe, json.dumps(list(expected))])
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout), expected)
            checked = fixture.run(["-m", "pip", "check"])
            self.assertEqual(checked.returncode, 0, checked.stdout)


class GatewayProfileTests(unittest.TestCase):
    def validate(self, state):
        return harness.validate_gateway_profile(state, expected_cache={
            "Name": "owned-cache", "Mountpoint": "/var/lib/docker/volumes/owned-cache/_data"})

    def test_unsafe_inherited_gateway_settings_are_rejected_without_mutation(self):
        for value in ("true", "1", "false", "0"):
            env = {"DOCKER_MCP_IN_DIND": value, "PATH": "/some/path"}
            before = dict(env)
            with self.subTest(value=value), self.assertRaises(AssertionError):
                harness.gateway_environment(env)
            self.assertEqual(env, before)
        env = {"PATH": "/some/path"}
        self.assertEqual(harness.gateway_environment(env), env)

    def state(self):
        return {"Id": "session-server", "Image": "sha256:" + "a" * 64,
                "Config": {"User": "10001:10001", "WorkingDir": "/opt/v8std"},
                "HostConfig": {"Init": True, "Privileged": False,
                               "SecurityOpt": ["no-new-privileges=true"],
                               "ReadonlyRootfs": False, "CapDrop": None,
                               "Tmpfs": None, "NetworkMode": "none"},
                "Mounts": [{"Type": "volume", "Name": "owned-cache",
                            "Source": "/var/lib/docker/volumes/owned-cache/_data",
                            "Destination": "/var/lib/v8std-mcp", "RW": True}]}

    def test_privileged_environment_is_rejected_before_any_gateway_or_docker_launch(self):
        with patch.dict(os.environ, {"DOCKER_MCP_IN_DIND": "1"}), \
                patch.object(harness, "run") as docker, patch.object(harness, "Stdio") as launch:
            with self.assertRaisesRegex(AssertionError, "unsafe DOCKER_MCP_IN_DIND"):
                harness.host_gateway_check("not-launched", "test-image", "test-cache",
                                           "http://v8std.localhost/", Path("/not-used"))
            docker.assert_not_called()
            launch.assert_not_called()

    def test_privileged_preflight_is_not_disabled_by_python_optimization(self):
        code = "from check_mcp_container import gateway_environment; gateway_environment({'DOCKER_MCP_IN_DIND':'1'})"
        result = subprocess.run([sys.executable, "-O", "-c", code], cwd=ROOT / "scripts",
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe DOCKER_MCP_IN_DIND", result.stderr)

    def test_native_profile_reports_required_and_optional_controls(self):
        for security_opt in ("no-new-privileges", "no-new-privileges:true", "no-new-privileges=true"):
            state = self.state()
            state["HostConfig"]["SecurityOpt"] = [security_opt]
            result = self.validate(state)
            self.assertEqual(result["id"], state["Id"])
            self.assertEqual(result["image_id"], state["Image"])
            self.assertEqual(result["user"], "10001:10001")
            self.assertTrue(result["init"])
            self.assertTrue(result["no_new_privileges"])
            self.assertFalse(result["privileged"])
            self.assertFalse(result["read_only"])
            self.assertIsNone(result["cap_drop"])
            self.assertIsNone(result["tmpfs"])
            self.assertEqual(result["mounts"], state["Mounts"])

    def test_native_profile_rejects_each_missing_or_disabled_required_control(self):
        for section, key, value in (("Config", "User", "0:0"),
                                    ("Config", "User", "10001:0"),
                                    ("HostConfig", "Init", False),
                                    ("HostConfig", "Privileged", True),
                                    ("HostConfig", "SecurityOpt", []),
                                    ("HostConfig", "SecurityOpt", ["no-new-privileges=false"]),
                                    ("HostConfig", "SecurityOpt", ["no-new-privileges:true", "no-new-privileges:false"])):
            for missing in (False, True):
                with self.subTest(key=key, value=value, missing=missing):
                    state = self.state()
                    if missing:
                        del state[section][key]
                    else:
                        state[section][key] = value
                    with self.assertRaises(AssertionError):
                        self.validate(state)
        state = self.state()
        del state["Mounts"]
        with self.assertRaises(AssertionError):
            self.validate(state)

    def test_socket_sources_aliases_and_destinations_cannot_hide_in_mounts(self):
        mounts = [
            {"Type": "bind", "Source": "/var/run/docker.sock", "Destination": "/socket-alias"},
            {"Type": "bind", "Source": "/Users/operator/.docker/run/docker.sock", "Destination": "/var/lib/v8std-mcp"},
            {"Type": "bind", "Source": "/tmp/opaque-daemon-alias", "Destination": "/var/lib/v8std-mcp"},
            {"Type": "bind", "Source": "/tmp/opaque-daemon-alias", "Destination": "/run/docker.sock"},
            {"Type": "volume", "Source": "/var/run/docker.raw.sock", "Destination": "/var/lib/v8std-mcp"},
            {"Type": "volume", "Source": "/cache", "Destination": "/var/run/docker.sock"},
            {"Type": "bind", "Source": "/run", "Destination": "/daemon-directory"},
        ]
        for mount in mounts:
            with self.subTest(mount=mount), self.assertRaises(AssertionError):
                state = self.state()
                state["Mounts"] = [mount]
                self.validate(state)

    def test_only_exact_writable_owned_cache_mount_is_allowed(self):
        for field, value in (("Name", "other-cache"), ("Source", "/unexpected/alias"),
                             ("Destination", "/unexpected"), ("RW", False)):
            state = self.state()
            state["Mounts"][0][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.validate(state)
        state = self.state()
        state["Mounts"].append(dict(state["Mounts"][0]))
        with self.assertRaises(AssertionError):
            self.validate(state)

    def test_optional_hardening_is_reported_when_present(self):
        state = self.state()
        state["HostConfig"].update(ReadonlyRootfs=True, CapDrop=["ALL"], Tmpfs={"/tmp": "size=64m"})
        result = self.validate(state)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["cap_drop"], ["ALL"])
        self.assertEqual(result["tmpfs"], {"/tmp": "size=64m"})


class SiteOverrideTests(unittest.TestCase):
    def test_two_valid_urls_do_not_require_default_to_fail(self):
        with patch.object(harness, "http", return_value=(200, {}, b"")) as request:
            self.assertEqual(harness.check_default_source("http://selected.localhost/kb/",
                                                        "http://default.localhost/kb/"), {})
            request.assert_not_called()

    def test_explicit_regression_flag_requires_404_and_distinct_source(self):
        selected, default = "http://selected.localhost/kb/", "http://default.localhost/kb/"
        with patch.object(harness, "http", return_value=(200, {}, b"")):
            with self.assertRaises(AssertionError):
                harness.check_default_source(selected, default, require_404=True)
        with patch.object(harness, "http", return_value=(404, {}, b"")) as request:
            self.assertEqual(harness.check_default_source(selected, default, require_404=True),
                             {"default_source_status": 404})
            request.assert_called_once_with(default + "ai/mcp/v1/manifest.json")
            with self.assertRaises(AssertionError):
                harness.check_default_source(selected, selected, require_404=True)


class DistributionTests(unittest.TestCase):
    def test_actual_compose_resolution_preserves_site_override_and_local_defaults(self):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("V8STD_")}
        env.update(V8STD_SITE_IMAGE="local-site:test", V8STD_MCP_IMAGE="local-mcp:test")
        cases = [({}, "http://v8std.localhost:18765/"),
                 ({"V8STD_SITE_PORT": "19875", "V8STD_SITE_PREFIX": "/kb/"},
                  "http://v8std.localhost:19875/kb/"),
                 ({"V8STD_SITE_PORT": "19875", "V8STD_SITE_PREFIX": "/unused/",
                   "V8STD_MCP_SITE_URL": "http://alternate.localhost:19876/knowledge/"},
                  "http://alternate.localhost:19876/knowledge/")]
        for settings, expected in cases:
            with self.subTest(settings=settings):
                resolved = json.loads(subprocess.check_output(
                    ["docker", "compose", "--env-file", os.devnull, "-f", str(ROOT / "compose.yaml"),
                     "--profile", "mcp", "config", "--format", "json"],
                    env={**env, **settings}, text=True, timeout=20))
                mcp = resolved["services"]["mcp"]
                self.assertEqual(mcp["environment"]["V8STD_MCP_SITE_URL"], expected)
                self.assertNotIn("--site-url", mcp["command"])

    def test_images_are_thin_pinned_and_unprivileged(self):
        runtime = (ROOT / "Dockerfile.mcp").read_text()
        static = (ROOT / "Dockerfile.site").read_text()
        for definition in (runtime, static):
            self.assertRegex(definition, r"FROM [^\n]+@sha256:[0-9a-f]{64}")
            self.assertIn("USER 10001:10001", definition)
        self.assertIn('CMD ["--transport", "stdio"]', runtime)
        self.assertIn("retrieval-rules.yml", runtime)
        self.assertIn("v8std_search_features.py", runtime)
        self.assertNotIn("v8std_mcp*.py", runtime)
        self.assertNotIn("COPY docs", runtime)
        self.assertIn("--require-hashes", runtime)

    def test_compose_has_common_address_and_internal_mcp(self):
        compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
        site, mcp = (compose["services"][name] for name in ("site", "mcp"))
        for service in (site, mcp):
            self.assertTrue(service["read_only"])
            self.assertTrue(service["init"])
            self.assertEqual(service["cap_drop"], ["ALL"])
            self.assertNotIn("build", service)
            self.assertEqual(len(service["tmpfs"]), 1)
            self.assertIn("uid=10001,gid=10001", service["tmpfs"][0])
        self.assertTrue(all(port.startswith("127.0.0.1:") for port in site["ports"]))
        self.assertNotIn("ports", mcp)
        self.assertEqual(mcp["profiles"], ["mcp"])
        self.assertEqual(mcp["networks"], ["corpus"])
        self.assertTrue(compose["networks"]["corpus"]["internal"])
        self.assertIn("v8std.localhost", site["networks"]["corpus"]["aliases"])
        self.assertIn("v8std.localhost", mcp["environment"]["V8STD_MCP_SITE_URL"])

    def test_profile_rejects_source_output_overlap(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_local_site import build_local_site
        for output in (ROOT, ROOT / "docs", ROOT / "site", ROOT / "scripts/out"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build_local_site(ROOT, output, "http://v8std.localhost:18765/kb/", "a" * 40)

    def test_catalog_has_long_lived_configurable_stdio(self):
        spec = yaml.safe_load((ROOT / "deploy/docker-catalog/server.yaml").read_text())
        self.assertTrue(spec["longLived"])
        self.assertEqual(spec["run"]["user"], "10001:10001")
        self.assertEqual(spec["run"]["command"], ["--transport", "stdio"])
        self.assertTrue(spec["image"].startswith("ghcr.io/zeegin/v8std-mcp"))
        self.assertEqual(set(spec["run"]["env"]),
                         {"V8STD_MCP_SITE_URL", "V8STD_MCP_MAX_SNIPPET_CHARS"})


@unittest.skipUnless(os.environ.get("V8STD_TEST_LOCAL_BUILD"), "explicit local build acceptance")
class LocalBuildTests(unittest.TestCase):
    def test_actual_isolated_build_and_canonical_snapshot(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_local_site import build_local_site
        from generate_mcp_snapshot import build_snapshot
        from v8std_mcp_snapshot_format import verify_archive

        def hashes():
            return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for folder in ("docs", "overrides", "site")
                    for p in (ROOT / folder).rglob("*") if p.is_file()}

        before = hashes()
        source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        with tempfile.TemporaryDirectory(prefix="v8std-local-test-") as temporary:
            output = Path(temporary) / "site"
            build_local_site(ROOT, output, "http://v8std.localhost:18765/kb/", source_sha)
            manifest = json.loads((output / "ai/mcp/v1/manifest.json").read_bytes())
            self.assertFalse(manifest["archive"]["path"].startswith(("/", "http")))
            archive = (output / "ai/mcp/v1" / manifest["archive"]["path"]).read_bytes()
            canonical, _ = build_snapshot(ROOT / "docs", source_sha, "https://v8std.ru/")
            self.assertEqual(archive, canonical)
            verify_archive(archive, manifest)
            self.assertTrue((output / "LICENSES/index.html").is_file())
            html = (output / "std/437/index.html").read_text()
            self.assertNotIn("u.ingvar.pro", html)
            self.assertNotIn("fonts.googleapis.com", html)
            self.assertTrue("http://v8std.localhost:18765/kb/" in html_module.unescape(html))
        self.assertEqual(before, hashes())


if __name__ == "__main__":
    unittest.main()
