"""Explicit local Task5 evidence; no pull/build/registry or host configuration.

Run V8STD_TASK5_DOCKER=1 .venv/bin/python -m unittest
tests.test_v8std_mcp_release_docker -v. The retained Task4 image supplies locked
dependencies; only Task5 runtime modules are mounted read-only. This is not a
claim that an image containing the new code has already been published.
"""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tarfile
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from tests import mcp_snapshot_fixtures as fixture
from tests.test_v8std_mcp_release import port
import v8std_mcp_release as release

ROOT = Path(__file__).resolve().parents[1]
NGINX = "sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c"
RUNTIME = "sha256:bec25fa5b9f240225db206c5e21d35a8c28e2d4ae30b1b878d272eacd9df1031"


@unittest.skipUnless(os.environ.get("V8STD_TASK5_DOCKER") == "1", "explicit disposable Docker evidence")
class DockerReleaseTests(unittest.TestCase):
    def docker(self, *args, check=True):
        self.calls.append(["docker", *map(str, args)])
        result = subprocess.run(["docker", *map(str, args)], capture_output=True, timeout=60)
        if check:
            details = result.stderr.decode()
            if result.returncode and args[0] == "exec":
                details += subprocess.run(["docker", "logs", str(args[1])], capture_output=True).stderr.decode()
            self.assertEqual(result.returncode, 0, details)
        return result

    def test_native_nginx_static_independence_hold_and_admission(self):
        self.calls = []
        name = "v8std-task5-" + uuid.uuid4().hex[:12]
        network, nginx, runtime, volume = (name + "-" + suffix for suffix in ("net", "edge", "runtime", "cache"))
        control_volume, writer = name + "-control", name + "-writer"
        endpoint_port = port()
        source_url = f"http://v8std-task5.localhost:{endpoint_port}/"
        archive, manifest = fixture.snapshot_fixture()
        archive_hash = manifest["archive"]["sha256"]
        token = "a" * 32
        evidence = {"runtime_image": RUNTIME, "nginx_image": NGINX, "source_sha_fixture": manifest["source_sha"],
                    "limits": {"nginx_workers": 2, "mcp_active": 8, "downloads": 2, "download_rate": "1m",
                               "runtime_memory": "512m", "nginx_memory": "128m", "cpus_each": 1}}
        with tempfile.TemporaryDirectory(prefix="v8std-task5-docker-") as directory:
            directory = Path(directory)
            config, static, source = [directory / x for x in ("nginx", "static", "source")]
            for path in (config, static, source):
                path.mkdir(mode=0o755)
            for filename in ("edge-http.conf", "edge-locations.conf"):
                shutil.copyfile(ROOT / "deploy/container" / filename, config / filename)
            (config / "v8std-release").mkdir()
            upstream = config / "v8std-release/upstream.conf"
            upstream.write_text("server 127.0.0.1:9 max_conns=8;\n")
            (config / "nginx.conf").write_text(
                "worker_processes 2; worker_shutdown_timeout 30s; pid /tmp/nginx.pid;\n"
                "error_log /dev/stderr warn; events { worker_connections 128; }\n"
                "http { access_log off; client_body_temp_path /tmp/client; proxy_temp_path /tmp/proxy;\n"
                "fastcgi_temp_path /tmp/fastcgi; uwsgi_temp_path /tmp/uwsgi; scgi_temp_path /tmp/scgi;\n"
                "include /etc/nginx/edge-http.conf; server {\n"
                f"listen {endpoint_port}; server_name v8std-task5.localhost;\n"
                "include /etc/nginx/edge-locations.conf;\n"
                "location = /ai/mcp/v1/manifest.json { alias /srv/source/manifest.json; etag off; if_modified_since off; add_header Cache-Control 'max-age=0, must-revalidate'; }\n"
                'location ~ "^/ai/mcp/v1/([0-9a-f]{64})/snapshot[.]tar[.]gz$" { alias /srv/v8std-indexes/v1/$1/snapshot.tar.gz; types {} default_type application/gzip; }\n'
                "} }\n")
            (static / archive_hash).mkdir()
            (static / archive_hash / "snapshot.tar.gz").write_bytes(archive)
            (source / "manifest.json").write_bytes(release.canonical_json(manifest))

            def publish_control(*, unreadable=False):
                # Native Linux root writer with the recovery service's umask.
                # Only this disposable named volume is writable; no Docker socket.
                code = ("import os,sys,json; from pathlib import Path; "
                        "sys.path.insert(0,'/opt/v8std/scripts'); import v8std_mcp_release as r; "
                        "os.umask(0o077); p=Path('/state/slots/runtime/control'); ")
                if unreadable:
                    code += "os.chmod(p/'control.json',0); print('{}')"
                else:
                    code += (f"r.HostAdapter(Path('/state'),{{}}).control({{'release_id':'runtime'}},'hold',{token!r},{manifest!r}); "
                             "print(json.dumps({'directory_mode':oct(p.stat().st_mode & 0o777),"
                             "'file_mode':oct((p/'control.json').stat().st_mode & 0o777),"
                             "'directory_uid':p.stat().st_uid,'file_uid':(p/'control.json').stat().st_uid}))")
                result = self.docker("run", "--rm", "--name", writer, "--pull=never", "--network=none",
                    "--user=0:0", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--init",
                    "--memory=128m", "--memory-swap=128m", "--cpus=1", "--pids-limit=128",
                    "--label=pro.v8std.test=task5", "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
                    "--mount", f"type=volume,source={control_volume},target=/state",
                    "--mount", f"type=bind,source={ROOT / 'scripts/v8std_mcp_release.py'},target=/opt/v8std/scripts/v8std_mcp_release.py,readonly",
                    "--entrypoint=python", RUNTIME, "-I", "-c", code)
                return json.loads(result.stdout)

            def request(path, method="GET", body=None):
                client = http.client.HTTPConnection("127.0.0.1", endpoint_port, timeout=10)
                try:
                    client.request(method, path, body)
                    result = client.getresponse()
                    return result.status, dict(result.getheaders()), result.read()
                finally:
                    client.close()

            def ready():
                until = time.monotonic() + 15
                observed = None
                while time.monotonic() < until:
                    try:
                        status, _, body = request("/healthz")
                        observed = (status, body)
                        if status == 200 and json.loads(body).get("hold_token") == token:
                            return json.loads(body)
                    except (OSError, ValueError):
                        pass
                    time.sleep(.1)
                logs = [self.docker("logs", x, check=False) for x in (runtime, nginx)]
                self.fail(repr(observed) + "\n" + "\n".join((x.stdout + x.stderr).decode() for x in logs))

            self.docker("network", "create", "--label", "pro.v8std.test=task5", network)
            self.docker("volume", "create", "--label", "pro.v8std.test=task5", volume)
            self.docker("volume", "create", "--label", "pro.v8std.test=task5", control_volume)
            try:
                permissions = publish_control()
                self.assertEqual(permissions, {"directory_mode": "0o755", "file_mode": "0o644",
                                               "directory_uid": 0, "file_uid": 0})
                evidence["root_control_umask_0077"] = permissions
                common = ["--pull=never", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                          "--init", "--user=10001:10001", "--cpus=1", "--pids-limit=128",
                          "--network", network, "--label=pro.v8std.test=task5", "--tmpfs=/tmp:rw,noexec,nosuid,size=64m"]
                self.docker("run", "-d", "--name", nginx, *common, "--memory=128m", "--memory-swap=128m",
                    "--network-alias=v8std-task5.localhost", "-p", f"127.0.0.1:{endpoint_port}:{endpoint_port}",
                    "--mount", f"type=bind,source={config},target=/etc/nginx,readonly",
                    "--mount", f"type=bind,source={static},target=/srv/v8std-indexes/v1,readonly",
                    "--mount", f"type=bind,source={source},target=/srv/source,readonly",
                    "--entrypoint=nginx", NGINX, "-g", "daemon off;")
                evidence["nginx_t"] = self.docker("exec", nginx, "nginx", "-t").stderr.decode().strip()
                modules = []
                for module in ("v8std_mcp_hold.py", "v8std_mcp_runtime.py", "v8std_mcp_snapshots.py"):
                    modules.extend(["--mount", f"type=bind,source={ROOT / 'scripts' / module},target=/opt/v8std/scripts/{module},readonly"])
                self.docker("run", "-d", "--name", runtime, *common, "--memory=512m", "--memory-swap=512m",
                    "--mount", f"type=volume,source={volume},target=/var/lib/v8std-mcp",
                    "--mount", f"type=volume,source={control_volume},target=/run/v8std-release,volume-subpath=slots/runtime/control,readonly", *modules,
                    RUNTIME, "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000",
                    "--site-url", source_url, "--refresh-seconds", "1", "--allowed-host", "127.0.0.1")
                upstream.write_text(f"server {runtime}:8000 max_conns=8;\n")
                self.docker("exec", nginx, "nginx", "-t")
                self.docker("exec", nginx, "nginx", "-s", "reload")
                health = ready()
                evidence["health"] = health
                publish_control(unreadable=True)
                until = time.monotonic() + 5
                while True:
                    state = json.loads(request("/healthz")[2])
                    if state.get("hold_token") is None:
                        break
                    self.assertLess(time.monotonic(), until)
                    time.sleep(.05)
                self.assertTrue(state["ready"])
                self.assertEqual(state["archive_sha256"], archive_hash)
                self.assertEqual(publish_control(), permissions)  # Same exact token/manifest.
                self.assertEqual(ready()["release_control_token"], token)
                evidence["same_token_read_failure_recovery"] = "ready; ack revoked; same command reacknowledged"
                record = {"runtime_source_sha": health["runtime_sha"], "corpus_id": manifest["corpus_id"],
                          "archive_sha256": archive_hash, "hold_token": token}
                release.smoke(f"http://127.0.0.1:{endpoint_port}", record, time.monotonic() + 30)
                # Exercise the production switch method against a real nginx -t
                # rejection. Failed validation must restore include before reload.
                saved_upstream = upstream.read_bytes()
                main_config = config / "nginx.conf"
                saved_config = main_config.read_bytes()
                main_config.write_bytes(saved_config + b"invalid_task5_directive;\n")
                nginx_calls = []
                def native_nginx(argv, deadline):
                    nginx_calls.append(argv)
                    result = self.docker("exec", nginx, *argv, check=False)
                    if result.returncode:
                        raise release.ReleaseError("command_failed")
                    return result.stdout
                adapter = release.HostAdapter(directory, {"nginx_include": str(upstream)})
                with patch.object(release, "run", native_nginx), self.assertRaises(release.ReleaseError):
                    adapter.switch({"port": 9}, time.monotonic() + 5)
                self.assertEqual(nginx_calls, [["nginx", "-t"]])
                self.assertEqual(upstream.read_bytes(), saved_upstream)
                main_config.write_bytes(saved_config)
                upstream.chmod(0o644)
                self.docker("exec", nginx, "nginx", "-t")
                self.assertEqual(request("/healthz")[0], 200)
                evidence["invalid_nginx_switch"] = "rejected; previous include restored; no reload; endpoint 200"
                info = json.loads(self.docker("inspect", runtime).stdout)[0]
                self.assertTrue(info["HostConfig"]["ReadonlyRootfs"])
                self.assertEqual(info["Config"]["User"], "10001:10001")
                self.assertTrue(info["HostConfig"]["Init"])
                self.assertIn("ALL", info["HostConfig"]["CapDrop"])
                evidence["container_image_id"] = info["Image"]
                # Read local OCI export: descriptor type/membership are explicit,
                # independent of Docker's ambiguous .Id representation.
                saved = directory / "image.tar"
                self.docker("image", "save", "-o", saved, RUNTIME)
                with tarfile.open(saved) as tar:
                    index_raw = tar.extractfile("blobs/sha256/" + RUNTIME[7:]).read()
                    index = json.loads(index_raw)
                    member = next(x for x in index["manifests"] if x.get("platform", {}).get("architecture") == "arm64")
                    child_raw = tar.extractfile("blobs/sha256/" + member["digest"][7:]).read()
                evidence["descriptor_types"] = release.verify_descriptors(index_raw, child_raw,
                    {"image_digest": RUNTIME, "platform_digest": member["digest"]}, "linux/arm64")
                self.assertIn(info["Image"], evidence["descriptor_types"])
                path = f"/indexes/v1/{archive_hash}/snapshot.tar.gz"
                before = request(path)
                self.assertEqual(before[0], 200)
                self.assertEqual(release.digest(before[2]), archive_hash)
                self.assertIn("immutable", before[1]["Cache-Control"])
                self.assertNotIn("Content-Encoding", before[1])
                self.assertEqual(request(path, "HEAD")[1]["Content-Length"], str(len(archive)))
                denied = request(path, "POST", b"x")
                self.assertEqual(denied[0], 403)
                self.assertNotIn("Cache-Control", denied[1])
                missing = request("/indexes/v1/" + "f" * 64 + "/snapshot.tar.gz")
                self.assertEqual(missing[0], 404)
                self.assertNotIn("Cache-Control", missing[1])
                self.docker("stop", "--time=5", runtime)
                after = request(path)
                self.assertEqual((after[0], after[2]), (before[0], before[2]))
                for header in ("Content-Length", "ETag", "Cache-Control"):
                    self.assertEqual(after[1][header], before[1][header])
                evidence["runtime_stopped_static_sha256"] = release.digest(after[2])
                # 8 same-NAT downloads, 2 globally admitted across 2 workers.
                # Synthetic hash-addressed bytes exercise transport capacity only.
                blob = os.urandom(3 * 1024 * 1024)
                key = release.digest(blob)
                (static / key).mkdir()
                (static / key / "snapshot.tar.gz").write_bytes(blob)
                with ThreadPoolExecutor(max_workers=8) as pool:
                    responses = list(pool.map(lambda _: request(f"/indexes/v1/{key}/snapshot.tar.gz"), range(8)))
                codes = [value[0] for value in responses]
                self.assertIn(200, codes)
                self.assertIn(429, codes)
                self.assertLessEqual(codes.count(200), 2)
                for code, headers, _ in responses:
                    if code == 429:
                        self.assertEqual(headers["Retry-After"], "1")
                        self.assertNotIn("Cache-Control", headers)
                evidence["download_statuses"] = codes
                self.assertEqual(request("/mcp", "GET")[0], 405)
                unavailable = request("/mcp", "POST", b"{}")
                self.assertEqual(unavailable[0], 503)
                self.assertEqual(unavailable[1]["Retry-After"], "1")
                evidence["commands"] = self.calls
                print("TASK5_DOCKER_EVIDENCE=" + json.dumps(evidence, sort_keys=True))
            finally:
                for container in (runtime, nginx, writer):
                    info = self.docker("inspect", container, check=False)
                    if info.returncode == 0:
                        self.assertEqual(json.loads(info.stdout)[0]["Config"]["Labels"]["pro.v8std.test"], "task5")
                        self.docker("rm", "-f", container)
                self.docker("volume", "rm", volume)
                self.docker("volume", "rm", control_volume)
                self.docker("network", "rm", network)


if __name__ == "__main__":
    unittest.main()
