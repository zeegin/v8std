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
import dev.checks.check_mcp_container as harness


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
            built = _context_command(["docker", "build", "--progress=plain", "-f", "delivery/ci/Dockerfile",
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
    def test_every_runtime_copy_survives_actual_buildkit_context_filter(self):
        definition = (ROOT / "delivery/mcp/Dockerfile").read_text().replace("\\\n", " ")
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
        definition = (ROOT / "delivery/mcp/Dockerfile").read_text().replace("\\\n", " ")
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
                ["docker", "build", "--progress=plain", "--file", "delivery/mcp/Dockerfile",
                 "--build-arg", "SOURCE_SHA=" + "0" * 40, "--tag", fixture.tag, "."], timeout=600)
            self.assertEqual(built.returncode, 0, built.stdout)
            probe = (
                "import hashlib,json,os,pathlib,sys; "
                "sys.path.insert(0,'/opt/v8std/scripts'); from runtime import v8std_mcp_server, v8std_mcp_hold; "
                "assert os.getuid()==10001; "
                "print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() "
                "for p in json.loads(sys.argv[1])}))"
            )
            result = fixture.run(["-c", probe, json.dumps(list(expected))])
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout), expected)
            checked = fixture.run(["-m", "pip", "check"])
            self.assertEqual(checked.returncode, 0, checked.stdout)


class AcceptanceHelperTests(unittest.TestCase):
    def test_real_http_server_rejects_extra_tools(self):
        from tests.test_v8std_mcp_tools_only import http_rpc, initialize
        from runtime.v8std_mcp_index import V8StdIndex
        index = V8StdIndex(pages_path=ROOT / "docs/ai/pages.jsonl",
                          vectors_path=ROOT / "docs/ai/search-vectors.jsonl")
        index.load()
        with http_rpc(index) as rpc:
            initialize(rpc)
            def request(method, params=None):
                return rpc.call(method, params)["result"]
            self.assertEqual(harness.check_tools(request, "https://v8std.ru/")[0], "std437")
            def aggregate(method, params=None):
                result = request(method, params)
                if method == "tools/list":
                    result["tools"].append({"name": "unexpected-tool"})
                return result
            with self.assertRaises(AssertionError):
                harness.check_tools(aggregate, "https://v8std.ru/")

    def test_resource_denial_is_semantic_and_rejects_payload_or_wrong_typed_id(self):
        check = getattr(harness, "validate_resource_denial", None)
        self.assertTrue(callable(check), "acceptance needs a semantic full-envelope denial verifier")
        good = {"jsonrpc": "2.0", "id": 7, "error": {"code": -32601, "message": "Unsupported method"}}
        check(good, 7)
        for value in ({**good, "id": "7"}, {**good, "id": True}, {**good, "jsonrpc": "1.0"},
                      {**good, "result": {}}, {**good, "error": {"code": -32602, "message": "bad params"}},
                      {**good, "error": {**good["error"], "data": "corpus"}},
                      {**good, "error": {"code": -32601, "message": "x" * 1024}}):
            with self.subTest(value=value), self.assertRaises(AssertionError):
                check(value, 7)


    def test_tool_content_rejects_embedded_resources_even_with_structured_content(self):
        reply = {"isError": False, "content": [{"type": "resource", "resource": {
            "uri": "v8std://llms.txt", "text": "corpus"}}], "structuredContent": {"found": True}}
        with self.assertRaises(AssertionError):
            harness.content(reply)




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
                    ["docker", "compose", "--env-file", os.devnull, "-f", str(ROOT / "delivery/local/compose.yaml"),
                     "--profile", "mcp", "config", "--format", "json"],
                    env={**env, **settings}, text=True, timeout=20))
                mcp = resolved["services"]["mcp"]
                self.assertEqual(mcp["environment"]["V8STD_MCP_SITE_URL"], expected)
                self.assertNotIn("--site-url", mcp["command"])

    def test_images_are_thin_pinned_and_unprivileged(self):
        runtime = (ROOT / "delivery/mcp/Dockerfile").read_text()
        static = (ROOT / "delivery/site/Dockerfile").read_text()
        for definition in (runtime, static):
            self.assertRegex(definition, r"FROM [^\n]+@sha256:[0-9a-f]{64}")
            self.assertIn("USER 10001:10001", definition)
        self.assertIn('CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]', runtime)
        self.assertIn("retrieval-rules.yml", runtime)
        self.assertIn("v8std_search_features.py", runtime)
        self.assertNotIn("v8std_mcp*.py", runtime)
        self.assertNotIn("COPY docs", runtime)
        self.assertIn("--require-hashes", runtime)

    def test_compose_has_common_address_and_internal_mcp(self):
        compose = yaml.safe_load((ROOT / "delivery/local/compose.yaml").read_text())
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
        from delivery.site.build_local_site import build_local_site
        for output in (ROOT, ROOT / "docs", ROOT / "site", ROOT / "scripts/out"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build_local_site(ROOT, output, "http://v8std.localhost:18765/kb/", "a" * 40)



@unittest.skipUnless(os.environ.get("V8STD_TEST_LOCAL_BUILD"), "explicit local build acceptance")
class LocalBuildTests(unittest.TestCase):
    def test_actual_isolated_build_and_canonical_snapshot(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from delivery.site.build_local_site import build_local_site
        from delivery.index.generate_mcp_snapshot import build_snapshot
        from runtime.v8std_mcp_snapshot_format import verify_archive

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
