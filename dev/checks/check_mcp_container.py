#!/usr/bin/env python3
"""Disposable HTTP image acceptance.

Build images first. Requires Docker, Python runtime dependencies, and (with
--chrome) Chrome plus Node 22+. Each run removes only its own labeled resources.
"""
from __future__ import annotations

import argparse
from functools import cache
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid


ROOT = Path(__file__).resolve().parents[2]
INIT = {"protocolVersion": "2025-03-26", "capabilities": {},
        "clientInfo": {"name": "v8std-container-check", "version": "1"}}
SIGNAL = 'Предупреждение("Текст");'
TOOLS = {"v8std_search", "v8std_get_page", "v8std_get_related",
         "v8std_explain_snippet", "v8std_explain_diagnostics"}
RESOURCE_REQUESTS = [("resources/list", {}), ("resources/templates/list", {})] + [
    (method, {"uri": uri})
    for method in ("resources/read", "resources/subscribe", "resources/unsubscribe")
    for uri in ("v8std://llms.txt", "v8std://llms-full.txt", "v8std://ai/pages.jsonl", "v8std://missing")]
# Whole-attempt budget plus bounded interpreter/container startup margin.
# This is only polling readiness; individual RPC/read/stop budgets stay shorter.
STARTUP_SECONDS = 360 + 30


@cache
def canonical_ranking():
    from runtime.v8std_mcp_index import V8StdIndex
    index = V8StdIndex(pages_path=ROOT / "docs/ai/pages.jsonl",
                      vectors_path=ROOT / "docs/ai/search-vectors.jsonl")
    index.load()
    return [row["id"] for row in index.search("модальные окна", limit=5)["results"]]


def run(*args, timeout=180, **kwargs):
    return subprocess.check_output(list(map(str, args)), text=True, timeout=timeout, **kwargs).strip()


def eventually(check, seconds=120):
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        try:
            result = check()
            if result:
                return result
        except (OSError, ValueError, AssertionError, subprocess.CalledProcessError) as error:
            last = error
        time.sleep(1)
    raise AssertionError(f"readiness deadline: {last}")


def http(url, message=None, headers=None):
    req = Request(url, data=json.dumps(message).encode() if message else None,
                  headers={"Accept": "application/json, text/event-stream",
                           "Content-Type": "application/json", **(headers or {})})
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        data = response.read()
        return response.status, dict(response.headers), data


def validate_envelope(reply, request_id):
    assert isinstance(reply, dict) and reply.get("jsonrpc") == "2.0", reply
    assert type(reply.get("id")) is type(request_id) and reply["id"] == request_id, reply
    assert ("result" in reply) != ("error" in reply), reply
    return reply


def successful_result(reply):
    assert "error" not in reply and isinstance(reply.get("result"), dict), reply
    return reply["result"]


def validate_resource_denial(reply, request_id):
    validate_envelope(reply, request_id)
    assert set(reply) == {"jsonrpc", "id", "error"}, reply
    error = reply["error"]
    assert isinstance(error, dict) and set(error) == {"code", "message"}, reply
    assert error["code"] == -32601 and isinstance(error["message"], str) and error["message"].strip(), reply
    assert len(json.dumps(reply, ensure_ascii=False).encode()) < 256, "resource error contains excessive payload"


def check_resources_disabled(envelope):
    for method, params in RESOURCE_REQUESTS:
        reply = envelope(method, params)
        # Transport adapters have already matched the typed request ID.
        validate_resource_denial(reply, reply["id"])
    return {"probes": len(RESOURCE_REQUESTS), "rejected": len(RESOURCE_REQUESTS), "code": -32601}


