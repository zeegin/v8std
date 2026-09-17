"""Manual loopback-only smoke for the native Python launch and existing servers."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]


def check(url: str, maximum: int) -> dict:
    if urlparse(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("smoke is restricted to loopback servers")
    with httpx.Client(timeout=10, trust_env=False) as client:
        def rpc(method, params, ascii_json=False):
            payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                                 ensure_ascii=ascii_json).encode("utf-8")
            response = client.post(url, content=payload, headers={
                "Accept": "application/json, text/event-stream", "Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()["result"], len(payload)

        rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                           "clientInfo": {"name": "codex", "version": "snippet-smoke"}})
        catalog, _ = rpc("tools/list", {})
        tool = next(tool for tool in catalog["tools"] if tool["name"] == "v8std_explain_snippet")
        assert tool["inputSchema"]["properties"]["snippet"]["maxLength"] == maximum
        assert str(maximum) in tool["description"]
        signal = "\nУстановитьПривилегированныйРежим(Истина);"
        source = "😀" * (maximum - len(signal)) + signal
        sizes = {}
        for ascii_json in (False, True):
            response, size = rpc("tools/call", {"name": "v8std_explain_snippet",
                "arguments": {"snippet": source, "limit": 1}}, ascii_json)
            assert not response.get("isError")
            result = json.loads(response["content"][0]["text"])
            assert [item["id"] for item in result["standards"]] == ["std485"]
            sizes["escaped" if ascii_json else "utf8"] = size
        error, _ = rpc("tools/call", {"name": "v8std_explain_snippet",
            "arguments": {"snippet": "private_marker" + " " * maximum}})
        assert error["isError"] and "private_marker" not in json.dumps(error)
        for name, arguments in (
            ("v8std_search", {"query": "std437", "limit": 1}),
            ("v8std_get_page", {"id_or_alias_or_url": "std485", "body_limit": 1000}),
            ("v8std_get_related", {"id_or_alias_or_url": "std485", "limit": 1}),
            ("v8std_explain_diagnostics", {"codes": ["acc:1245"]}),
        ):
            response, _ = rpc("tools/call", {"name": name, "arguments": arguments})
            assert not response.get("isError"), name
        assert client.get(url, headers={"Accept": "text/event-stream"}).status_code == 405
        return {"url": url, "max_snippet_chars": maximum, "all_five_tools": "ok",
                "size_error_redacted": True, "post_only": True, "request_bytes": sizes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch", choices=["python"])
    parser.add_argument("--url")
    parser.add_argument("--limit", type=int, default=32000)
    args = parser.parse_args()
    if bool(args.launch) == bool(args.url):
        parser.error("choose --launch or --url")
    if args.url:
        print(json.dumps(check(args.url, args.limit)))
        return
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {**os.environ, "V8STD_MCP_MAX_SNIPPET_CHARS": str(args.limit)}
    command = [sys.executable, "-m", "runtime.v8std_mcp_server", "--pages", "docs/ai/pages.jsonl",
               "--vectors", "docs/ai/search-vectors.jsonl", "--host", "127.0.0.1", "--port", str(port)]
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(log.read())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=.1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise TimeoutError("local MCP did not start")
            print(json.dumps({"launch": args.launch, **check(f"http://127.0.0.1:{port}/mcp", args.limit)}))
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
