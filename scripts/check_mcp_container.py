#!/usr/bin/env python3
"""Disposable real-image acceptance; never edits an active Docker catalog.

Build images first. Requires Docker, Python runtime dependencies, and (with
--chrome) Chrome plus Node 22+. Each run removes only its own labeled resources.
"""
from __future__ import annotations

import argparse
import contextlib
from functools import cache
import hashlib
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

import yaml

ROOT = Path(__file__).resolve().parents[1]
INIT = {"protocolVersion": "2025-03-26", "capabilities": {},
        "clientInfo": {"name": "v8std-container-check", "version": "1"}}
SIGNAL = 'Предупреждение("Текст");'
TOOLS = {"v8std_search", "v8std_get_page", "v8std_get_related",
         "v8std_explain_snippet", "v8std_explain_diagnostics"}


@cache
def canonical_ranking():
    sys.path.insert(0, str(ROOT / "scripts"))
    from v8std_mcp_index import V8StdIndex
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
        if data.startswith(b"event:"):
            data = next(line[6:] for line in data.splitlines() if line.startswith(b"data: "))
        return response.status, dict(response.headers), data


class Stdio:
    def __init__(self, command, stderr, env=None):
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=stderr, text=True, bufsize=1, env=env)
        self.lines = queue.Queue()
        self.seq = 0
        def read():
            for line in self.process.stdout:
                self.lines.put(line)
            self.lines.put(None)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def request(self, method, params=None):
        self.seq += 1
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.seq,
            "method": method, "params": params or {}}) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.lines.get(timeout=120)
            assert line is not None, "premature stdout EOF"
            message = json.loads(line)  # Every stdout line must be protocol JSON.
            if message.get("id") == self.seq:
                assert "error" not in message, message
                return message["result"]

    def initialize(self, name="v8std"):
        reply = self.request("initialize", INIT)
        if name:
            assert reply["serverInfo"]["name"] == name, reply
        self.process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.process.stdin.flush()
        return reply

    def close(self):
        self.process.stdin.close()
        code = self.process.wait(timeout=20)
        self.reader.join(timeout=2)
        self.process.stdout.close()
        assert code == 0, f"stdio EOF exit={code}"


def content(reply):
    assert not reply.get("isError"), str(reply)[:400]
    return reply.get("structuredContent") or json.loads(reply["content"][0]["text"])


def check_tools(request, site_url, *, resources=True):
    listed = request("tools/list")
    names = {tool["name"] for tool in listed["tools"]}
    assert TOOLS <= names, names
    if resources:
        assert names == TOOLS
        assert len(request("resources/list")["resources"]) == 3
    snippet = next(t for t in listed["tools"] if t["name"] == "v8std_explain_snippet")
    assert snippet["inputSchema"]["properties"]["snippet"]["maxLength"] == 4000
    def call(name, args):
        return content(request("tools/call", {"name": name, "arguments": args}))
    search = eventually(lambda: call("v8std_search", {"query": "std437", "limit": 3}))
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
    assert page["page"]["url"] == site_url + "std/437/"
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