class HttpRpc:
    """The same complete-envelope lifecycle for online and network-none HTTP."""
    def __init__(self, send):
        self.send, self.seq, self.headers = send, 0, {}

    def envelope(self, method, params=None):
        self.seq += 1
        status, headers, body = self.send({"jsonrpc": "2.0", "id": self.seq,
            "method": method, "params": params or {}}, self.headers)
        assert status == 200, (status, body[:200])
        media = {key.lower(): value for key, value in headers.items()}.get("content-type", "")
        assert media.split(";")[0] == "application/json", media
        return validate_envelope(json.loads(body), self.seq)

    def request(self, method, params=None):
        return successful_result(self.envelope(method, params))

    def initialize(self):
        reply = self.request("initialize", INIT)
        assert reply["serverInfo"]["name"] == "v8std" and "resources" not in reply["capabilities"], reply
        assert reply["protocolVersion"] == INIT["protocolVersion"], reply
        self.headers["MCP-Protocol-Version"] = reply["protocolVersion"]
        status, _, body = self.send({"jsonrpc": "2.0", "method": "notifications/initialized"}, self.headers)
        assert status == 202 and not body, (status, body)
        return reply


def check_default_source(site_url, local_default, *, require_404=False):
    """A working alternate source does not imply the default must be broken."""
    if not require_404:
        return {}
    assert site_url != local_default, "404 regression requires an explicit alternate source"
    status = http(local_default + "ai/mcp/v1/manifest.json")[0]
    assert status == 404, "override regression requires an unavailable default source"
    return {"default_source_status": status}




def content(reply):
    assert not reply.get("isError"), str(reply)[:400]
    assert reply.get("content") and all(item["type"] == "text" for item in reply["content"]), reply
    decoded = json.loads(reply["content"][0]["text"])
    assert isinstance(decoded, dict), decoded
    if "structuredContent" in reply:
        assert reply["structuredContent"] == decoded, reply
    return decoded


def check_tools(request, site_url):
    listed = request("tools/list")
    names = {tool["name"] for tool in listed["tools"]}
    assert names == TOOLS, names
    snippet = next(t for t in listed["tools"] if t["name"] == "v8std_explain_snippet")
    assert snippet["inputSchema"]["properties"]["snippet"]["maxLength"] == 4000
    def call(name, args):
        return content(request("tools/call", {"name": name, "arguments": args}))
    search = eventually(lambda: call("v8std_search", {"query": "std437", "limit": 3}),
                        seconds=STARTUP_SECONDS)
    assert search["results"][0]["id"] == "std437", search
    assert search["results"][0]["url"] == site_url + "std/437/", search
    ranking = call("v8std_search", {"query": "модальные окна", "limit": 5})
    assert [row["id"] for row in ranking["results"]] == canonical_ranking(), ranking
    result = call("v8std_explain_snippet", {"snippet": SIGNAL, "limit": 1})
    ids = [row["id"] for field in ("diagnostics", "standards") for row in result[field]]
    assert ids == ["bslls:UsingModalWindows"], ids
    row = (result["diagnostics"] + result["standards"])[0]
    assert any(reason.startswith("snippet_signal:") for reason in row["match_reasons"]), row
    page = call("v8std_get_page", {"id_or_alias_or_url": "std437"})
    assert page["found"] and page["page"]["id"] == "std437" and page["page"]["body_markdown"]
    assert page["page"]["url"] == site_url + "std/437/"
    related = call("v8std_get_related", {"id_or_alias_or_url": "std437"})
    assert related["found"] and related["id"] == "std437" and related["related"], related
    assert all(row.get("id") and row.get("relation") and row["url"].startswith(site_url)
               for row in related["related"]), related
    diagnostics = call("v8std_explain_diagnostics", {"codes": ["bslls:UsingModalWindows"]})
    assert diagnostics["diagnostics"][0]["id"] == "bslls:UsingModalWindows", diagnostics
    return [row["id"] for row in search["results"]]


