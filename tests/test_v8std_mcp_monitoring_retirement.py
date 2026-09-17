"""Real nginx conformance; opt in with V8STD_MONITORING_RETIREMENT_DOCKER=1.

Uses the pinned, already-local nginx image from test_v8std_mcp_release_docker.
No image pull, build, production access, or shared Docker resource cleanup.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]
NGINX = "sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c"


@unittest.skipUnless(
    os.environ.get("V8STD_MONITORING_RETIREMENT_DOCKER") == "1",
    "explicit disposable Docker evidence",
)
class MonitoringRetirementTests(unittest.TestCase):
    @staticmethod
    def docker(*args: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=30,
        )
        if result.returncode:
            raise AssertionError(f"docker {args}: {result.stdout}{result.stderr}")
        return result

    @classmethod
    def setUpClass(cls) -> None:
        cls.docker("image", "inspect", NGINX)
        temporary = tempfile.TemporaryDirectory(prefix="v8std-monitoring-retirement-")
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        config, web, indexes = (directory / name for name in ("nginx", "web", "indexes"))
        for path in (config, web, indexes):
            path.mkdir(mode=0o755)
        for name in ("edge-http.conf", "edge-locations.conf"):
            shutil.copyfile(ROOT / "delivery/vps/nginx" / name, config / name)
        (config / "v8std-release").mkdir()
        (config / "v8std-release/upstream.conf").write_text(
            "server 127.0.0.1:9;\n", encoding="utf-8",
        )
        (config / "nginx.conf").write_text(
            "worker_processes 1; pid /tmp/nginx.pid;\n"
            "error_log /dev/stderr warn; events { worker_connections 128; }\n"
            "http { access_log off; client_body_temp_path /tmp/client;\n"
            "proxy_temp_path /tmp/proxy; fastcgi_temp_path /tmp/fastcgi;\n"
            "uwsgi_temp_path /tmp/uwsgi; scgi_temp_path /tmp/scgi;\n"
            "include /etc/nginx/edge-http.conf;\n"
            "server { listen 8080; server_name localhost; root /srv/web;\n"
            "include /etc/nginx/edge-locations.conf;\n"
            "} }\n",
            encoding="utf-8",
        )
        (web / "index.html").write_bytes(b"public-root-fixture\n")
        legacy = web / "monitoring"
        legacy.mkdir()
        (legacy / "index.html").write_bytes(b"private-monitoring-sentinel\n")
        (legacy / "stats.json").write_bytes(b'{"data":"private-monitoring-sentinel"}\n')
        snapshot = indexes / ("a" * 64)
        snapshot.mkdir()
        (snapshot / "snapshot.tar.gz").write_bytes(b"snapshot-fixture\n")

        cls.name = "v8std-monitoring-retirement-" + uuid.uuid4().hex
        cls.owner_label = "pro.v8std.monitoring-retirement=" + cls.name
        cls.addClassCleanup(cls.cleanup_container)
        cls.docker(
            "create", "--name", cls.name, "--pull=never",
            "--label", cls.owner_label, "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--init", "--user=10001:10001",
            "--memory=128m", "--memory-swap=128m", "--cpus=1", "--pids-limit=128",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=64m", "-p", "127.0.0.1::8080",
            "--mount", f"type=bind,source={config},target=/etc/nginx,readonly",
            "--mount", f"type=bind,source={web},target=/srv/web,readonly",
            "--mount", f"type=bind,source={indexes},target=/srv/v8std-indexes/v1,readonly",
            "--entrypoint=nginx", NGINX, "-g", "daemon off;",
        )
        cls.docker("start", cls.name)
        info = json.loads(cls.docker("container", "inspect", cls.name).stdout)[0]
        binding = info["NetworkSettings"]["Ports"]["8080/tcp"]
        if len(binding) != 1 or binding[0]["HostIp"] != "127.0.0.1":
            raise AssertionError(f"fixture must publish only on loopback: {binding}")
        cls.port = int(binding[0]["HostPort"])
        check = cls.docker("exec", cls.name, "nginx", "-t")
        print(f"\n{cls.name}: {check.stderr.strip()}", flush=True)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                cls.request("/")
                return
            except OSError:
                time.sleep(0.1)
        raise AssertionError(cls.docker("logs", cls.name).stderr)

    @classmethod
    def cleanup_container(cls) -> None:
        # An exact UUID name plus owner label prevents removal of another fixture.
        owned = cls.docker(
            "container", "ls", "--all", "--quiet", "--no-trunc",
            "--filter", "label=" + cls.owner_label,
            "--filter", "name=^/" + cls.name + "$",
        ).stdout.split()
        if len(owned) > 1:
            raise AssertionError(f"ambiguous fixture ownership: {owned}")
        for container_id in owned:
            cls.docker("container", "rm", "--force", "--volumes", container_id)
        remaining = cls.docker(
            "container", "ls", "--all", "--quiet",
            "--filter", "label=" + cls.owner_label,
        ).stdout.strip()
        if remaining:
            raise AssertionError(f"owned fixture remains: {remaining}")
        print(f"\ncleanup {cls.name}: owned containers absent", flush=True)

    @classmethod
    def request(cls, path: str, method: str = "GET") -> tuple[int, dict, bytes]:
        client = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=5)
        try:
            client.request(method, path)
            response = client.getresponse()
            return (
                response.status,
                {key.lower(): value for key, value in response.getheaders()},
                response.read(),
            )
        finally:
            client.close()

    def test_retired_paths_never_serve_legacy_files_or_redirect(self) -> None:
        # Missing either tombstone, a redirect, or cacheable errors breaks this.
        for method in ("GET", "HEAD", "POST"):
            for path in (
                "/monitoring", "/monitoring?x=1", "/monitoring/",
                "/monitoring/index.html", "/monitoring/stats.json",
                "/monitoring/stats.json?x=1", "/monitoring/unknown",
            ):
                with self.subTest(method=method, path=path):
                    status, headers, body = self.request(path, method)
                    self.assertEqual(status, 410)
                    self.assertEqual(headers.get("cache-control"), "no-store")
                    self.assertNotIn(b"private-monitoring-sentinel", body)
                    self.assertNotIn("location", headers)
                    if method == "HEAD":
                        self.assertEqual(body, b"")

    def test_public_root_is_still_served(self) -> None:
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"public-root-fixture\n")
        self.assertNotEqual(headers.get("cache-control"), "no-store")

    def test_health_and_mcp_keep_their_dead_upstream_boundaries(self) -> None:
        for path, method, expected in (
            ("/healthz", "GET", 502), ("/version", "GET", 502),
            ("/mcp", "GET", 405), ("/mcp", "POST", 503),
            ("/mcp", "HEAD", 503),
        ):
            with self.subTest(path=path, method=method):
                status, headers, body = self.request(path, method)
                self.assertEqual(status, expected)
                self.assertNotEqual(headers.get("cache-control"), "no-store")
                self.assertNotIn(b"private-monitoring-sentinel", body)
                if expected == 503:
                    self.assertEqual(headers.get("retry-after"), "1")
                if expected == 405:
                    self.assertEqual(headers.get("allow"), "POST, HEAD")

    def test_index_download_stays_available_with_dead_upstream(self) -> None:
        path = "/indexes/v1/" + "a" * 64 + "/snapshot.tar.gz"
        for method in ("GET", "HEAD"):
            with self.subTest(method=method):
                status, headers, body = self.request(path, method)
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("content-type"), "application/gzip")
                self.assertEqual(headers.get("cache-control"), "public, max-age=31536000, immutable")
                self.assertEqual(body, b"snapshot-fixture\n" if method == "GET" else b"")
        for target, method, expected in (
            (path, "POST", 403), ("/indexes/", "GET", 404),
            ("/indexes/v1/unknown/snapshot.tar.gz", "GET", 404),
        ):
            with self.subTest(path=target, method=method):
                status, headers, _ = self.request(target, method)
                self.assertEqual(status, expected)
                self.assertNotIn("immutable", headers.get("cache-control", ""))


if __name__ == "__main__":
    unittest.main()