def host_gateway_check(project, image, volume, site_url, directory):
    """Two isolated host Gateways consume the already verified cache offline.

    Containerized Gateway's site-network routing is a separate acceptance gate.
    No HOME override, active catalog modification, or extra Docker privileges.
    """
    catalog_root = Path.home() / ".docker/mcp/catalogs"
    catalog_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=project + "-", dir=catalog_root) as catalog_dir:
        catalog_path = Path(catalog_dir) / "catalog.yaml"
        source = yaml.safe_load((ROOT / "deploy/docker-catalog/server.yaml").read_text())
        spec = {"name": project, "type": source["type"], "image": image,
                "title": source["about"]["title"], "longLived": source["longLived"],
                "user": source["run"]["user"], "command": source["run"]["command"],
                "disableNetwork": True, "volumes": [volume + ":/var/lib/v8std-mcp"],
                "env": [{"name": "V8STD_MCP_SITE_URL", "value": site_url},
                        {"name": "V8STD_MCP_MAX_SNIPPET_CHARS", "value": "4000"}]}
        catalog_path.write_text(yaml.safe_dump({"registry": {project: spec}}))
        for name in ("config.yaml", "registry.yaml", "tools.yaml"):
            (directory / name).write_text("{}\n")
        (directory / "secrets.env").write_text("")
        command = ["docker", "mcp", "gateway", "run", "--catalog", str(catalog_path),
                   "--config", str(directory / "config.yaml"), "--registry", str(directory / "registry.yaml"),
                   "--tools-config", str(directory / "tools.yaml"), "--secrets", str(directory / "secrets.env"),
                   "--servers", project, "--verify-signatures=false", "--watch=false",
                   "--cpus", "2", "--memory", "1536Mb", "--long-lived", "--transport", "stdio"]
        sessions = []
        try:
            with contextlib.ExitStack() as stack:
                for number in range(2):
                    log = stack.enter_context((directory / f"gateway-{number}.log").open("w"))
                    session = Stdio(command, log)
                    sessions.append(session)
                    session.initialize(name=None)
                    check_tools(session.request, site_url, resources=False)
                ids = run("docker", "ps", "-q", "--filter", "label=docker-mcp-name=" + project).splitlines()
                assert len(ids) == 2, f"expected one long-lived server per session, got {ids}"
                time.sleep(3)
                for session in sessions:
                    check_tools(session.request, site_url, resources=False)
                assert set(ids) == set(run("docker", "ps", "-q", "--filter", "label=docker-mcp-name=" + project).splitlines())
                states = json.loads(run("docker", "inspect", *ids))
                for state in states:
                    assert state["Config"]["User"] == "10001:10001"
                    assert state["Config"]["WorkingDir"] == "/opt/v8std"
                    assert state["HostConfig"]["NetworkMode"] == "none"
                for session in sessions:
                    session.close()
                return {"sessions": 2, "servers": len(ids), "network": "none",
                        "warm_cache": True, "long_lived_same_ids": True,
                        "read_only": states[0]["HostConfig"]["ReadonlyRootfs"],
                        "cap_drop": states[0]["HostConfig"]["CapDrop"]}
        finally:
            for session in sessions:
                if session.process.poll() is None:
                    session.process.terminate()
                    try:
                        session.process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        session.process.kill()
                        session.process.wait(timeout=5)
            own = run("docker", "ps", "-aq", "--filter", "label=docker-mcp-name=" + project).splitlines()
            if own:
                run("docker", "rm", "-f", *own)


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
    parser.add_argument("--host-gateway", action="store_true",
                        help="Two Gateway sessions using warm cache and network none")
    args = parser.parse_args()
    canonical_ranking()
    for port in (args.site_port, args.mcp_port):
        with socket.socket() as probe:
            # Permit TIME_WAIT from our preceding run, but never an active listener.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
    assert args.prefix.startswith("/") and args.prefix.endswith("/")
    site_url = f"http://v8std.localhost:{args.site_port}{args.prefix}"
    project = "v8std-task4-" + uuid.uuid4().hex[:10]
    env = {**os.environ, "V8STD_SITE_IMAGE": args.site_image, "V8STD_MCP_IMAGE": args.mcp_image,
           "V8STD_SITE_PORT": str(args.site_port), "V8STD_MCP_PORT": str(args.mcp_port),
           "V8STD_SITE_PREFIX": args.prefix, "DOCKER_DEFAULT_PLATFORM": args.platform}
    compose = ["docker", "compose", "-p", project, "-f", str(ROOT / "compose.yaml")]
    names = []
    report = {"platform": args.platform, "site_url": site_url}
    with tempfile.TemporaryDirectory(prefix=project) as directory:
        directory = Path(directory)
        try:
            run(*compose, "up", "-d", "site", env=env)
            site = run(*compose, "ps", "-q", "site", env=env)
            eventually(lambda: http(site_url)[0] == 200)
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
            if args.chrome:
                report["browser"] = browser_graph(args.chrome, args.node, site_url, directory)
            network = project + "_corpus"
            volume = project + "-stdio-cache"
            run("docker", "volume", "create", "--label", f"v8std-task4={project}", volume)
            def container(name, network_name, transport="stdio", cache=volume):
                names.append(name)
                return ["docker", "run", "--name", name, "--platform", args.platform,
                    "--label", f"v8std-task4={project}", "-i", "--init", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--cpus", "2",
                    "--memory", "1536m", "--pids-limit", "128", "--network", network_name,
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m,uid=10001,gid=10001",
                    "-v", cache + ":/var/lib/v8std-mcp", "-e", "V8STD_MCP_SITE_URL=" + site_url,
                    args.mcp_image, "--transport", transport, "--refresh-seconds", "0"]

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

            for iteration, network_name in enumerate((network, "none")):
                name = project + f"-stdio-{iteration}"
                with (directory / f"stdio-{iteration}.log").open("w") as log:
                    session = Stdio(container(name, network_name), log)
                    try:
                        session.initialize()
                        ranking = check_tools(session.request, site_url)
                        state = inspect(name)
                        if iteration == 0:
                            code = "import importlib.metadata as m,json; from pathlib import Path; " \
                                   "names={d.metadata['Name'].lower():d.version for d in m.distributions()}; " \
                                   "assert not {'pillow','zensical','markdown'} & names.keys(); " \
                                   "assert names['mcp']=='1.27.0' and names['markdown-it-py']=='4.0.0' and names['mdurl']=='0.1.2'; " \
                                   "assert not Path('/opt/v8std/docs').exists(); " \
                                   "assert not Path('/opt/v8std/zensical.toml').exists(); " \
                                   "assert Path('/opt/v8std/LICENSE').is_file(); " \
                                   "print(json.dumps(names,sort_keys=True))"
                            report["installed_runtime_graph"] = json.loads(run("docker", "exec", name, "python", "-c", code))
                        current = cache_state(name)
                        assert current and all(value[0] == 10001 for value in current.values())
                        if iteration == 0:
                            original, original_ranking = current, ranking
                            report["mcp_image_id"] = state["Image"]
                        else:
                            assert original == current, "offline warm restart rewrote cache"
                            assert original_ranking == ranking
                        session.close()
                    finally:
                        if session.process.poll() is None:
                            run("docker", "stop", "-t", "15", name)
                            session.process.wait(timeout=20)
                assert not json.loads(run("docker", "inspect", name))[0]["State"]["OOMKilled"]
            report["stdio"] = "cold-online + warm-network-none; EOF=0; cache UID10001 and bytes/mtime stable"
            terminated = project + "-stdio-term"
            with (directory / "stdio-term.log").open("w") as log:
                session = Stdio(container(terminated, "none") + ["--max-snippet-chars", "32000"], log)
                try:
                    session.initialize()
                    listed = session.request("tools/list")["tools"]
                    tool = next(t for t in listed if t["name"] == "v8std_explain_snippet")
                    assert tool["inputSchema"]["properties"]["snippet"]["maxLength"] == 32000
                    body = " " * (32000 - len(SIGNAL)) + SIGNAL
                    result = eventually(lambda: content(session.request("tools/call", {
                        "name": "v8std_explain_snippet", "arguments": {"snippet": body, "limit": 1}})))
                    assert result["diagnostics"][0]["id"] == "bslls:UsingModalWindows"
                    run("docker", "stop", "-t", "15", terminated)
                    report["stdio_sigterm_exit"] = session.process.wait(timeout=20)
                    assert report["stdio_sigterm_exit"] in (0, 143)
                finally:
                    if session.process.poll() is None:
                        run("docker", "stop", "-t", "15", terminated)
                        session.process.wait(timeout=20)
                    session.process.stdin.close()
                    session.reader.join(timeout=2)
                    session.process.stdout.close()
            if args.host_gateway:
                report["gateway"] = host_gateway_check(project, args.mcp_image, volume, site_url, directory)

            # Ready/liveness boundary with no source and no cache.
            cold = project + "-cold"
            command = container(cold, "none", "streamable-http", cache=project + "-empty")
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

            run(*compose, "--profile", "mcp", "up", "-d", env=env)
            mcp = run(*compose, "ps", "-q", "mcp", env=env)
            endpoint = f"http://127.0.0.1:{args.mcp_port}"
            health = eventually(lambda: json.loads(http(endpoint + "/healthz")[2]) if http(endpoint + "/healthz")[0] == 200 else None)
            assert health["corpus_id"] == manifest["corpus_id"], health
            count = 0
            def request(method, params=None):
                nonlocal count
                count += 1
                status, _, body = http(endpoint + "/mcp", {"jsonrpc": "2.0", "id": count,
                                                           "method": method, "params": params or {}})
                assert status == 200, (status, body[:200])
                return json.loads(body)["result"]
            assert request("initialize", INIT)["serverInfo"]["name"] == "v8std"
            assert http(endpoint + "/mcp", {"jsonrpc":"2.0", "id":999,
                        "method":"initialize", "params":INIT}, headers={"Host":"untrusted.invalid"})[0] == 421
            check_tools(request, site_url)
            inspect(mcp)
            assert list(json.loads(run("docker", "inspect", mcp))[0]["NetworkSettings"]["Networks"]) == [network]
            report["http"] = health
            report["site_image_id"] = json.loads(run("docker", "inspect", site))[0]["Image"]
            run(*compose, "stop", "-t", "15", "mcp", env=env)
            report["warm_http_sigterm_exit"] = json.loads(run("docker", "inspect", mcp))[0]["State"]["ExitCode"]
            assert report["warm_http_sigterm_exit"] in (0, 143)
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
            for volume_name in (project + "-stdio-cache", project + "-empty"):
                subprocess.run(["docker", "volume", "rm", volume_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