# Browser target + worker events are captured before navigation. Request
# interception blocks every foreign origin and records attempts as failures.
CHROME_CHECK = r"""
const [endpoint, base] = process.argv.slice(1);
const socket = new WebSocket(endpoint);
await new Promise(r => socket.addEventListener('open', r, {once:true}));
let seq=0; const pending=new Map(), attached=new Map(), requests=[], failures=[], statuses=[];
function send(method,params={},sessionId) {
  const id=++seq;
  return new Promise((resolve,reject)=>{
    pending.set(id,{resolve,reject});
    socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
  });
}
socket.addEventListener('message',async ({data})=>{
 const m=JSON.parse(data);
 if(m.id) { const p=pending.get(m.id); pending.delete(m.id);
   if(m.error)p.reject(Error(JSON.stringify(m.error)));else p.resolve(m.result);return; }
 const p=m.params;
 if(m.method==='Target.attachedToTarget') {
   await send('Network.enable',{},p.sessionId);
   if(p.targetInfo.type==='page') {
     await send('Fetch.enable',{patterns:[{urlPattern:'*'}]},p.sessionId);
     await send('Target.setAutoAttach',
         {autoAttach:true,waitForDebuggerOnStart:true,flatten:true},p.sessionId);
   }
   attached.set(p.targetInfo.targetId,p.sessionId);
   await send('Runtime.runIfWaitingForDebugger',{},p.sessionId);
 }
 if(m.method==='Network.requestWillBeSent')requests.push(p.request.url);
 if(m.method==='Network.responseReceived')statuses.push({url:p.response.url,status:p.response.status});
 if(m.method==='Fetch.requestPaused') {
   const u=p.request.url;
   if(/^https?:/.test(u) && new URL(u).origin!==new URL(base).origin) {
     failures.push(u);await send('Fetch.failRequest',{requestId:p.requestId,errorReason:'BlockedByClient'},m.sessionId);
   }else await send('Fetch.continueRequest',{requestId:p.requestId},m.sessionId);
 }
});
await send('Target.setAutoAttach',{autoAttach:true,waitForDebuggerOnStart:true,flatten:true});
const {targetId}=await send('Target.createTarget',{url:'about:blank'});
while(!attached.has(targetId))await new Promise(r=>setTimeout(r,10));
const sessionId=attached.get(targetId);
await send('Page.enable',{},sessionId);
for (const path of ['', 'std/437/', 'diagnostics/bslls/', 'diagnostics/bslls/UsingModalWindows/', 'LICENSES/']) {
 const navigation=await send('Page.navigate',{url:base+path},sessionId);
 if(navigation.errorText)throw Error(navigation.errorText);
 await new Promise(r=>setTimeout(r,2500));
 await send('Runtime.evaluate',{expression:`document.querySelector('input[data-md-component="search-query"]')?.focus()`},sessionId);
 await new Promise(r=>setTimeout(r,1500));
}
const unique=[...new Set(requests.filter(u=>/^https?:/.test(u)))];
failures.push(...unique.filter(u=>new URL(u).origin!==new URL(base).origin));
const bad=statuses.filter(x=>x.status>=400);
console.log(JSON.stringify({requests:unique,blocked:failures,badResponses:bad}));
await send('Target.closeTarget',{targetId});socket.close();
if(failures.length||bad.length||unique.length<10)process.exitCode=1;
"""


