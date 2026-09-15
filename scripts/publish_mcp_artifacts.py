#!/usr/bin/env python3
"""Fail-closed CI coordination; the restricted host controller owns publication.

This helper stages Pages only after an exact committed receipt and public byte
verification. Its transport never grants an unrestricted host command.
"""
from __future__ import annotations

import ast
import argparse
import base64
from contextlib import contextmanager
import hashlib
import io
import json
import os
import re
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
import uuid
from pathlib import Path

from generate_mcp_snapshot import _atomic_file
from v8std_mcp_snapshot_format import (
    MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES, canonical_json, strict_json, validate_manifest, verify_archive,
)
from v8std_mcp_release import (
    attestation_command, http as release_http, read_file, smoke as runtime_smoke, validate_envelope, validate_upload,
)

REPOSITORY = "zeegin/v8std"
MANIFEST_URL = "https://v8std.ru/ai/mcp/v1/manifest.json"
IMAGE = "ghcr.io/zeegin/v8std-mcp"
SITE_IMAGE = "ghcr.io/zeegin/v8std-site"
GATES = {"architecture", "build", "tests", "benchmark"}


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          timeout=30).stdout


def input_identities(root, source_sha):
    """Hash committed input blobs, before source_sha salts the corpus descriptor.

    Runtime is the explicit Dockerfile COPY closure, not all scripts. Corpus
    includes producer imports and the pinned builder (including fonts/zlib).
    Generated docs outputs are not inputs; the strict builder regenerates them.
    """
    require(isinstance(source_sha, str) and re.fullmatch(r"[0-9a-f]{40}", source_sha), "source_sha")
    tree = {}
    for entry in git(root, "ls-tree", "-rz", source_sha).split(b"\0"):
        if entry:
            info, name = entry.split(b"\t", 1)
            mode, kind, blob = info.decode().split()
            tree[name.decode()] = (mode, kind, blob)

    def read(name):
        require(name in tree and tree[name][0] in {"100644", "100755"}, "input_not_regular")
        payload = git(root, "cat-file", "blob", tree[name][2])
        require(len(payload) <= 4 * 1024 * 1024, "input_size")
        return payload.decode()

    def expand(names):
        selected = set()
        for name in names:
            matches = {path for path in tree if path == name.rstrip("/") or path.startswith(name.rstrip("/") + "/")}
            require(bool(matches), "missing_input")
            selected.update(matches)
        return selected

    dockerfile = read("Dockerfile.mcp").replace("\\\n", " ")
    copies = []
    for line in dockerfile.splitlines():
        if re.match(r"\s*(ADD|COPY)\s", line, re.I):
            tokens = shlex.split(line)
            require(tokens[0].upper() == "COPY" and not any(token.startswith("--from") for token in tokens),
                    "unsupported_copy")
            inputs = [token for token in tokens[1:] if not token.startswith("--")][:-1]
            require(inputs and all(re.fullmatch(r"[a-zA-Z0-9_./-]+", path) and ".." not in path.split("/")
                                   for path in inputs), "unsupported_copy")
            copies.extend(inputs)
    require(bool(copies), "missing_copy")
    runtime = expand(["Dockerfile.mcp", ".dockerignore", ".github/workflows/ci.yml", *copies])
    corpus = expand(["docs", "zensical.toml", "retrieval-rules.yml", "LICENSE", "LICENSES",
                     "requirements-build.lock", "Dockerfile.ci", "deploy/ci", ".github/workflows/ci.yml",
                     "scripts/zensical_docs.sh", "scripts/zensical-version.sh",
                     "scripts/build_local_site.py",
                     "scripts/generate_ai_artifacts.py", "scripts/generate_search_vectors.py",
                     "scripts/generate_mcp_snapshot.py"])
    wrapper = read("scripts/zensical_docs.sh")
    invoked = re.findall(r'\$\{SCRIPT_DIR\}/([a-z_]+\.py)', wrapper)
    invoked += re.findall(r'script_dir / "([a-z_]+\.py)"', wrapper)
    corpus.update(expand(["scripts/" + name for name in invoked]))
    corpus -= {name for name in corpus if name.startswith(("docs/ai/", "docs/assets/images/social/"))
               or name in {"docs/llms.txt", "docs/llms-full.txt"}}
    pending = [name for name in corpus if name.startswith("scripts/") and name.endswith(".py")]
    inspected = set()
    while pending:
        name = pending.pop()
        if name in inspected:
            continue
        inspected.add(name)
        for node in ast.walk(ast.parse(read(name))):
            imports = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for module in imports:
                path = "scripts/" + module.removeprefix("scripts.").replace(".", "/") + ".py"
                if path in tree and path not in corpus:
                    corpus.add(path)
                    pending.append(path)

    def identity(paths):
        require(all(tree[name][0] in {"100644", "100755"} for name in paths), "input_not_regular")
        return hashlib.sha256(canonical_json({name: list(tree[name]) for name in sorted(paths)})).hexdigest()
    return {"runtime": identity(runtime), "corpus": identity(corpus)}


