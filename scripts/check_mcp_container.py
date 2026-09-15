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
RESOURCE_REQUESTS = [("resources/list", {}), ("resources/templates/list", {})] + [
    (method, {"uri": uri})
    for method in ("resources/read", "resources/subscribe", "resources/unsubscribe")
    for uri in ("v8std://llms.txt", "v8std://llms-full.txt", "v8std://ai/pages.jsonl", "v8std://missing")]
# Whole-attempt budget plus bounded interpreter/container startup margin.
# This is only polling readiness; individual RPC/read/stop budgets stay shorter.
STARTUP_SECONDS = 360 + 30


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


def gateway_environment(environ):
    """Reject Gateway's privileged DinD switch before any launch, never unset it."""
    if environ.get("DOCKER_MCP_IN_DIND"):
        raise AssertionError("unsafe DOCKER_MCP_IN_DIND: Gateway may add --privileged")
    return dict(environ)


def validate_gateway_profile(state, *, expected_cache):
    """Validate this harness's native Gateway launch with its sole named cache.

    Match the volume identity/source/destination, not socket filenames: a bind
    mounted socket (or its parent directory) may have an arbitrary alias.
    Optional hardening is observed, not required by the native Gateway profile.
    """
    config, host = state.get("Config", {}), state.get("HostConfig", {})
    assert config.get("User") == "10001:10001", "Gateway user must be 10001:10001"
    assert host.get("Init") is True, "Gateway init is required"
    assert host.get("Privileged") is False, "Gateway must not be privileged"
    security = host.get("SecurityOpt") or []
    nnp = [option for option in security if option.startswith("no-new-privileges")]
    assert nnp and all(option in ("no-new-privileges", "no-new-privileges:true",
                                  "no-new-privileges=true") for option in nnp), "Gateway no-new-privileges is required"
    mounts = state.get("Mounts")
    assert isinstance(mounts, list) and len(mounts) == 1, "only the expected Gateway cache mount is allowed"
    mount = mounts[0]
    assert (mount.get("Type") == "volume" and mount.get("Name") == expected_cache["Name"]
            and mount.get("Source") == expected_cache["Mountpoint"]
            and mount.get("Destination") == "/var/lib/v8std-mcp" and mount.get("RW") is True), \
        "unexpected Gateway mount; bind mounts/socket aliases are forbidden"
    return {"id": state["Id"], "image_id": state["Image"], "user": config["User"],
            "init": host["Init"], "privileged": host["Privileged"],
            "no_new_privileges": True, "security_opt": security, "mounts": mounts,
            "network": host.get("NetworkMode"), "read_only": host.get("ReadonlyRootfs"),
            "cap_drop": host.get("CapDrop"), "tmpfs": host.get("Tmpfs")}


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

    def envelope(self, method, params=None):
        self.seq += 1
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.seq,
            "method": method, "params": params or {}}) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.lines.get(timeout=120)
            assert line is not None, "premature stdout EOF"
            message = json.loads(line)  # Every stdout line must be protocol JSON.
            if "id" in message:
                return validate_envelope(message, self.seq)
            assert not message.get("method", "").startswith("notifications/resources/"), message

    def request(self, method, params=None):
        return successful_result(self.envelope(method, params))

    def initialize(self, name="v8std"):
        reply = self.request("initialize", INIT)
        if name:
            assert reply["serverInfo"]["name"] == name, reply
            assert "resources" not in reply["capabilities"], reply
        assert reply["protocolVersion"] == INIT["protocolVersion"], reply
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
    assert reply.get("content") and all(item["type"] == "text" for item in reply["content"]), reply
    decoded = json.loads(reply["content"][0]["text"])
    assert isinstance(decoded, dict), decoded
    if "structuredContent" in reply:
        assert reply["structuredContent"] == decoded, reply
    return decoded


def check_tools(request, site_url, *, aggregate_catalog=False):
    listed = request("tools/list")
    names = {tool["name"] for tool in listed["tools"]}
    assert TOOLS <= names, names
    if not aggregate_catalog:
        assert names == TOOLS
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


