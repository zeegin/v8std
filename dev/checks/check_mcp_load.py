#!/usr/bin/env python3
"""Bounded disposable local acceptance, not a production capacity benchmark.

Uses prebuilt exact-source images, private fixture logging, retained API budgets
and real corpus reads. No credentials, Docker socket mount or global setup.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import tempfile
import time
import uuid

import httpx

from delivery.ci.publish_mcp_artifacts import bounded_command, require, save
from dev.checks.check_mcp_container import (RESOURCE_REQUESTS, content, validate_envelope, validate_resource_denial)
from runtime.v8std_mcp_snapshot_format import MAX_ARCHIVE_BYTES, validate_manifest, verify_archive

ROOT = Path(__file__).resolve().parents[2]
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "bounded-load", "version": "1"}}}
RESOURCE_PROBE = ("import json,pathlib,os; p=pathlib.Path('/sys/fs/cgroup'); "
    "files=['memory.current','memory.peak','memory.events','cpu.stat']; "
    "out={n:(p/n).read_text() for n in files}; out['fd_count']=0; out['runtime_pids']=[]\n"
    "for d in pathlib.Path('/proc').iterdir():\n"
    " if d.name.isdigit():\n"
    "  try:\n"
    "   if d.stat().st_uid==os.getuid(): out['fd_count']+=len(list((d/'fd').iterdir())); out['runtime_pids'].append(int(d.name))\n"
    "  except (PermissionError,FileNotFoundError): pass\n"
    "print(json.dumps(out))")


def request(number):
    slot = number % 20
    if slot < 7:
        kind, tool, args = "search", "v8std_search", {"query": "модальные окна", "limit": 5}
    elif slot < 12:
        kind, tool, args = "page", "v8std_get_page", {"id_or_alias_or_url": "std437"}
    elif slot < 15:
        kind, tool, args = "snippet", "v8std_explain_snippet", {"snippet": 'Предупреждение("Текст");', "limit": 5}
    elif slot < 17:
        kind, tool, args = "diagnostics", "v8std_explain_diagnostics", {"codes": ["bslls:UsingModalWindows"]}
    else:
        kind, tool, args = "related", "v8std_get_related", {"id_or_alias_or_url": "std437"}
    return kind, {"jsonrpc": "2.0", "id": number + 2, "method": "tools/call", "params": {"name": tool, "arguments": args}}


def valid_reply(kind, body):
    try:
        reply = json.loads(body)
        validate_envelope(reply, reply["id"])
        result = reply["result"]
        if "error" in reply or result.get("isError"):
            return False
        if kind == "initialize":
            return (result.get("serverInfo", {}).get("name") == "v8std"
                    and result.get("protocolVersion") == INIT["params"]["protocolVersion"]
                    and isinstance(result.get("capabilities"), dict) and "resources" not in result["capabilities"])
        payload = content(result)
        if kind == "search":
            return bool(payload.get("results")) and all(row.get("id") for row in payload["results"])
        if kind == "page":
            return (payload.get("found") is True and payload.get("page", {}).get("id") == "std437"
                    and bool(payload["page"].get("body_markdown")))
        if kind == "related":
            return (payload.get("found") is True and payload.get("id") == "std437"
                    and bool(payload.get("related"))
                    and all(row.get("id") and row.get("relation") and row.get("url") for row in payload["related"]))
        if kind in {"snippet", "diagnostics"}:
            return any(row.get("id") == "bslls:UsingModalWindows" for row in payload.get("diagnostics", []))
        return False
    except (AssertionError, AttributeError, KeyError, ValueError, TypeError, IndexError):
        return False


def valid_wire_reply(kind, body, message, media):
    try:
        require(media.split(";")[0] == "application/json", "json_only_response")
        reply = validate_envelope(json.loads(body), message["id"])
        if kind == "resource_denial":
            validate_resource_denial(reply, message["id"])
            return True
        return valid_reply(kind, body)
    except (AssertionError, KeyError, TypeError, ValueError):
        return False


def summarize(rows, seconds):
    success = sorted(row["seconds"] for row in rows if row["outcome"] == "ok")
    def percentile(percent, values=success):
        return round(values[max(0, math.ceil(len(values) * percent) - 1)], 6) if values else None
    kinds = {}
    for kind in sorted({row["kind"] for row in rows}):
        group = [row for row in rows if row["kind"] == kind]
        times = sorted(row["seconds"] for row in group if row["outcome"] == "ok")
        kinds[kind] = {"requests": len(group), "successes": len(times), "success_p95_seconds": percentile(.95, times),
                       "success_p99_seconds": percentile(.99, times), "response_bytes": sum(row["bytes"] for row in group)}
    return {"requests": len(rows), "admitted_successes": len(success),
            "retryable_429_503": sum(row["outcome"] == "admission" for row in rows),
            "unexpected_errors": sum(row["outcome"] not in {"ok", "admission"} for row in rows),
            "successful_rps": round(len(success) / seconds, 3), "success_p95_seconds": percentile(.95),
            "success_p99_seconds": percentile(.99), "response_bytes": sum(row["bytes"] for row in rows),
            "statuses": dict(Counter(str(row["status"]) for row in rows)),
            "outcomes": dict(Counter(row["outcome"] for row in rows)),
            "by_kind": kinds}


def edge_config(upstream):
    require(upstream in {"mcp-a", "mcp-b"}, "fixture_upstream")
    http = (ROOT / "delivery/vps/nginx/edge-http.conf").read_text()
    http = http.replace("include /etc/nginx/v8std-release/upstream.conf;",
                        "server " + upstream + ":8000;")
    locations = (ROOT / "delivery/vps/nginx/edge-locations.conf").read_text()
    server = "server { listen 8000; server_name localhost;\n" + locations + "\n}\n"
    return ("worker_processes 1; worker_rlimit_nofile 131072; pid /tmp/nginx.pid;\n"
            "error_log /dev/stderr warn; events { worker_connections 65536; }\nhttp {\n"
            "access_log off; client_body_temp_path /tmp/client; proxy_temp_path /tmp/proxy;\n"
            "fastcgi_temp_path /tmp/fastcgi; uwsgi_temp_path /tmp/uwsgi; scgi_temp_path /tmp/scgi;\n"
            + http + server + "\n}\n")


class Stack:
    """Own only exact UUID-labelled fixtures, including uncertain failed starts."""
    def __init__(self):
        self.prefix = "v8std-load-" + uuid.uuid4().hex[:16]
        self.owned = []

    def docker(self, *args, seconds=30):
        return bounded_command(["docker", *map(str, args)], seconds=seconds, limit=2 * 1024 * 1024).decode()

    def __enter__(self):
        return self

    def __exit__(self, kind, primary, traceback):
        failures = []
        for resource in ("container", "volume", "network"):
            for item, name in self.owned:
                if item != resource:
                    continue
                try:
                    query = (resource, "ls", "--filter", "name=" + ("^/" + name + "$" if item == "container" else name),
                             "--format", "{{.Names}}" if item == "container" else "{{.Name}}")
                    if item == "container":
                        query += ("-a",)
                    names = self.docker(*query).splitlines()
                    if not names:
                        continue
                    require(names == [name], "cleanup_exact_target")
                    info = json.loads(self.docker(*(("inspect", name) if item == "container" else (item, "inspect", name))))[0]
                    labels = info["Config"]["Labels"] if item == "container" else info["Labels"]
                    require(labels.get("pro.v8std.load") == self.prefix, "cleanup_ownership")
                    self.docker(*(("rm", "-f", name) if item == "container" else (item, "rm", name)))
                    require(not self.docker(*query).strip(), "cleanup_remaining")
                except Exception as error:
                    failures.append(item + " " + name + ": " + str(error))
        if failures:
            message = "owned load fixture cleanup failed: " + "; ".join(failures)
            if primary is None:
                raise RuntimeError(message)
            primary.add_note(message)
        return False

    def create(self, kind, suffix, *args):
        name = self.prefix + "-" + suffix
        self.owned.append((kind, name))
        self.docker(kind, "create", "--label", "pro.v8std.load=" + self.prefix, *args, name)
        return name

    def launch(self, suffix, image, *args, command=(), memory="1536m", cpus="2", user="10001:10001", networks=()):
        name = self.prefix + "-" + suffix
        self.owned.append(("container", name))
        self.docker("create", "--name", name, "--pull=never", "--label", "pro.v8std.load=" + self.prefix,
                    "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--init", "--user", user,
                    "--memory", memory, "--memory-swap", memory, "--cpus", cpus, "--pids-limit", "128",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m,uid=10001,gid=10001", *args, image, *command, seconds=45)
        for network, alias in networks:
            self.docker("network", "connect", "--alias", alias, network, name)
        self.docker("start", name)
        return name

    def inspect(self, name):
        return json.loads(self.docker("inspect", name))[0]


async def measure(client, url, kind, message=None, *, headers=None):
    started = time.monotonic()
    row = {"kind": kind, "status": 0, "bytes": 0, "retry_after": None}
    try:
        async with client.stream("POST" if message else "GET", url, json=message, headers=headers) as response:
            row.update(status=response.status_code, retry_after=response.headers.get("retry-after"))
            chunks = []
            async for chunk in response.aiter_bytes():
                row["bytes"] += len(chunk)
                require(row["bytes"] <= 64 * 1024 * 1024, "load_client_response_bound")
                if message:
                    chunks.append(chunk)
            if row["status"] in {429, 503}:
                row["outcome"] = "admission" if row["retry_after"] else "overload_without_retry_after"
            elif row["status"] != 200:
                row["outcome"] = "http_error"
            else:
                row["outcome"] = "ok" if not message or valid_wire_reply(
                    kind, b"".join(chunks), message, response.headers.get("content-type", "")) else "mcp_error"
    except httpx.TimeoutException:
        row["outcome"] = "timeout"
    except httpx.HTTPError:
        row["outcome"] = "transport_error"
    row["seconds"] = time.monotonic() - started
    return row


def stage_snapshot(directory, destination):
    manifest = validate_manifest((directory / "manifest.json").read_bytes())
    name = manifest["archive"]["sha256"] + "/snapshot.tar.gz"
    archive = (directory / name).read_bytes()
    require(len(archive) <= MAX_ARCHIVE_BYTES, "fixture_archive_size")
    verified = verify_archive(archive, manifest)
    path = destination / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o755)
    path.write_bytes(archive)
    path.chmod(0o644)
    manifest["archive"]["path"] = name
    rows = [json.loads(line) for line in verified.files["pages.jsonl"].splitlines() if line.strip()]
    page = next(row for row in rows if row["id"] == "std437")
    body = page["body_markdown"]
    # These explicitly synthetic fixtures use a bounded, literal page body.
    # Hash archive content directly, never the runtime presentation algorithm.
    require(isinstance(body, str) and 0 < len(body) <= 12000, "controlled_page_within_default_budget")
    return manifest, hashlib.sha256(body.encode("utf-8")).hexdigest()


def pointer(path, manifest):
    save(path, manifest)
    path.chmod(0o644)


def write_report(path, report):
    # Local measurements contain finite fractional seconds; they are not the
    # integer-only canonical snapshot/publication contract.
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


async def open_idle(port):
    reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), 3)
    try:
        writer.write(b"GET /healthz HTTP/1.1\r\nHost: ai.v8std.ru\r\nConnection: keep-alive\r\n\r\n")
        await writer.drain()
        header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        size = re.search(rb"(?im)^content-length:\s*([0-9]+)", header)
        require(b" 200 " in header and size is not None and int(size[1]) <= 65536, "idle_probe")
        await asyncio.wait_for(reader.readexactly(int(size[1])), 5)
        return reader, writer
    except BaseException:
        writer.close()
        await writer.wait_closed()
        raise


async def maintain_idle(idle, port, stop, stats, *, interval=.25):
    while not stop.is_set():
        for index, (reader, writer) in enumerate(idle):
            if reader.at_eof():
                writer.close()
                await writer.wait_closed()
                idle[index] = await open_idle(port)
                stats["reconnections"] += 1
        try:
            await asyncio.wait_for(stop.wait(), interval)
        except TimeoutError:
            pass


async def page_content_hash(client, endpoint, expected):
    _, message = request(7)
    async with client.stream("POST", endpoint + "/mcp", json=message) as response:
        require(response.status_code == 200, "page_hash_http")
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            require(size <= 256 * 1024, "page_hash_bound")
            chunks.append(chunk)
    body = b"".join(chunks)
    require(valid_wire_reply("page", body, message, response.headers.get("content-type", "")), "page_hash_reply")
    page = content(json.loads(body)["result"])["page"]
    require(page.get("body_truncated") is False, "controlled_page_truncated")
    actual = hashlib.sha256(page["body_markdown"].encode("utf-8")).hexdigest()
    require(actual == expected, "controlled_page_content_mismatch")
    return actual


async def profile(stack, args, directory, names, manifests, page_hashes, endpoint, static_url):
    rows, samples, events = [], [], []
    headers = {"Host": "ai.v8std.ru", "Accept": "application/json, text/event-stream"}
    limits = httpx.Limits(max_connections=64, max_keepalive_connections=64)
    async with httpx.AsyncClient(timeout=15, trust_env=False, limits=limits, headers=headers) as client:
        deadline = time.monotonic() + 390
        health = None
        while time.monotonic() < deadline:
            try:
                response = await client.get(endpoint + "/healthz")
                health = response.json()
                if response.status_code == 200 and health.get("corpus_id") == manifests[0]["corpus_id"]:
                    break
            except (httpx.HTTPError, ValueError):
                pass
            await asyncio.sleep(.5)
        require(health is not None and health.get("runtime_sha") == args.source_sha
                and health.get("corpus_id") == manifests[0]["corpus_id"], "load_initial_readiness")
        initial = await measure(client, endpoint + "/mcp", "initialize", INIT)
        require(initial["outcome"] == "ok", "load_initialize")
        client.headers["MCP-Protocol-Version"] = INIT["params"]["protocolVersion"]
        notified = await client.post(endpoint + "/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        require(notified.status_code == 202 and not notified.content, "load_initialized_notification")
        async def denied_probes():
            probes = []
            for number, (method, params) in enumerate(RESOURCE_REQUESTS):
                message = {"jsonrpc": "2.0", "id": "denied-" + str(number), "method": method, "params": params}
                row = await measure(client, endpoint + "/mcp", "resource_denial", message)
                row.update(method=method, params=params)
                probes.append(row)
            require(all(row["outcome"] == "ok" for row in probes), "load_resources_not_denied")
            return probes
        negative_before = await denied_probes()
        before_hash = await page_content_hash(client, endpoint, page_hashes[0])
        # Burst is discovery traffic, deliberately separate from data-call mix.
        burst_start = time.monotonic()
        semaphore = asyncio.Semaphore(64)
        async def burst_request():
            async with semaphore:
                return await measure(client, endpoint + "/mcp", "initialize", INIT)
        burst = await asyncio.gather(*(burst_request() for _ in range(args.burst)))
        burst_seconds = time.monotonic() - burst_start
        await asyncio.sleep(5)  # Existing Retry-After/admission budget, not suppressed errors.
        idle = []
        idle_stop, idle_stats = asyncio.Event(), {"reconnections": 0}
        idle_keeper = None
        primary = None
        port = int(endpoint.rsplit(":", 1)[1])
        try:
            for _ in range(args.idle):
                idle.append(await open_idle(port))
            idle_keeper = asyncio.create_task(maintain_idle(idle, port, idle_stop, idle_stats))
            started = time.monotonic()
            reconnects = 0
            maximum_inflight = inflight = 0
            async def worker(worker_id):
                nonlocal reconnects, maximum_inflight, inflight
                number = worker_id * 3
                while time.monotonic() - started < args.seconds:
                    label, message = request(number)
                    close = number % 11 == 0
                    reconnects += close
                    inflight += 1
                    maximum_inflight = max(maximum_inflight, inflight)
                    try:
                        rows.append(await measure(client, endpoint + "/mcp", label, message,
                                                  headers={"Connection": "close"} if close else None))
                    finally:
                        inflight -= 1
                    number += 1
                    await asyncio.sleep(.05)
            async def downloads():
                while time.monotonic() - started < args.seconds:
                    for manifest in manifests:
                        rows.append(await measure(client, static_url + "/ai/mcp/v1/" + manifest["archive"]["path"], "archive"))
                    await asyncio.sleep(.2)
            async def transitions():
                await asyncio.sleep(args.seconds / 3)
                pointer(directory / "source/manifest.json", manifests[1])
                events.append({"action": "refresh_manifest", "seconds": round(time.monotonic() - started, 3),
                               "corpus_id": manifests[1]["corpus_id"]})
                await asyncio.sleep(args.seconds / 3)
                (directory / "edge/nginx.conf").write_text(edge_config("mcp-b"))
                await asyncio.to_thread(stack.docker, "exec", names["edge"], "nginx", "-t", "-c", "/fixture/nginx.conf")
                await asyncio.to_thread(stack.docker, "exec", names["edge"], "nginx", "-s", "reload", "-c", "/fixture/nginx.conf")
                events.append({"action": "switch_to_second_process_same_image", "seconds": round(time.monotonic() - started, 3)})
            async def sample():
                while time.monotonic() - started < args.seconds:
                    raw = await asyncio.to_thread(stack.docker, "stats", "--no-stream", "--format", "{{json .}}",
                                                  *names.values(), seconds=15)
                    samples.append({"seconds": round(time.monotonic() - started, 3),
                                    "containers": [json.loads(line) for line in raw.splitlines()],
                                    "runtime_cgroups": {slot: json.loads(await asyncio.to_thread(stack.docker, "exec", names[slot],
                                        "python", "-c", RESOURCE_PROBE, seconds=10)) for slot in ("a", "b")}})
                    await asyncio.sleep(1)
            async with asyncio.timeout(args.seconds + 35):
                await asyncio.gather(*(worker(number) for number in range(args.clients)), downloads(), transitions(), sample())
            elapsed = time.monotonic() - started
            final = (await client.get(endpoint + "/healthz")).json()
            require(final.get("ok") is True and final.get("runtime_sha") == args.source_sha
                    and final.get("corpus_id") == manifests[1]["corpus_id"], "refresh_and_switch_readiness")
            after_hash = await page_content_hash(client, endpoint, page_hashes[1])
            negative_after = await denied_probes()
            data = [row for row in rows if row["kind"] != "archive"]
            return {"scope": "local HTTP (no TLS), one edge worker, two processes of the same exact image; not host-controller deployment",
                    "duration_seconds": elapsed, "configured_clients": args.clients, "maximum_inflight_data_calls": maximum_inflight,
                    "idle_connections_opened": len(idle), "idle_connections_still_open": sum(not reader.at_eof() for reader, _ in idle),
                    "idle_reconnections": idle_stats["reconnections"], "idle_maintenance_interval_seconds": .25,
                    "page_content_hashes": {"before": before_hash, "after": after_hash},
                    "rejected_resource_probes": {"before": negative_before, "after": negative_after,
                        "requests": len(negative_before) + len(negative_after),
                        "rejected": len(negative_before) + len(negative_after), "unexpected_errors": 0},
                    "initialize": initial,
                    "connection_close_requests": reconnects, "shared_nat": "all clients share one host address at edge",
                    "data": summarize(data, elapsed), "static": summarize([row for row in rows if row["kind"] == "archive"], elapsed),
                    "discovery_burst": summarize(burst, max(.001, burst_seconds)), "events": events,
                    "samples": samples, "initial_health": health, "final_health": final}
        except BaseException as error:
            primary = error
            raise
        finally:
            idle_stop.set()
            if idle_keeper is not None:
                # A failed reconnect must fail the profile, but not skip socket cleanup.
                await asyncio.gather(idle_keeper, return_exceptions=True)
            for _, writer in idle:
                writer.close()
            await asyncio.gather(*(writer.wait_closed() for _, writer in idle), return_exceptions=True)
            if idle_keeper is not None and not idle_keeper.cancelled() and idle_keeper.exception() is not None:
                if primary is None:
                    raise idle_keeper.exception()
                primary.add_note("idle maintenance failed: " + str(idle_keeper.exception()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-image", required=True)
    parser.add_argument("--site-image", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--refresh-snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--idle", type=int, default=64)
    parser.add_argument("--burst", type=int, default=600)
    args = parser.parse_args(argv)
    require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha) and 30 <= args.seconds <= 120
            and 1 <= args.clients <= 32 and 0 <= args.idle <= 256 and 0 <= args.burst <= 1000, "load_bounds")
    require(not args.output.exists(), "evidence_output_exists")
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 18765))
    with tempfile.TemporaryDirectory(prefix="v8std-load-source-") as temporary, Stack() as stack:
        directory = Path(temporary)
        for name in ("source", "edge"):
            (directory / name).mkdir(mode=0o755)
        staged = [stage_snapshot(path, directory / "source") for path in (args.snapshot, args.refresh_snapshot)]
        manifests, page_hashes = [item[0] for item in staged], [item[1] for item in staged]
        require(manifests[0]["corpus_id"] != manifests[1]["corpus_id"], "distinct_refresh_fixture_required")
        require(page_hashes[0] != page_hashes[1], "changed_page_content_required")
        pointer(directory / "source/manifest.json", manifests[0])
        (directory / "edge/nginx.conf").write_text(edge_config("mcp-a"))
        (directory / "edge/nginx.conf").chmod(0o644)
        image_info = json.loads(stack.docker("image", "inspect", args.mcp_image, args.site_image))
        require(len(image_info) == 2 and all(info["Config"]["Labels"].get("org.opencontainers.image.revision") == args.source_sha
                                           for info in image_info), "committed_image_source")
        corpus = stack.create("network", "corpus", "--internal")
        publish = stack.create("network", "publish")
        logs = stack.create("volume", "logs")
        mount = json.loads(stack.docker("volume", "inspect", logs))[0]["Mountpoint"]
        require(mount.startswith("/var/lib/docker/volumes/" + logs + "/"), "owned_volume_mountpoint")
        # Only this bounded fixture preparer is root, with CHOWN on its own
        # empty volume. MCP receives a single file bind, never this directory.
        root_code = ("import os,time; os.mkdir('/fixture/private',0o700); "
                     "f=os.open('/fixture/private/usage.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o640); "
                     "os.fchmod(f,0o640); os.fchown(f,10001,0); os.close(f); time.sleep(1200)")
        root = stack.launch("prepare", args.mcp_image, "--network=none", "--cap-add=CHOWN", "--entrypoint=python",
                            "--mount", f"type=volume,source={logs},target=/fixture", command=("-c", root_code),
                            memory="64m", cpus="0.25", user="0:0")
        stack.docker("exec", root, "python", "-c", "import time,pathlib; p=pathlib.Path('/fixture/private/usage.jsonl'); "
                     "end=time.monotonic()+5\nwhile not p.exists() and time.monotonic()<end: time.sleep(.02)\nassert p.is_file()")
        names = {"prepare": root}
        names["site"] = stack.launch("site", args.site_image, "--network", publish, "-p", "127.0.0.1:18765:18765",
            "--mount", f"type=bind,source={directory / 'source'},target=/srv/site/ai/mcp/v1,readonly", "--entrypoint=/bin/sh",
            command=("-ec", "sed 's/listen 8000;/listen 18765;/' /etc/nginx/nginx.conf > /tmp/site.conf; "
                             "exec nginx -c /tmp/site.conf -g 'daemon off;'"),
            memory="128m", cpus="0.5", networks=((corpus, "v8std.localhost"),))
        for slot in ("a", "b"):
            names[slot] = stack.launch(slot, args.mcp_image, "--network", corpus, "--network-alias", "mcp-" + slot,
                "--tmpfs", "/var/lib/v8std-mcp:rw,size=256m,uid=10001,gid=10001,mode=0700",
                "--mount", f"type=bind,source={mount}/private/usage.jsonl,target=/var/log/v8std-mcp-usage.jsonl",
                command=("--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000",
                         "--site-url", "http://v8std.localhost:18765/", "--refresh-seconds", "5",
                         "--usage-log", "/var/log/v8std-mcp-usage.jsonl"))
        names["edge"] = stack.launch("edge", args.site_image, "--network", publish, "-p", "127.0.0.1::8000",
            "--ulimit", "nofile=131072:131072", "--mount", f"type=bind,source={directory / 'edge'},target=/fixture,readonly",
            command=("-c", "/fixture/nginx.conf", "-g", "daemon off;"), memory="128m", cpus="1",
            networks=((corpus, "edge"),))
        port = stack.inspect(names["edge"])["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
        print("owned mixed-load fixtures starting: " + stack.prefix, flush=True)
        report = asyncio.run(profile(stack, args, directory, names, manifests, page_hashes,
                                     "http://127.0.0.1:" + port, "http://127.0.0.1:18765"))
        report.update(source_sha=args.source_sha, image_ids=[info["Id"] for info in image_info],
                      fixture_prefix=stack.prefix, source_manifests=manifests, refresh_seconds=5,
                      limits={"runtime_each_memory_bytes": 1536 * 1024**2, "runtime_each_cpus": 2,
                              "static_memory_bytes": 128 * 1024**2, "edge_memory_bytes": 128 * 1024**2,
                              "edge_cpus": 1, "root_fixture_memory_bytes": 64 * 1024**2})
        report["runtime_cgroups"] = {slot: json.loads(stack.docker("exec", names[slot], "python", "-c", RESOURCE_PROBE)) for slot in ("a", "b")}
        log_probe = ("import json,pathlib,collections; p=pathlib.Path('/fixture/private/usage.jsonl'); "
                     "s=p.stat(); c=collections.Counter(json.loads(line)['tool'] for line in p.read_text().splitlines()); "
                     "print(json.dumps({'bytes':s.st_size,'uid':s.st_uid,'gid':s.st_gid,'mode':s.st_mode&511,'tool_counts':c}))")
        report["usage_log"] = json.loads(stack.docker("exec", root, "python", "-c", log_probe))
        require(report["usage_log"]["bytes"] > 0 and report["usage_log"]["uid"] == 10001
                and report["usage_log"]["mode"] == 0o640, "private_load_logging")
        for slot in ("a", "b"):
            require(not stack.inspect(names[slot])["State"]["OOMKilled"], "load_oom")
    report["cleanup"] = "verified removal of every exact labelled container, network and log volume; temporary source removed"
    write_report(args.output, report)
    compact = {key: report[key] for key in ("data", "static", "discovery_burst", "usage_log", "cleanup")}
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    require(all(report[key]["unexpected_errors"] == 0 for key in ("data", "static", "discovery_burst")), "load_unexpected_errors")
    require(all(value["successes"] > 0 for value in report["data"]["by_kind"].values())
            and set(report["data"]["by_kind"]) == {"search", "page", "snippet", "diagnostics", "related"}, "load_incomplete_mix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