def choose_sources(trigger_sha, identities, published):
    """published contains independently successful states, never HEAD^ or a failed run."""
    require(re.fullmatch(r"[0-9a-f]{40}", trigger_sha) is not None, "source_sha")
    result = {}
    for kind in ("runtime", "corpus"):
        identity = identities[kind]
        require(re.fullmatch(r"[0-9a-f]{64}", identity) is not None, "input_identity")
        previous = published.get(kind)
        if previous is not None:
            require(type(previous) is dict and isinstance(previous.get("source_sha"), str)
                    and re.fullmatch(r"[0-9a-f]{40}", previous["source_sha"])
                    and isinstance(previous.get("input_id"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", previous["input_id"]), "published_state")
        changed = previous is None or previous["input_id"] != identity
        result[kind + "_sha"] = trigger_sha if changed else previous["source_sha"]
        result[kind + "_changed"] = changed
    return result


class PublicationError(ValueError):
    """Bounded local error code, never raw credentials or host output."""


def require(condition, code):
    if not condition:
        raise PublicationError(code)


def bounded_command(argv, *, payload=b"", seconds=30, limit=2 * 1024 * 1024, env=None):
    """No shell/PIPE capture; kill the owned group even after its leader exits."""
    deadline = time.monotonic() + seconds
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as output:
        source.write(payload)
        source.seek(0)
        process = subprocess.Popen(argv, stdin=source, stdout=output, stderr=subprocess.DEVNULL,
                                   start_new_session=True, env=env)
        try:
            while process.poll() is None:
                require(time.monotonic() < deadline, "command_timeout")
                require(output.tell() <= limit, "command_output")
                time.sleep(min(.02, max(0, deadline - time.monotonic())))
            require(process.returncode == 0, "command_failed")
            require(output.tell() <= limit, "command_output")
            output.seek(0)
            return output.read(limit + 1)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                # Darwin reports EPERM for a vanished process group. A live
                # leader is still a cleanup failure, not a successful command.
                require(process.poll() is not None, "command_cleanup")
            process.wait(timeout=2)


def anonymous_environment(directory):
    # Do not inherit alternate auth stores or a remote daemon selection.
    excluded = {"DOCKER_AUTH_CONFIG", "REGISTRY_AUTH_FILE", "DOCKER_CONTEXT", "DOCKER_HOST",
                "DOCKER_CERT_PATH", "DOCKER_TLS_VERIFY"}
    return {**{key: value for key, value in os.environ.items() if key not in excluded}, "DOCKER_CONFIG": directory}


def check_external_protection(branch, environment, policies):
    require(branch.get("protected") is True, "main_unprotected")
    require(environment.get("deployment_branch_policy") == {
        "protected_branches": False, "custom_branch_policies": True}, "environment_unrestricted")
    entries = policies.get("branch_policies", [])
    require(len(entries) == 1 and entries[0].get("type") == "branch"
            and entries[0].get("name") == "main", "environment_not_main_branch_only")


def read_state_artifact(payload):
    require(len(payload) <= 256 * 1024, "state_archive_size")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            require(len(entries) == 1 and entries[0].filename == "state.json"
                    and entries[0].file_size <= 128 * 1024
                    and not stat.S_ISLNK(entries[0].external_attr >> 16), "state_archive_shape")
            return strict_json(archive.read(entries[0]))
    except (zipfile.BadZipFile, RuntimeError):
        raise PublicationError("state_archive_invalid") from None


def last_published(root, main_sha, sequence, kind, api, download):
    """Read independent milestone artifacts, even when a later job in that run failed.

    This is internal CI state, not a public manifest or a new host authority.
    Missing/expired/malformed history never silently means a successful publish.
    Artifact upload steps run only after the corresponding verified milestone.
    """
    require(kind in {"runtime", "corpus"}, "state_kind")
    prefix = f"repos/{REPOSITORY}/actions"
    deadline = time.monotonic() + 120
    def candidates():
        for page in range(1, 101):
            require(time.monotonic() < deadline, "state_history_deadline")
            listing = api(prefix + f"/artifacts?per_page=100&page={page}")
            for artifact in sorted(listing["artifacts"], key=lambda entry: entry["id"], reverse=True):
                if artifact.get("name", "").startswith(f"mcp-{kind}-state-v1-"):
                    yield artifact
            if len(listing["artifacts"]) < 100:
                return
        raise PublicationError("state_history_window_exhausted")
    for artifact in candidates():
        source = artifact.get("workflow_run", {})
        if (source.get("head_branch") != "main" or source.get("repository_id") != source.get("head_repository_id")):
            continue
        require(type(source.get("id")) is int and type(artifact.get("id")) is int, "state_run")
        attempt = artifact["name"].removeprefix(f"mcp-{kind}-state-v1-")
        require(re.fullmatch(r"[1-9][0-9]{0,2}", attempt), "state_attempt")
        run = api(prefix + f"/runs/{source['id']}/attempts/{attempt}")
        if (run.get("path") != ".github/workflows/ci.yml" or run.get("event") not in {"push", "workflow_dispatch"}
                or run.get("repository", {}).get("full_name") != REPOSITORY
                or run.get("head_repository", {}).get("full_name") != REPOSITORY):
            continue
        require(type(run.get("run_number")) is int and type(run.get("run_attempt")) is int
                and run["run_attempt"] == int(attempt), "state_run")
        previous_sequence = run["run_number"] * 1000 + run["run_attempt"]
        if previous_sequence == sequence:
            continue  # This attempt's later job may see its own milestone.
        require(previous_sequence < sequence, "stale_run")
        require(run.get("status") == "completed" and run.get("head_branch") == "main"
                and run.get("head_sha") == source.get("head_sha"), "state_run")
        require(artifact.get("expired") is False, "published_state_expired")
        state = read_state_artifact(download(prefix + f"/artifacts/{artifact['id']}/zip"))
        fields = {"schema_version", "kind", "sequence", "trigger_sha", "source_sha", "input_id",
                  "image_digest" if kind == "runtime" else "manifest"}
        require(set(state) == fields and type(state["schema_version"]) is int and state["schema_version"] == 1
                and state["kind"] == kind and type(state["sequence"]) is int
                and state["sequence"] == previous_sequence and state["trigger_sha"] == run["head_sha"], "state_identity")
        for sha in (state["source_sha"], state["trigger_sha"]):
            require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha), "state_source")
            try:
                git(root, "merge-base", "--is-ancestor", sha, main_sha)
            except subprocess.CalledProcessError:
                raise PublicationError("state_not_main_ancestor") from None
        require(input_identities(root, state["source_sha"])[kind] == state["input_id"], "state_input_identity")
        if kind == "runtime":
            require(isinstance(state["image_digest"], str)
                    and re.fullmatch(r"sha256:[0-9a-f]{64}", state["image_digest"]), "state_image")
        else:
            require(public_manifest(state["manifest"])["source_sha"] == state["source_sha"], "state_corpus")
        return state
    return None


class CITransport:
    monotonic = staticmethod(time.monotonic)
    sleep = staticmethod(time.sleep)
    time = staticmethod(time.time)

    def __init__(self, *, release_host=None, key=None, known_hosts=None):
        self.release_host, self.key, self.known_hosts = release_host, key, known_hosts

    def command(self, command, payload, *, seconds=30):
        require(command in {"publish-index", "status", "validate-envelope", "deploy"}, "forced_command")
        require(isinstance(self.release_host, str)
                and re.fullmatch(r"[a-z_][a-z0-9_-]*@[a-z0-9][a-z0-9.-]*", self.release_host)
                and self.key and self.known_hosts, "ssh_not_configured")
        argv = ["ssh", "-F", "/dev/null", "-T", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
                "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=" + self.known_hosts,
                "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2",
                "-i", self.key, self.release_host, command]
        return strict_json(bounded_command(argv, payload=payload, seconds=seconds, limit=128 * 1024))

    def get(self, url, limit):
        require(url == MANIFEST_URL or re.fullmatch(
            r"https://ai\.v8std\.ru/indexes/v1/[0-9a-f]{64}/snapshot\.tar\.gz", url), "fetch_url")
        with tempfile.TemporaryDirectory(prefix="v8std-public-proof-") as directory:
            headers_path = Path(directory) / "headers"
            command = ["curl", "-q", "--silent", "--show-error", "--proto", "=https",
                       "--max-redirs", "0", "--max-time", "30", "--connect-timeout", "10",
                       "-H", "Accept-Encoding: identity", "--dump-header", str(headers_path)]
            def headers():
                raw = read_file(headers_path, 64 * 1024)
                lines = raw.rstrip().split(b"\r\n\r\n")[-1].splitlines()
                require(bool(lines) and re.fullmatch(rb"HTTP/[0-9.]+ [0-9]{3}(?: .*)?", lines[0]), "http_status")
                status = lines[0].split()[1]
                if status == b"404" and url == MANIFEST_URL:
                    raise FileNotFoundError("manifest_404")
                require(status == b"200", "http_status")
                fields = {}
                for line in lines[1:]:
                    require(b":" in line, "http_headers")
                    key, value = line.split(b":", 1)
                    key = key.strip().lower()
                    require(key not in fields, "duplicate_http_header")
                    fields[key] = value.strip()
                require(fields.get(b"content-encoding", b"identity") == b"identity", "http_encoding")
                return fields
            bounded_command([*command, "--head", url], seconds=32, limit=64 * 1024)
            head = headers()
            body = bounded_command([*command, "--max-filesize", str(limit), url], seconds=32, limit=limit)
            fields = headers()
            if b"content-length" in fields:
                require(fields[b"content-length"] == str(len(body)).encode(), "http_length")
            if url != MANIFEST_URL:
                require(fields.get(b"content-type", b"").split(b";")[0] == b"application/gzip"
                        and b"content-length" in fields and b"etag" in fields
                        and b"immutable" in fields.get(b"cache-control", b""), "archive_headers")
                require(head.get(b"content-length") == str(len(body)).encode(), "archive_head_length")
            return body

    def smoke(self, image, runtime_sha, manifest):
        """Anonymous pull + real cold default source, no site-url override/cache.

        Docker credentials are isolated in this temporary directory. The helper
        is invoked on the hosted runner, never against a production Docker host.
        Each platform gets a distinct bounded, hardened disposable container.
        """
        require(re.fullmatch(re.escape(IMAGE) + r"@sha256:[0-9a-f]{64}", image), "image_identity")
        bounded_command(attestation_command("oci://" + image, runtime_sha), seconds=90)
        with tempfile.TemporaryDirectory(prefix="v8std-anonymous-") as directory:
            env = anonymous_environment(directory)
            for platform in ("linux/amd64", "linux/arm64"):
                bounded_command(["docker", "pull", "--platform", platform, image], env=env, seconds=180)
                name = "v8std-ci-default-" + uuid.uuid4().hex
                primary = None
                try:
                    bounded_command(["docker", "run", "-d", "--name", name, "--label", "pro.v8std.ci=" + name,
                        "--platform", platform, "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                        "--init", "--pids-limit", "128", "--memory", "1024m", "--cpus", "2",
                        "--tmpfs", "/tmp:size=16m", "--tmpfs", "/var/lib/v8std-mcp:rw,size=256m,uid=10001,gid=10001,mode=0700",
                        "-p", "127.0.0.1::8000", image, "--transport", "streamable-http", "--host", "0.0.0.0",
                        "--port", "8000", "--refresh-seconds", "0"], env=env, seconds=30)
                    inspected = json.loads(bounded_command(["docker", "inspect", name], env=env))[0]
                    require(inspected["Config"]["Labels"].get("org.opencontainers.image.revision") == runtime_sha,
                            "image_source_label")
                    port = inspected["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
                    deadline = time.monotonic() + 390
                    record = {"runtime_source_sha": runtime_sha, "corpus_id": manifest["corpus_id"],
                              "archive_sha256": manifest["archive"]["sha256"], "hold_token": None}
                    while True:
                        try:
                            runtime_smoke("http://127.0.0.1:" + port, record, min(deadline, time.monotonic() + 30))
                            break
                        except ValueError:
                            require(time.monotonic() < deadline, "default_source_not_ready")
                            time.sleep(1)
                except BaseException as error:
                    primary = error
                    raise
                finally:
                    try:
                        found = bounded_command(["docker", "container", "ls", "-a", "--filter", "name=^/" + name + "$",
                                                 "--format", "{{.Names}}"], env=env).decode().splitlines()
                        require(found in ([], [name]), "fixture_inventory")
                        if found:
                            info = json.loads(bounded_command(["docker", "inspect", name], env=env))[0]
                            require(info["Config"]["Labels"].get("pro.v8std.ci") == name, "fixture_ownership")
                            bounded_command(["docker", "rm", "--force", name], env=env)
                            require(not bounded_command(["docker", "container", "ls", "-a", "--filter", "name=^/" + name + "$",
                                                         "--format", "{{.Names}}"], env=env).strip(), "fixture_cleanup")
                    except BaseException as error:
                        if primary is None:
                            raise
                        primary.add_note("owned default-source fixture cleanup failed: " + str(error))

    def local_smoke(self, image, runtime_sha, site_image, site_sha, manifest):
        """Exercise both exact digests through the retained isolated Compose.

        This explicit-source check is not the later public-default proof. Host
        MCP requests use the site's loopback proxy; runtime source and result
        links share the unchanged Compose v8std.localhost address.
        """
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="v8std-pair-proof-") as directory:
            for platform in ("linux/amd64", "linux/arm64"):
                project = "v8std-ci-pair-" + uuid.uuid4().hex[:16]
                env = {**anonymous_environment(directory), "DOCKER_DEFAULT_PLATFORM": platform,
                       "V8STD_SITE_IMAGE": site_image, "V8STD_MCP_IMAGE": image,
                       "V8STD_SITE_PORT": "18765", "V8STD_MCP_PORT": "18766",
                       "V8STD_SITE_PREFIX": "/", "V8STD_MCP_SITE_URL": "http://v8std.localhost:18765/"}
                compose = ["docker", "compose", "-p", project, "-f", str(root / "compose.yaml"), "--profile", "mcp"]
                primary = None
                try:
                    bounded_command([*compose, "pull"], env=env, seconds=240)
                    bounded_command([*compose, "up", "-d", "--no-build", "--pull", "never"], env=env, seconds=60)
                    for service, source in (("mcp", runtime_sha), ("site", site_sha)):
                        container = bounded_command([*compose, "ps", "-q", service], env=env).decode().strip()
                        require(re.fullmatch(r"[0-9a-f]{64}", container), "fixture_container")
                        info = strict_json(bounded_command(["docker", "inspect", container], env=env))[0]
                        require(info["Config"]["Labels"].get("org.opencontainers.image.revision") == source
                                and info["Config"]["User"] == "10001:10001"
                                and info["HostConfig"]["Privileged"] is False
                                and info["HostConfig"]["ReadonlyRootfs"] is True, "image_profile")
                    record = {"runtime_source_sha": runtime_sha, "corpus_id": manifest["corpus_id"],
                              "archive_sha256": manifest["archive"]["sha256"], "hold_token": None}
                    deadline = time.monotonic() + 390
                    while True:
                        try:
                            runtime_smoke("http://127.0.0.1:18766", record, min(deadline, time.monotonic() + 30))
                            break
                        except ValueError:
                            require(time.monotonic() < deadline, "local_source_not_ready")
                            time.sleep(1)
                except BaseException as error:
                    primary = error
                    raise
                finally:
                    try:
                        bounded_command([*compose, "down", "--volumes", "--timeout", "15"], env=env, seconds=60)
                        for kind in ("container", "network", "volume"):
                            query = ["docker", kind, "ls", "--filter", "label=com.docker.compose.project=" + project, "-q"]
                            if kind == "container":
                                query.append("-a")
                            require(not bounded_command(query, env=env).strip(), "pair_fixture_cleanup")
                    except BaseException as error:
                        if primary is None:
                            raise
                        primary.add_note("owned image-pair cleanup failed: " + str(error))

    def tag(self, image, source_sha):
        namespace, digest = image.split("@", 1)
        require(namespace in {IMAGE, SITE_IMAGE} and re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
                and re.fullmatch(r"[0-9a-f]{40}", source_sha), "image_identity")
        reference = "sha-" + source_sha
        existing = registry_manifest(namespace, reference)
        if existing is not None:
            require("sha256:" + hashlib.sha256(existing).hexdigest() == digest, "immutable_tag_conflict")
            return
        fresh_context(Path(__file__).resolve().parents[1], os.environ)
        bounded_command(["docker", "buildx", "imagetools", "create", "--tag", namespace + ":" + reference, image], seconds=90)
        observed = registry_manifest(namespace, reference)
        require(observed is not None and "sha256:" + hashlib.sha256(observed).hexdigest() == digest, "immutable_tag_digest")

    def promote(self, image):
        require(re.fullmatch(re.escape(IMAGE) + r"@sha256:[0-9a-f]{64}", image), "image_identity")
        fresh_context(Path(__file__).resolve().parents[1], os.environ)
        bounded_command(["docker", "buildx", "imagetools", "create", "--tag", IMAGE + ":stable", image], seconds=90)
        raw = bounded_command(["docker", "buildx", "imagetools", "inspect", "--raw", IMAGE + ":stable"], seconds=30)
        require("sha256:" + hashlib.sha256(raw).hexdigest() == image.split("@", 1)[1], "promoted_digest")


def authorized(context):
    require(set(context) == {"event", "repository", "ref", "sha", "main_sha", "run_id",
                             "run_number", "attempt", "gates"}, "context_fields")
    require(context["event"] in {"push", "workflow_dispatch"}
            and context["repository"] == REPOSITORY
            and context["ref"] == "refs/heads/main", "source_not_main")
    require(isinstance(context["sha"], str) and re.fullmatch(r"[0-9a-f]{40}", context["sha"])
            and context["sha"] == context["main_sha"], "stale_or_invalid_sha")
    for name, maximum in (("run_id", 2**53 - 1), ("run_number", 2**40), ("attempt", 999)):
        require(type(context[name]) is int and 0 < context[name] <= maximum, "run_identity")
    require(type(context["gates"]) is dict and set(context["gates"]) == GATES
            and all(value == "success" for value in context["gates"].values()), "failed_gate")


def public_manifest(manifest):
    result = validate_manifest(canonical_json(manifest))
    expected = "https://ai.v8std.ru/indexes/v1/" + result["archive"]["sha256"] + "/snapshot.tar.gz"
    require(result["archive"]["path"] == expected, "public_archive_path")
    return result


def expected_receipt(header):
    manifest = header["manifest"]
    return {"publication_id": header["publication_id"], "sequence": header["sequence"],
            "action": header["action"], "trigger_sha": header["trigger_sha"],
            "corpus_source_sha": manifest["source_sha"], "corpus_id": manifest["corpus_id"],
            "archive_sha256": manifest["archive"]["sha256"]}


def committed(receipt, header):
    require(type(receipt) is dict, "receipt_shape")
    require(all(receipt.get(key) == value for key, value in expected_receipt(header).items()),
            "receipt_identity")
    require(receipt.get("state") == "COMMITTED" and receipt.get("error_code") is None
            and receipt.get("cleanup_complete") is True, "receipt_not_committed")


class Publication:
    def __init__(self, context, adapter):
        authorized(context)
        self.context, self.adapter = context, adapter

    def header(self, action, manifest):
        context = self.context
        # A rerun is a new attempt, not a mutation of a host's immutable receipt.
        # Two ordered operations per attempt; gaps do not weaken host monotonicity.
        sequence = (context["run_number"] * 1000 + context["attempt"]) * 2
        return validate_upload({
            "schema_version": 1, "publication_id": f"ci-{context['run_id']}-{context['attempt']}-{action}",
            "sequence": sequence + (action == "reference"), "trigger_sha": context["sha"],
            "manifest": public_manifest(manifest), "action": action,
            "deadline": int(self.adapter.time()) + 300,
        })

    def acknowledge(self, header, archive=b""):
        validate_upload(header)
        wire = canonical_json(header) + b"\n"
        require(len(wire) <= 65536, "header_size")
        require(len(archive) == (header["manifest"]["archive"]["bytes"]
                                if header["action"] == "publish" else 0), "upload_size")
        deadline = self.adapter.monotonic() + 300
        initial = self.adapter.command("publish-index", wire + archive, seconds=30)
        require(initial.get("publication_id") == header["publication_id"], "receipt_identity")
        query = canonical_json({"schema_version": 1, "kind": "publication", "id": header["publication_id"]}) + b"\n"
        while self.adapter.monotonic() < deadline:
            receipt = self.adapter.command("status", query, seconds=min(20, deadline - self.adapter.monotonic()))
            require(type(receipt) is dict, "receipt_shape")
            require(all(receipt.get(key) == value for key, value in expected_receipt(header).items()),
                    "receipt_identity")
            require(receipt.get("state") in {"QUEUED", "RECEIVED", "VERIFIED", "COMMITTED"}
                    and receipt.get("error_code") is None, "publication_failed")
            if receipt["state"] == "COMMITTED":
                committed(receipt, header)
                return receipt
            self.adapter.sleep(min(2, deadline - self.adapter.monotonic()))
        raise PublicationError("publication_timeout")

    def archive(self, manifest):
        manifest = public_manifest(manifest)
        payload = self.adapter.get(manifest["archive"]["path"], MAX_ARCHIVE_BYTES)
        verify_archive(payload, manifest)
        return payload

    def prepare(self, pages_path, manifest, archive, *, enabled, previously_published=False):
        require(type(enabled) is bool and type(previously_published) is bool, "activation_type")
        header = receipt = None
        if enabled:
            manifest = public_manifest(manifest)
            verify_archive(archive, manifest)  # Local verification precedes all host effects.
            header = self.header("publish", manifest)
            receipt = self.acknowledge(header, archive)
            self.archive(manifest)  # A successful receipt alone is not public byte proof.
        else:
            try:
                payload = self.adapter.get(MANIFEST_URL, MAX_MANIFEST_BYTES)
            except FileNotFoundError:
                require(not previously_published, "published_manifest_missing")
                manifest = None
            else:
                manifest = public_manifest(validate_manifest(payload))
                self.archive(manifest)
        pages_path = Path(pages_path)
        # Caller passes its disposable Pages build, never the public site itself.
        if manifest is None:
            pages_path.unlink(missing_ok=True)
        else:
            pages_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_file(pages_path, canonical_json(manifest) + b"\n")
        return {"manifest": manifest, "header": header, "receipt": receipt}

    def finish(self, prepared, *, image=None, runtime_sha=None, promote=False):
        require(type(promote) is bool, "activation_type")
        manifest, header = prepared["manifest"], prepared["header"]
        if header is not None:
            validate_upload(header)
            require(header["action"] == "publish" and header["trigger_sha"] == self.context["sha"]
                    and header["manifest"] == manifest
                    and header["publication_id"] == self.header("publish", manifest)["publication_id"]
                    and header["sequence"] == self.header("publish", manifest)["sequence"], "prepared_identity")
            committed(prepared["receipt"], header)
        if manifest is None:
            require(not promote, "default_source_absent")
            return None
        observed = public_manifest(validate_manifest(self.adapter.get(MANIFEST_URL, MAX_MANIFEST_BYTES)))
        require(observed == manifest, "pages_manifest_mismatch")
        self.archive(manifest)
        if header is not None:
            self.acknowledge(self.header("reference", manifest))
        if image is not None:
            require(isinstance(image, str) and re.fullmatch(re.escape(IMAGE) + r"@sha256:[0-9a-f]{64}", image),
                    "image_identity")
            require(isinstance(runtime_sha, str) and re.fullmatch(r"[0-9a-f]{40}", runtime_sha), "runtime_sha")
            self.adapter.smoke(image, runtime_sha, manifest)
        require(not promote or image is not None, "image_required")
        if promote:
            self.adapter.promote(image)
        return manifest


def api(path):
    require(path.startswith(f"repos/{REPOSITORY}/"), "api_scope")
    return strict_json(bounded_command(["gh", "api", path], seconds=30))


def download_state(path):
    require(re.fullmatch(r"repos/zeegin/v8std/actions/artifacts/[0-9]+/zip", path), "api_scope")
    return bounded_command(["gh", "api", path], seconds=30, limit=256 * 1024)


def activated(environ, name):
    value = environ.get(name, "")
    require(value in {"", "false", "true"}, "activation_value")
    return value == "true"


def ci_context(environ, *, main_sha=None):
    try:
        context = {"event": environ["GITHUB_EVENT_NAME"], "repository": environ["GITHUB_REPOSITORY"],
                   "ref": environ["GITHUB_REF"], "sha": environ["GITHUB_SHA"], "main_sha": main_sha,
                   "run_id": int(environ["GITHUB_RUN_ID"]), "run_number": int(environ["GITHUB_RUN_NUMBER"]),
                   "attempt": int(environ["GITHUB_RUN_ATTEMPT"]),
                   "gates": strict_json(environ.get("MCP_GATES", "{}").encode())}
    except (KeyError, ValueError):
        raise PublicationError("ci_context") from None
    require(re.fullmatch(r"[0-9a-f]{40}", context["sha"]), "source_sha")
    return context


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), "output_symlink")
    _atomic_file(path, canonical_json(value) + b"\n")