def browser_graph(chrome, node, site_url, directory):
    with (directory / "chrome.log").open("w") as log:
        process = subprocess.Popen([chrome, "--headless=new", "--no-first-run",
            "--no-default-browser-check", "--disable-background-networking", "--disable-component-update",
            "--password-store=basic", "--remote-debugging-port=0",
            "--disable-sync", "--disable-default-apps", "--disable-domain-reliability",
            "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE v8std.localhost, EXCLUDE localhost",
            f"--user-data-dir={directory / 'chrome-profile'}", "about:blank"],
            stdout=log, stderr=log)
        try:
            active = directory / "chrome-profile/DevToolsActivePort"
            eventually(lambda: active.is_file(), seconds=15)
            port, endpoint = active.read_text().splitlines()[:2]
            try:
                result = run(node, "--input-type=module", "-e", CHROME_CHECK,
                             f"ws://127.0.0.1:{port}{endpoint}", site_url, timeout=55)
            except subprocess.CalledProcessError as error:
                raise AssertionError("browser graph: " + error.output[-6000:]) from None
            return json.loads(result)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-image", required=True)
    parser.add_argument("--site-image", required=True)
    parser.add_argument("--platform", choices=["linux/arm64", "linux/amd64"], required=True)
    parser.add_argument("--site-port", type=int, default=18765)
    parser.add_argument("--mcp-port", type=int, default=18766)
    parser.add_argument("--prefix", default="/")
    parser.add_argument("--chrome")
    parser.add_argument("--node", default="node")
    parser.add_argument("--require-default-source-404", action="store_true",
                        help="Explicit override regression: additionally require the default manifest to be absent")
    args = parser.parse_args()
    canonical_ranking()
    for port in (args.site_port, args.mcp_port):
        with socket.socket() as probe:
            # Permit TIME_WAIT from our preceding run, but never an active listener.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
    assert args.prefix.startswith("/") and args.prefix.endswith("/")
    local_default = f"http://v8std.localhost:{args.site_port}{args.prefix}"
    site_url = os.environ.get("V8STD_MCP_SITE_URL") or local_default
    project = "v8std-task4-" + uuid.uuid4().hex[:10]
    env = {**os.environ, "V8STD_SITE_IMAGE": args.site_image, "V8STD_MCP_IMAGE": args.mcp_image,
           "V8STD_SITE_PORT": str(args.site_port), "V8STD_MCP_PORT": str(args.mcp_port),
           "V8STD_SITE_PREFIX": args.prefix, "DOCKER_DEFAULT_PLATFORM": args.platform}
    compose = ["docker", "compose", "-p", project, "-f", str(ROOT / "delivery/local/compose.yaml")]
    names = []
    report = {"platform": args.platform, "site_url": site_url, "successful_tools": sorted(TOOLS),
              "rejected_resources": {}, "browser": "incomplete: --chrome not supplied"}
    resolved = json.loads(run(*compose, "--profile", "mcp", "config", "--format", "json", env=env))
    assert resolved["services"]["mcp"]["environment"]["V8STD_MCP_SITE_URL"] == site_url
    report["compose_site_url"] = site_url
    with tempfile.TemporaryDirectory(prefix=project) as directory:
        directory = Path(directory)
        try:
            run(*compose, "up", "-d", "site", env=env)
            site = run(*compose, "ps", "-q", "site", env=env)
            eventually(lambda: http(site_url)[0] == 200)
            report.update(check_default_source(site_url, local_default,
                          require_404=args.require_default_source_404))
            manifest_url = site_url + "ai/mcp/v1/manifest.json"
            status, headers, payload = http(manifest_url)
            assert status == 200 and headers.get("Cache-Control") == "no-store"
            manifest = json.loads(payload)
            assert not manifest["archive"]["path"].startswith(("/", "http"))
            archive_url = site_url + "ai/mcp/v1/" + manifest["archive"]["path"]
            status, headers, archive = http(archive_url)
            assert status == 200 and headers["Content-Type"] == "application/gzip"
            assert "immutable" in headers["Cache-Control"]
            assert hashlib.sha256(archive).hexdigest() == manifest["archive"]["sha256"]
            status, headers, _ = http(site_url + "ai/mcp/v1/" + "0" * 64 + "/snapshot.tar.gz")
            assert status == 404 and "immutable" not in headers.get("Cache-Control", "")
            status, _, _ = http(manifest_url, headers={"If-Modified-Since": "Wed, 31 Dec 2099 23:59:59 GMT"})
            assert status == 200, "manifest must not return stale 304"
            assert http(site_url + "LICENSES/")[0] == 200
            for license_name in ("LGPL-3.0", "GPL-3.0", "EPL-2.0"):
                assert http(site_url + f"LICENSES/{license_name}.txt")[2] == (ROOT / f"LICENSES/{license_name}.txt").read_bytes()
            report["corpus_id"] = manifest["corpus_id"]
            report["corpus_source_sha"] = manifest["source_sha"]
            report["archive_sha256"] = manifest["archive"]["sha256"]
            if args.chrome:
                report["browser"] = browser_graph(args.chrome, args.node, site_url, directory)
            network = project + "_corpus"
            def container(name, network_name, *, cache):
                names.append(name)
                return ["docker", "run", "--name", name, "--platform", args.platform,
                    "--label", f"v8std-task4={project}", "-i", "--init", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--cpus", "2",
                    "--memory", "1536m", "--pids-limit", "128", "--network", network_name,
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m,uid=10001,gid=10001",
                    "-v", cache + ":/var/lib/v8std-mcp", "-e", "V8STD_MCP_SITE_URL=" + site_url,
                    args.mcp_image, "--transport", "streamable-http", "--refresh-seconds", "0"]

            def inspect(name):
                state = json.loads(run("docker", "inspect", name))[0]
                assert state["Config"]["User"] == "10001:10001"
                assert state["Config"]["WorkingDir"] == "/opt/v8std"
                assert state["HostConfig"]["ReadonlyRootfs"]
                assert state["HostConfig"]["CapDrop"] == ["ALL"]
                assert state["HostConfig"]["Init"]
                assert all("docker.sock" not in m["Destination"] for m in state["Mounts"])
                return state

            def cache_state(name):
                code = "from pathlib import Path; import json; p=Path('/var/lib/v8std-mcp'); " \
                       "print(json.dumps({str(f.relative_to(p)): [f.stat().st_uid, f.stat().st_size, f.stat().st_mtime_ns] " \
                       "for f in p.rglob('*') if f.is_file() and f.name in ('state.json','snapshot.tar.gz')}))"
                return json.loads(run("docker", "exec", name, "python", "-c", code))

            # Ready/liveness boundary with no source and no cache.
            cold = project + "-cold"
            command = container(cold, "none", cache=project + "-empty")
            process = subprocess.Popen(command + ["--host", "0.0.0.0", "--port", "8000"],
                                       stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                code = "import urllib.request,urllib.error; " \
                       "r=urllib.request.urlopen('http://127.0.0.1:8000/livez'); print(r.status)"
                eventually(lambda: run("docker", "exec", cold, "python", "-c", code,
                                       stderr=subprocess.DEVNULL) == "200")
                code = "import http.client; c=http.client.HTTPConnection('127.0.0.1',8000); " \
                       "c.request('GET','/healthz'); r=c.getresponse(); print(r.status)"
                assert run("docker", "exec", cold, "python", "-c", code) == "503"
                run("docker", "stop", "-t", "15", cold)
                report["cold_http_sigterm_exit"] = process.wait(timeout=20)
                assert report["cold_http_sigterm_exit"] in (0, 143)
            finally:
                if process.poll() is None:
                    run("docker", "stop", "-t", "15", cold)
                    process.wait(timeout=20)
                process.stdin.close()

            started = time.monotonic()
            print("HTTP cold-online: starting", file=sys.stderr, flush=True)
            run(*compose, "--profile", "mcp", "up", "-d", env=env)
            mcp = run(*compose, "ps", "-q", "mcp", env=env)
            endpoint = f"http://127.0.0.1:{args.mcp_port}"
            health = eventually(lambda: json.loads(http(endpoint + "/healthz")[2]) if http(endpoint + "/healthz")[0] == 200 else None,
                                seconds=STARTUP_SECONDS)
            report["http_cold_ready_seconds"] = round(time.monotonic() - started, 2)
            print("HTTP cold-online: ready", file=sys.stderr, flush=True)
            assert health["corpus_id"] == manifest["corpus_id"], health
            rpc = HttpRpc(lambda message, headers: http(endpoint + "/mcp", message, headers))
            rpc.initialize()
            assert http(endpoint + "/mcp", {"jsonrpc":"2.0", "id":999,
                        "method":"initialize", "params":INIT}, headers={"Host":"untrusted.invalid"})[0] == 421
            check_tools(rpc.request, site_url)
            report["rejected_resources"]["http_online"] = check_resources_disabled(rpc.envelope)
            version = json.loads(http(endpoint + "/version")[2])
            assert version["api"] == "v2" and version["api_profiles"] == ["legacy-tools"], version
            report["version"] = version
            state = inspect(mcp)
            expected_sha = json.loads(run("docker", "image", "inspect", args.mcp_image))[0]["Config"]["Labels"]["org.opencontainers.image.revision"]
            assert health["runtime_sha"] == expected_sha, health
            assert "V8STD_MCP_SITE_URL=" + site_url in state["Config"]["Env"]
            http_cache = cache_state(mcp)
            http_volume = next(m["Name"] for m in state["Mounts"] if m["Destination"] == "/var/lib/v8std-mcp")
            assert list(json.loads(run("docker", "inspect", mcp))[0]["NetworkSettings"]["Networks"]) == [network]
            report["http"] = health
            report["site_image_id"] = json.loads(run("docker", "inspect", site))[0]["Image"]
            run(*compose, "stop", "-t", "15", "mcp", env=env)
            report["online_http_sigterm_exit"] = json.loads(run("docker", "inspect", mcp))[0]["State"]["ExitCode"]
            assert report["online_http_sigterm_exit"] in (0, 143)

            # Same Compose cache, but no network: exercise real warm HTTP startup.
            warm = project + "-warm-http"
            started = time.monotonic()
            print("HTTP warm-network-none: starting", file=sys.stderr, flush=True)
            with (directory / "warm-http.log").open("w") as log:
                process = subprocess.Popen(container(warm, "none", cache=http_volume)
                    + ["--host", "0.0.0.0", "--port", "8000"], stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=log)
                try:
                    code = "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=10).read().decode())"
                    warm_health = eventually(lambda: json.loads(run("docker", "exec", warm, "python", "-c", code,
                        stderr=subprocess.DEVNULL)), seconds=STARTUP_SECONDS)
                    assert warm_health["corpus_id"] == health["corpus_id"]
                    assert warm_health["runtime_sha"] == expected_sha
                    def warm_send(message, headers):
                        code = "import json,sys,urllib.request; r=urllib.request.Request('http://127.0.0.1:8000/mcp',data=sys.argv[1].encode(),headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream',**json.loads(sys.argv[2])}); response=urllib.request.urlopen(r,timeout=10); print(json.dumps([response.status,dict(response.headers),response.read().decode()]))"
                        status, headers, body = json.loads(run("docker", "exec", warm, "python", "-c", code,
                                                             json.dumps(message), json.dumps(headers)))
                        return status, headers, body.encode()
                    warm_rpc = HttpRpc(warm_send)
                    warm_rpc.initialize()
                    check_tools(warm_rpc.request, site_url)
                    report["rejected_resources"]["http_warm_offline"] = check_resources_disabled(warm_rpc.envelope)
                    assert cache_state(warm) == http_cache, "offline warm HTTP rewrote cache"
                    assert inspect(warm)["HostConfig"]["NetworkMode"] == "none"
                    report["http_warm_ready_seconds"] = round(time.monotonic() - started, 2)
                    report["http_warm"] = warm_health
                    print("HTTP warm-network-none: ready", file=sys.stderr, flush=True)
                    run("docker", "stop", "-t", "15", warm)
                    report["warm_http_sigterm_exit"] = process.wait(timeout=20)
                    assert report["warm_http_sigterm_exit"] in (0, 143)
                finally:
                    if process.poll() is None:
                        run("docker", "stop", "-t", "15", warm)
                        process.wait(timeout=20)
                    process.stdin.close()
            report["limits"] = {"mcp_memory_bytes": 1536 * 1024**2, "mcp_cpus": 2,
                                "site_memory_bytes": 128 * 1024**2, "site_cpus": 0.5}
            print(json.dumps(report, ensure_ascii=False, indent=2))
        except BaseException:
            for log in directory.glob("*.log"):
                print(f"{log.name}: {log.read_text(errors='replace')[-2500:]}", flush=True)
            raise
        finally:
            for name in names:
                subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            run(*compose, "--profile", "mcp", "down", "-v", env=env)
            for volume_name in (project + "-empty",):
                subprocess.run(["docker", "volume", "rm", volume_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
