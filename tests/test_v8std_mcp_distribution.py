"""Focused distribution checks; real Docker/browser acceptance is opt-in."""
import hashlib
import html as html_module
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_mcp_container as harness


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