def load(path):
    return strict_json(read_file(Path(path), 256 * 1024))


def plan_sources(root, environ, *, gates=False):
    context = ci_context(environ)
    require(git(root, "rev-parse", "HEAD").decode().strip() == context["sha"], "checkout_sha")
    identities = input_identities(root, context["sha"])
    published = {"runtime": None, "corpus": None}
    if (context["event"] in {"push", "workflow_dispatch"} and context["repository"] == REPOSITORY
            and context["ref"] == "refs/heads/main"):
        context["main_sha"] = api(f"repos/{REPOSITORY}/branches/main")["commit"]["sha"]
        require(context["sha"] == context["main_sha"], "stale_or_invalid_sha")
        require(environ.get("GITHUB_WORKFLOW_REF") == "zeegin/v8std/.github/workflows/ci.yml@refs/heads/main",
                "workflow_identity")
        sequence = context["run_number"] * 1000 + context["attempt"]
        expired = set()
        for kind in published:
            try:
                published[kind] = last_published(root, context["sha"], sequence, kind, api, download_state)
            except PublicationError as error:
                if str(error) != "published_state_expired":
                    raise
                expired.add(kind)
                # Recover only through existing externally verified identities,
                # never treat expired JSON as trustworthy or salt a new image.
        if published["corpus"] is None:
            adapter = CITransport()
            try:
                manifest = public_manifest(validate_manifest(adapter.get(MANIFEST_URL, MAX_MANIFEST_BYTES)))
            except FileNotFoundError:
                require("corpus" not in expired, "published_manifest_missing")
                manifest = None
            if manifest is not None:
                git(root, "merge-base", "--is-ancestor", manifest["source_sha"], context["sha"])
                verify_archive(adapter.get(manifest["archive"]["path"], MAX_ARCHIVE_BYTES), manifest)
                published["corpus"] = {"source_sha": manifest["source_sha"], "manifest": manifest,
                    "input_id": input_identities(root, manifest["source_sha"])["corpus"]}
        image_enabled = activated(environ, "MCP_IMAGE_PUBLICATION_ENABLED")
        runtime_enabled = activated(environ, "MCP_RUNTIME_DEPLOY_ENABLED")
        if published["runtime"] is None and (image_enabled or runtime_enabled):
            published["runtime"] = equivalent_runtime(root, context["sha"], identities["runtime"])
    if gates:
        authorized(context)
    return {"trigger_sha": context["sha"], "identities": identities, "published": published,
            **choose_sources(context["sha"], identities, published)}


