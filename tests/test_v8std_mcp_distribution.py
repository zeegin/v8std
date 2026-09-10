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

import yaml

ROOT = Path(__file__).resolve().parents[1]


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