def host_gateway_check(project, image, volume, site_url, directory):
    """Two isolated host Gateways consume the already verified cache offline.

    Containerized Gateway's site-network routing is a separate acceptance gate.
    No HOME override, active catalog modification, or extra Docker privileges.
    """
    env = gateway_environment(os.environ)
    expected_cache = json.loads(run("docker", "volume", "inspect", volume))[0]
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
                    session = Stdio(command, log, env=env)
                    sessions.append(session)
                    session.initialize(name=None)
                    check_tools(session.request, site_url, aggregate_catalog=True)
                ids = run("docker", "ps", "-q", "--filter", "label=docker-mcp-name=" + project).splitlines()
                assert len(ids) == 2, f"expected one long-lived server per session, got {ids}"
                time.sleep(3)
                for session in sessions:
                    check_tools(session.request, site_url, aggregate_catalog=True)
                assert set(ids) == set(run("docker", "ps", "-q", "--filter", "label=docker-mcp-name=" + project).splitlines())
                states = json.loads(run("docker", "inspect", *ids))
                profiles = [validate_gateway_profile(state, expected_cache=expected_cache) for state in states]
                for state in states:
                    assert state["Config"]["WorkingDir"] == "/opt/v8std"
                    assert state["HostConfig"]["NetworkMode"] == "none"
                for session in sessions:
                    session.close()
                return {"sessions": 2, "servers": len(ids), "network": "none",
                        "warm_cache": True, "long_lived_same_ids": True,
                        "profile": "native-gateway", "server_profiles": profiles}
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
    parser.add_argument("--gateway-warm-only", action="store_true",
                        help="Prepare one owned cache, then only check two warm host Gateway sessions")
    parser.add_argument("--require-default-source-404", action="store_true",
                        help="Explicit override regression: additionally require the default manifest to be absent")
    args = parser.parse_args()
    if args.host_gateway or args.gateway_warm_only:
        gateway_environment(os.environ)
    if args.gateway_warm_only and args.chrome:
        parser.error("--gateway-warm-only excludes browser acceptance")
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
    compose = ["docker", "compose", "-p", project, "-f", str(ROOT / "compose.yaml")]
    names = []
    report = {"platform": args.platform, "site_url": site_url, "successful_tools": sorted(TOOLS),
              "rejected_resources": {}, "browser": "incomplete: --chrome not supplied",
              "gateway": "incomplete: Gateway acceptance not requested"}
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

            for iteration, network_name in enumerate((network,) if args.gateway_warm_only else (network, "none")):
                started = time.monotonic()
                print(f"stdio {iteration}: starting {network_name}", file=sys.stderr, flush=True)
                name = project + f"-stdio-{iteration}"
                with (directory / f"stdio-{iteration}.log").open("w") as log:
                    session = Stdio(container(name, network_name), log)
                    try:
                        session.initialize()
                        ranking = check_tools(session.request, site_url)
                        report["rejected_resources"][f"stdio_{iteration}"] = check_resources_disabled(session.envelope)
                        report[f"stdio_{iteration}_ready_seconds"] = round(time.monotonic() - started, 2)
                        print(f"stdio {iteration}: ready", file=sys.stderr, flush=True)
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
                        namespace = "v1-" + hashlib.sha256(site_url.encode()).hexdigest() + "/"
                        assert all(path.startswith(namespace) for path in current), current
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
            if args.gateway_warm_only:
                report["stdio"] = "owned cold-online cache preparation only; EOF=0; cache UID10001"
                report["gateway"] = host_gateway_check(project, args.mcp_image, volume, site_url, directory)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return
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
                        "name": "v8std_explain_snippet", "arguments": {"snippet": body, "limit": 1}})),
                        seconds=STARTUP_SECONDS)
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
                process = subprocess.Popen(container(warm, "none", "streamable-http", cache=http_volume)
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
            for volume_name in (project + "-stdio-cache", project + "-empty"):
                subprocess.run(["docker", "volume", "rm", volume_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