def verify_build(directory):
    plan = load(directory / "plan.json")
    manifest = public_manifest(load(directory / "snapshot/manifest.json"))
    require(manifest["source_sha"] == plan["corpus_sha"], "built_corpus_source")
    name = manifest["archive"]["sha256"] + "/snapshot.tar.gz"
    archive = read_file(directory / "snapshot" / name, MAX_ARCHIVE_BYTES)
    verify_archive(archive, manifest)
    local = load(directory / "local-site/ai/mcp/v1/manifest.json")
    require(local["archive"]["path"] == name, "local_archive_path")
    local["archive"]["path"] = manifest["archive"]["path"]
    require(local == manifest and read_file(directory / "local-site/ai/mcp/v1" / name, MAX_ARCHIVE_BYTES) == archive,
            "public_local_corpus_mismatch")
    prior = plan["published"]["corpus"]
    if not plan["corpus_changed"]:
        require(prior is not None and prior["manifest"] == manifest, "unchanged_corpus_rebuilt_differently")
    return manifest, archive


def fresh_context(root, environ, environment="github-pages"):
    branch = api(f"repos/{REPOSITORY}/branches/main")
    context = ci_context(environ, main_sha=branch["commit"]["sha"])
    authorized(context)
    require(git(root, "rev-parse", "HEAD").decode().strip() == context["sha"], "checkout_sha")
    require(environ.get("GITHUB_WORKFLOW_REF") == "zeegin/v8std/.github/workflows/ci.yml@refs/heads/main",
            "workflow_identity")
    switches = [activated(environ, name) for name in (
        "MCP_IMAGE_PUBLICATION_ENABLED", "MCP_CORPUS_PUBLICATION_ENABLED", "MCP_RUNTIME_DEPLOY_ENABLED")]
    if any(switches):
        check_external_protection(branch, api(f"repos/{REPOSITORY}/environments/{environment}"),
            api(f"repos/{REPOSITORY}/environments/{environment}/deployment-branch-policies"))
    return context


@contextmanager
def transport(environ):
    """Only ephemeral owner-private key files; never edit ~/.ssh or Docker config."""
    with tempfile.TemporaryDirectory(prefix="v8std-release-ssh-") as directory:
        paths = []
        for name, setting in (("key", "MCP_RELEASE_SSH_KEY"), ("known-hosts", "MCP_RELEASE_KNOWN_HOSTS")):
            value = environ.get(setting, "")
            require(isinstance(value, str) and len(value.encode()) <= 65536 and "\0" not in value, "ssh_secret_size")
            path = Path(directory) / name
            with path.open("xb") as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(value.encode())
            paths.append(str(path) if value else None)
        yield CITransport(release_host=environ.get("MCP_RELEASE_HOST"), key=paths[0], known_hosts=paths[1])


def milestone(context, plan, kind, *, image_digest=None, manifest=None):
    return {"schema_version": 1, "kind": kind,
            "sequence": context["run_number"] * 1000 + context["attempt"],
            "trigger_sha": context["sha"], "source_sha": plan[kind + "_sha"],
            "input_id": plan["identities"][kind],
            **({"image_digest": image_digest} if kind == "runtime" else {"manifest": manifest})}


def registry_request(image, suffix):
    """Read-only GHCR token/manifest exchange; credentials only on stdin.

    A 404 is absence; authentication failure or transport failure never grants
    permission to overwrite a supposedly missing immutable tag.
    """
    require(image in {IMAGE, "ghcr.io/zeegin/v8std-site"}, "registry_namespace")
    repository = image.removeprefix("ghcr.io/")
    def request(url, authorization=b""):
        output = bounded_command(["curl", "-q", "--silent", "--show-error", "--proto", "=https",
            "--max-time", "30", "--max-redirs", "0", "--connect-timeout", "10", "--max-filesize", "2097152",
            "--header", "@-", "--header", "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json",
            "--write-out", "\n%{http_code}", url], payload=authorization, seconds=32, limit=2 * 1024 * 1024 + 4)
        body, status = output.rsplit(b"\n", 1)
        require(re.fullmatch(rb"[0-9]{3}", status), "registry_status")
        return int(status), body
    authorization = b""
    if os.environ.get("GH_TOKEN"):
        credentials = (os.environ.get("GITHUB_ACTOR", "x-access-token") + ":" + os.environ["GH_TOKEN"]).encode()
        authorization = b"Authorization: Basic " + base64.b64encode(credentials) + b"\n"
    status, raw = request("https://ghcr.io/token?service=ghcr.io&scope=repository:" + repository + ":pull", authorization)
    require(status == 200, "registry_authorization")
    token = strict_json(raw).get("token")
    require(isinstance(token, str) and 0 < len(token) <= 16384
            and all(33 <= ord(char) <= 126 for char in token), "registry_token")
    return request("https://ghcr.io/v2/" + repository + "/" + suffix,
                   b"Authorization: Bearer " + token.encode() + b"\n")


def registry_manifest(image, reference):
    require(re.fullmatch(r"sha-[0-9a-f]{40}|sha256:[0-9a-f]{64}", reference), "registry_reference")
    status, raw = registry_request(image, "manifests/" + reference)
    if status == 404:
        return None
    require(status == 200, "registry_manifest_unavailable")
    value = strict_json(raw)
    require(value.get("schemaVersion") == 2 and value.get("mediaType") in {
        "application/vnd.oci.image.index.v1+json", "application/vnd.docker.distribution.manifest.list.v2+json"}, "image_index")
    if reference.startswith("sha256:"):
        require("sha256:" + hashlib.sha256(raw).hexdigest() == reference, "registry_digest")
    return raw


def registry_tags():
    status, raw = registry_request(IMAGE, "tags/list?n=1000")
    if status == 404:
        return []
    require(status == 200, "registry_tags_unavailable")
    value = strict_json(raw)
    require(value.get("name") == IMAGE.removeprefix("ghcr.io/") and isinstance(value.get("tags"), list)
            and len(value["tags"]) < 1000 and all(isinstance(tag, str) for tag in value["tags"]), "registry_tags_window")
    return value["tags"]


def equivalent_runtime(root, main_sha, identity):
    """Recovery from existing immutable tags + main ancestry + attestations.

    No new registry metadata/schema. Only equivalent inputs can be reused without
    a CI milestone; a different arbitrary historical image is not 'last success'.
    The bounded window fails closed instead of silently ignoring older tags.
    """
    candidates = {tag[4:] for tag in registry_tags() if re.fullmatch(r"sha-[0-9a-f]{40}", tag)}
    deadline = time.monotonic() + 120
    checked = 0
    for source in git(root, "rev-list", "--topo-order", main_sha).decode().splitlines():
        if source not in candidates:
            continue
        checked += 1
        require(checked <= 64 and time.monotonic() < deadline, "identity_recovery_window")
        if input_identities(root, source)["runtime"] != identity:
            continue
        raw = registry_manifest(IMAGE, "sha-" + source)
        require(raw is not None, "immutable_image_disappeared")
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        bounded_command(attestation_command("oci://" + IMAGE + "@" + digest, source), seconds=90)
        return {"source_sha": source, "input_id": identity, "image_digest": digest}
    return None


def select_image(plan):
    source = plan["runtime_sha"]
    require(isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source), "runtime_sha")
    if not plan["runtime_changed"]:
        previous = plan["published"]["runtime"]
        require(previous is not None and previous["source_sha"] == source, "published_runtime_required")
        return {"build": False, "source_sha": source, "image_digest": previous["image_digest"]}
    raw = registry_manifest(IMAGE, "sha-" + source)
    if raw is None:
        return {"build": True, "source_sha": source, "image_digest": None}
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    bounded_command(attestation_command("oci://" + IMAGE + "@" + digest, source), seconds=90)
    return {"build": False, "source_sha": source, "image_digest": digest}


def select_site(source):
    require(isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source), "site_sha")
    raw = registry_manifest(SITE_IMAGE, "sha-" + source)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest() if raw is not None else None
    if digest:
        bounded_command(attestation_command("oci://" + SITE_IMAGE + "@" + digest, source), seconds=90)
    return {"build": raw is None, "source_sha": source, "image_digest": digest}


def record_images(context, adapter, runtime, site, manifest, *, runtime_digest, site_digest):
    authorized(context)
    references = []
    for selected, built, namespace in ((runtime, runtime_digest, IMAGE), (site, site_digest, SITE_IMAGE)):
        digest = built if selected["build"] else selected["image_digest"]
        require(isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", digest), "image_digest")
        require(not selected["build"] or selected["source_sha"] == context["sha"], "rebuilt_source_identity")
        image = namespace + "@" + digest
        bounded_command(attestation_command("oci://" + image, selected["source_sha"]), seconds=90)
        references.append(image)
    adapter.local_smoke(references[0], runtime["source_sha"], references[1], site["source_sha"], manifest)
    # Initial push is by digest only. An interrupted/unverified candidate never
    # occupies an immutable source tag; reruns do not overwrite existing tags.
    for image, selected in zip(references, (runtime, site)):
        adapter.tag(image, selected["source_sha"])
    return {"source_sha": runtime["source_sha"], "image_digest": references[0].split("@", 1)[1]}


def verify_running_runtime(source_sha):
    """A COMMITTED journal is not health; exercise the actual TLS/MCP endpoint.

    A valid stale corpus is allowed by the runtime contract. Bracket real tool
    calls with its current generation, rather than demanding an immediate refresh.
    """
    deadline = time.monotonic() + 30
    url = "https://ai.v8std.ru"
    health = strict_json(release_http(url + "/healthz", deadline))
    record = {"runtime_source_sha": source_sha, "corpus_id": health.get("corpus_id"),
              "archive_sha256": health.get("archive_sha256"), "hold_token": health.get("hold_token")}
    require(all(isinstance(record[key], str) and re.fullmatch(r"[0-9a-f]{64}", record[key])
                for key in ("corpus_id", "archive_sha256")), "live_corpus_identity")
    return runtime_smoke(url, record, deadline)


def deploy_runtime(context, adapter, accepted, *, enabled, configuration_digest, platform):
    authorized(context)
    require(type(enabled) is bool, "activation_type")
    if not enabled:
        return {"state": "DISABLED"}
    runtime = accepted.get("runtime")
    require(isinstance(runtime, dict) and re.fullmatch(r"sha256:[0-9a-f]{64}", runtime.get("image_digest", ""))
            and re.fullmatch(r"[0-9a-f]{40}", runtime.get("source_sha", "")), "published_runtime_required")
    manifest = public_manifest(accepted["manifest"])
    require(isinstance(configuration_digest, str) and re.fullmatch(r"[0-9a-f]{64}", configuration_digest)
            and platform in {"linux/amd64", "linux/arm64"}, "runtime_configuration")
    previous = adapter.command("status", b"")
    require(previous.get("state") in {"COMMITTED", "FAILED", "ROLLED_BACK"}
            and previous.get("cleanup_complete") is True, "predecessor_or_recovery_required")
    if (previous["state"] == "COMMITTED" and previous.get("error_code") is None
            and previous.get("image_digest") == runtime["image_digest"]
            and previous.get("configuration_digest") == configuration_digest):
        require(previous.get("runtime_source_sha") == runtime["source_sha"], "active_identity")
        verify_running_runtime(runtime["source_sha"])
        return {"state": "UNCHANGED", "image_digest": runtime["image_digest"]}
    raw = registry_manifest(IMAGE, runtime["image_digest"])
    require(raw is not None, "published_runtime_required")
    os_name, architecture = platform.split("/")
    descriptors = [item for item in strict_json(raw).get("manifests", [])
                   if isinstance(item, dict) and isinstance(item.get("platform"), dict)
                   and item["platform"].get("os") == os_name and item["platform"].get("architecture") == architecture
                   and item["platform"].get("variant", "") in ({"", "v8"} if architecture == "arm64" else {""})]
    require(len(descriptors) == 1, "platform_descriptor")
    envelope = {"schema_version": 1, "release_id": f"ci-{context['run_id']}-{context['attempt']}",
        "sequence": context["run_number"] * 1000 + context["attempt"], "trigger_sha": context["sha"],
        "runtime_source_sha": runtime["source_sha"], "image": IMAGE, "image_digest": runtime["image_digest"],
        "platform_digest": descriptors[0]["digest"], "configuration_digest": configuration_digest,
        "corpus_id": manifest["corpus_id"], "archive_sha256": manifest["archive"]["sha256"],
        "deadline": int(adapter.time()) + 300}
    validate_envelope(canonical_json(envelope), now=adapter.time())
    wire = canonical_json(envelope) + b"\n"
    deadline = adapter.monotonic() + 300
    require(adapter.command("validate-envelope", wire) == envelope, "validated_envelope_identity")
    initial = adapter.command("deploy", wire)
    require(isinstance(initial, dict) and initial.get("release_id") == envelope["release_id"], "release_queue_identity")
    query = canonical_json({"schema_version": 1, "kind": "release", "id": envelope["release_id"]}) + b"\n"
    while adapter.monotonic() < deadline:
        result = adapter.command("status", query, seconds=min(20, deadline - adapter.monotonic()))
        require(isinstance(result, dict) and all(result.get(key) == value for key, value in envelope.items()), "release_receipt_identity")
        require(result.get("state") in {"RECEIVED", "VERIFIED", "PREPARED", "READY", "SWITCHED", "COMMITTED"}
                and result.get("error_code") is None, "release_failed")
        if result.get("state") == "COMMITTED" and result.get("cleanup_complete") is True:
            require(result.get("error_code") is None, "release_failed")
            verify_running_runtime(runtime["source_sha"])
            return result
        adapter.sleep(min(2, deadline - adapter.monotonic()))
    raise PublicationError("release_timeout")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "value", "guard", "verify-build", "image-plan", "record-image",
                                            "prepare-pages", "finish", "deploy"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--directory", type=Path, default=Path(".ci"))
    parser.add_argument("--field", choices=["runtime_sha", "corpus_sha", "runtime_changed", "corpus_changed"])
    parser.add_argument("--environment", choices=["github-pages", "mcp-production"])
    args = parser.parse_args(argv)
    root, directory = args.root.resolve(), args.directory.resolve()
    try:
        if args.command == "plan":
            save(directory / "plan.json", plan_sources(root, os.environ))
        elif args.command == "value":
            require(args.field is not None, "field_required")
            value = load(directory / "plan.json")[args.field]
            print(str(value).lower() if isinstance(value, bool) else value)
        elif args.command == "guard":
            require(args.environment is not None, "environment_required")
            plan = plan_sources(root, os.environ, gates=True)
            switches = [activated(os.environ, name) for name in (
                "MCP_IMAGE_PUBLICATION_ENABLED", "MCP_CORPUS_PUBLICATION_ENABLED", "MCP_RUNTIME_DEPLOY_ENABLED")]
            enabled = any(switches)
            if enabled:
                branch = api(f"repos/{REPOSITORY}/branches/main")
                environment = api(f"repos/{REPOSITORY}/environments/{args.environment}")
                policies = api(f"repos/{REPOSITORY}/environments/{args.environment}/deployment-branch-policies")
                check_external_protection(branch, environment, policies)
            if (directory / "plan.json").exists():
                original = load(directory / "plan.json")
                require(all(plan[key] == original[key] for key in ("runtime_sha", "corpus_sha", "identities", "trigger_sha")),
                        "source_plan_changed_since_build")
            save(directory / "plan.json", plan)
        elif args.command == "verify-build":
            manifest, _ = verify_build(directory)
            print("verified public/local corpus " + manifest["corpus_id"])
        else:
            context = fresh_context(root, os.environ, "mcp-production" if args.command == "deploy" else "github-pages")
            plan = load(directory / "plan.json")
            require(plan["trigger_sha"] == context["sha"], "plan_trigger")
            with transport(os.environ) as adapter:
                publication = Publication(context, adapter)
                if args.command == "image-plan":
                    require(activated(os.environ, "MCP_IMAGE_PUBLICATION_ENABLED"), "image_publication_disabled")
                    images = {"runtime": select_image(plan), "site": select_site(context["sha"])}
                    save(directory / "images.json", images)
                    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                        output.write("build=" + str(images["runtime"]["build"]).lower() + "\n")
                        output.write("site_build=" + str(images["site"]["build"]).lower() + "\n")
                elif args.command == "record-image":
                    require(activated(os.environ, "MCP_IMAGE_PUBLICATION_ENABLED"), "image_publication_disabled")
                    manifest, _ = verify_build(directory)
                    images = load(directory / "images.json")
                    require(images["runtime"]["source_sha"] == plan["runtime_sha"]
                            and images["site"]["source_sha"] == context["sha"], "image_plan_source")
                    runtime = record_images(context, adapter, images["runtime"], images["site"], manifest,
                        runtime_digest=os.environ.get("MCP_BUILT_DIGEST"), site_digest=os.environ.get("MCP_SITE_BUILT_DIGEST"))
                    save(directory / "runtime-state/state.json", milestone(context, plan, "runtime",
                                                                          image_digest=runtime["image_digest"]))
                elif args.command == "prepare-pages":
                    manifest, archive = verify_build(directory)
                    enabled = activated(os.environ, "MCP_CORPUS_PUBLICATION_ENABLED")
                    prepared = publication.prepare(root / "site/ai/mcp/v1/manifest.json", manifest, archive,
                        enabled=enabled, previously_published=plan["published"]["corpus"] is not None)
                    save(directory / "prepared.json", prepared)
                    if enabled:
                        save(directory / "corpus-state/state.json", milestone(context, plan, "corpus", manifest=manifest))
                elif args.command == "finish":
                    runtime = (load(directory / "runtime-state/state.json") if (directory / "runtime-state/state.json").exists()
                               else plan["published"]["runtime"])
                    image_enabled = activated(os.environ, "MCP_IMAGE_PUBLICATION_ENABLED")
                    require(not image_enabled or runtime is not None, "published_runtime_required")
                    manifest = publication.finish(load(directory / "prepared.json"),
                        image=IMAGE + "@" + runtime["image_digest"] if image_enabled else None,
                        runtime_sha=runtime["source_sha"] if runtime else None, promote=image_enabled)
                    save(directory / "accepted.json", {"trigger_sha": context["sha"], "runtime": runtime, "manifest": manifest})
                elif args.command == "deploy":
                    accepted = load(directory / "accepted.json")
                    require(accepted["trigger_sha"] == context["sha"], "accepted_trigger")
                    result = deploy_runtime(context, adapter, accepted,
                        enabled=activated(os.environ, "MCP_RUNTIME_DEPLOY_ENABLED"),
                        configuration_digest=os.environ.get("MCP_CONFIGURATION_DIGEST"), platform=os.environ.get("MCP_PLATFORM"))
                    print("runtime " + result["state"])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, PublicationError) else getattr(error, "code", type(error).__name__)
        parser.exit(1, code + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
