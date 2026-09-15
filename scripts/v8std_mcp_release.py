"""Restricted host release transaction. Install reviewed code as root-owned files.

The public CLI has no path, environment, command, trust-policy or mount options.
Adapters own all external effects. Journals precede effects; deterministic object
names let recovery reconcile Docker operations whose CLI was killed mid-call.
This file is deliberately absent from the runtime image.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# The installed, root-owned module directory is the only additional import root
# under python -I. Never read PYTHONPATH or code from a release envelope.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v8std_mcp_snapshot_format import (
    MAX_ARCHIVE_BYTES, canonical_json, strict_json, validate_manifest, verify_archive,
)

IMAGE = "ghcr.io/zeegin/v8std-mcp"
REPO = "zeegin/v8std"
WORKFLOW = "zeegin/v8std/.github/workflows/ci.yml"
REF = "refs/heads/main"
ROOT = Path("/var/lib/v8std-release")
POLICY = Path("/etc/v8std-release/policy.json")
INSTALL = Path("/opt/v8std-release/scripts/v8std_mcp_release.py")
LEGACY_UNIT = "v8std-mcp.service"
LEGACY_APP = Path("/opt/v8std-mcp")
LEGACY_DATA = Path("/var/lib/v8std-mcp")
USAGE_LOG = Path("/var/log/v8std-mcp/tool-usage.jsonl")
USAGE_LOG_TARGET = "/var/log/v8std-mcp-usage.jsonl"
LEGACY_CONFIG = Path("/etc/systemd/system/v8std-mcp.service")
LEGACY_PYTHON = Path("/usr/bin/python3.12")
LEGACY_CACHE = {"pages.jsonl", "search-vectors.jsonl", "llms.txt", "llms-full.txt"}
RESTORE_STAGE = ".v8std-release-restore-v1"
BOOTSTRAP_WINDOW = Path("/etc/v8std-release/bootstrap.json")
LEGACY_GUARD = ("[Unit]\nRequires=v8std-bootstrap-recover.timer\nAfter=v8std-bootstrap-recover.timer\n"
    "\n[Service]\nExecCondition=+/usr/bin/python3 -I /opt/v8std-release/scripts/v8std_mcp_release.py _legacy-allowed\n")
BOOTSTRAP_SERVICE = ("[Unit]\nDescription=Recover operator v8std first migration independently of SSH\n"
    "After=docker.service nginx.service network-online.target\nWants=network-online.target\n\n"
    "[Service]\nType=exec\nExecStart=/usr/bin/python3 -I /opt/v8std-release/scripts/v8std_mcp_release.py bootstrap-recover\n"
    "RuntimeMaxSec=300s\nTimeoutStopSec=5s\nKillMode=control-group\nUMask=0077\nLimitNOFILE=4096\n"
    "PrivateTmp=yes\nNoNewPrivileges=yes\nProtectHome=yes\n")
BOOTSTRAP_TIMER = ("[Unit]\nDescription=Independent first-migration recovery guard\n\n[Timer]\n"
    "OnBootSec=5s\nOnUnitInactiveSec=15s\nUnit=v8std-bootstrap-recover.service\n\n"
    "[Install]\nWantedBy=timers.target\n")
TRANSACTION = 300
READINESS = 90
SMOKE = DRAIN = 30
STOP = 45
# Rollback gets a live budget even if preparation uses its entire work allowance.
# 90 ready + 30 smoke + 45 stop + 15 nginx/control overhead.
RECOVERY_RESERVE = 180
TERMINAL = {"FAILED", "ROLLED_BACK", "COMMITTED", "RECOVERY_REQUIRED"}
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
INDEX_TYPES = {"application/vnd.oci.image.index.v1+json",
               "application/vnd.docker.distribution.manifest.list.v2+json"}
MANIFEST_TYPES = {"application/vnd.oci.image.manifest.v1+json",
                  "application/vnd.docker.distribution.manifest.v2+json"}
CONFIG_TYPES = {"application/vnd.oci.image.config.v1+json",
                "application/vnd.docker.container.image.v1+json"}


class ReleaseError(ValueError):
    """Codes only; raw external errors and command output never enter status."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise ReleaseError(code)


def matches(pattern, value):
    return isinstance(value, str) and bool(pattern.fullmatch(value))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw, limit=8192):
    require(len(raw) <= limit, "input_size")
    try:
        value = strict_json(raw)
        require(isinstance(value, dict), "input_shape")
        return value
    except ValueError:
        raise ReleaseError("input_shape") from None


def validate_envelope(raw, *, now=None, expired=False):
    value = parse(raw)
    require(set(value) == {"schema_version", "release_id", "sequence", "runtime_source_sha",
        "trigger_sha", "image", "image_digest", "platform_digest", "configuration_digest",
        "corpus_id", "archive_sha256", "deadline"}, "envelope_fields")
    require(type(value["schema_version"]) is int and value["schema_version"] == 1, "schema")
    require(matches(ID, value["release_id"]), "release_id")
    require(type(value["sequence"]) is int and 0 < value["sequence"] <= 2**53 - 1, "sequence")
    require(value["image"] == IMAGE, "namespace")
    for key in ("runtime_source_sha", "trigger_sha"):
        require(matches(SHA, value[key]), key)
    for key in ("image_digest", "platform_digest"):
        require(matches(DIGEST, value[key]), key)
    for key in ("configuration_digest", "corpus_id", "archive_sha256"):
        require(matches(HEX, value[key]), key)
    require(type(value["deadline"]) is int, "deadline")
    if not expired:
        now = time.time() if now is None else now
        require(now < value["deadline"] <= now + TRANSACTION, "deadline")
    return value


def read_file(path, limit=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "file_shape")
        raw = stream.read(limit + 1)
        require(len(raw) <= limit, "file_size")
        return raw


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def ensure_directory(path, mode=0o700):
    if not path.exists():
        ensure_directory(path.parent)
        path.mkdir(mode=mode, exist_ok=True)
        sync_dir(path.parent)
    require(stat.S_ISDIR(path.lstat().st_mode), "directory_shape")


def atomic(path, raw, *, mode=0o600):
    ensure_directory(path.parent)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.replace(name, path)
        sync_dir(path.parent)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json(path, value, *, mode=0o600):
    # Operational timestamps/health contain finite floats; snapshot descriptors
    # and envelope hashes keep the separate float-free canonical encoding.
    atomic(path, json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode(), mode=mode)


def read_record(path):
    # The wire header remains <=64KiB; a durable receipt wraps it with state.
    # This host-owned record limit must not accidentally reapply the 8KiB
    # release-envelope limit to valid corpus manifests or publication receipts.
    return parse(read_file(path, 128 * 1024), 128 * 1024)


@contextmanager
def locked(root):
    ensure_directory(root)
    fd = os.open(root / "release.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ReleaseError("busy") from None
        yield
    finally:
        os.close(fd)


def remaining(deadline, cap=None):
    value = deadline - time.monotonic()
    require(value > 0, "deadline")
    return min(value, cap) if cap is not None else value


def run(argv, deadline, *, limit=2 * 1024 * 1024):
    """No shell. Kill/reap the CLI process group; daemon effects need reconciliation."""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen([str(x) for x in argv], stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.DEVNULL, start_new_session=True,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", "HOME": "/var/lib/v8std-release"})
        try:
            while process.poll() is None:
                require(output.tell() <= limit, "command_output")
                time.sleep(min(.025, remaining(deadline)))
            require(process.returncode == 0, "command_failed")
            require(output.tell() <= limit, "command_output")
            output.seek(0)
            return output.read(limit + 1)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def trusted_policy(path=POLICY):
    # Reject symlinked/writable policy and all parents before interpreting paths.
    trusted_path(path)
    policy = parse(read_file(path), 65536)
    return validate_policy(policy)


def trusted_path(path):
    for entry in (path, *path.parents):
        info = entry.lstat()
        require(not stat.S_ISLNK(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                "policy_permissions")


def prepare_usage_log(*, create=True):
    """Provision only the fixed private inode; never repair/truncate history."""
    parent = USAGE_LOG.parent
    trusted_path(parent.parent)
    try:
        try:
            parent.mkdir(mode=0o700)
            os.chown(parent, 0, 0)
            sync_dir(parent.parent)
        except FileExistsError:
            pass
        directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory)
            require((info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) == (0, 0, 0o700), "usage_log_directory")
            flags = os.O_NOFOLLOW | os.O_NONBLOCK
            try:
                fd = os.open(USAGE_LOG.name, os.O_RDONLY | flags, dir_fd=directory)
            except FileNotFoundError:
                require(create, "usage_log_missing")
                fd = os.open(USAGE_LOG.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | flags, 0o600, dir_fd=directory)
                try:
                    os.fchown(fd, 10001, 0)
                    os.fchmod(fd, 0o640)  # Explicit final mode despite UMask0077.
                    os.fsync(fd)
                    os.fsync(directory)
                except BaseException:
                    os.close(fd)
                    raise
            try:
                info = os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                        and (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) == (10001, 0, 0o640), "usage_log_file")
            finally:
                os.close(fd)
        finally:
            os.close(directory)
    except OSError:
        raise ReleaseError("usage_log_file") from None


def check_usage_binding(info):
    """Start-only guard: a malformed logging profile cannot forbid owned stop."""
    mounts = info.get("Mounts") or []
    selected = [mount for mount in mounts if mount.get("Destination") == USAGE_LOG_TARGET]
    require(len(selected) == 1 and selected[0].get("Type") == "bind"
            and selected[0].get("Source") == str(USAGE_LOG) and selected[0].get("RW") is True, "usage_log_binding")
    for mount in mounts:
        if mount is selected[0]:
            continue
        source = Path(mount.get("Source", ""))
        require(source not in USAGE_LOG.parents and not source.is_relative_to(USAGE_LOG.parent)
                and Path(mount.get("Destination", "")) not in Path(USAGE_LOG_TARGET).parents, "usage_log_exposure")
    command = info.get("Config", {}).get("Cmd") or []
    flags = [i for i, arg in enumerate(command) if arg == "--usage-log" or arg.startswith("--usage-log=")]
    require(len(flags) == 1 and command[flags[0]:flags[0] + 2] == ["--usage-log", USAGE_LOG_TARGET], "usage_log_argument")


def validate_bootstrap_window(window, envelope, *, recovery=False):
    require(set(window) == {"schema_version", "start_utc", "end_utc", "return_reserve_seconds",
            "envelope_sha256", "mode", "legacy_unit", "legacy_source_sha", "backup_manifest_sha256",
            "capacity"}, "bootstrap_fields")
    require(type(window["schema_version"]) is int and window["schema_version"] == 1, "schema")
    for key in ("start_utc", "end_utc", "return_reserve_seconds"):
        require(type(window[key]) is int, "bootstrap_window")
    duration = window["end_utc"] - window["start_utc"]
    require(0 < duration <= 7200 and 1800 <= window["return_reserve_seconds"] < duration, "bootstrap_window")
    require(window["envelope_sha256"] == digest(canonical_json(envelope)), "bootstrap_envelope")
    require(window["legacy_unit"] == LEGACY_UNIT and window["mode"] in {"overlap", "stop-start"}, "bootstrap_target")
    require(matches(SHA, window["legacy_source_sha"]) and matches(HEX, window["backup_manifest_sha256"]), "bootstrap_identity")
    capacity = window["capacity"]
    require(isinstance(capacity, dict) and set(capacity) == {
        "disk_bytes", "available_memory_bytes", "file_descriptors", "network_evidence"}, "capacity")
    require(all(type(capacity[k]) is int and capacity[k] > 0 for k in (
        "disk_bytes", "available_memory_bytes", "file_descriptors"))
        and matches(HEX, capacity["network_evidence"]), "capacity")
    if not recovery:
        now = time.time()
        require(window["start_utc"] <= now < window["end_utc"] - window["return_reserve_seconds"], "bootstrap_window")
        require(envelope["deadline"] <= window["end_utc"] - window["return_reserve_seconds"], "bootstrap_window")
    return window


def legacy_start_allowed(root):
    # ExecCondition is fail-closed even with corrupt journal or missing active.json.
    # An enabled legacy unit must never race accepted Docker recovery at boot.
    if (Path(root) / "active.json").exists():
        return False
    records = Controller(root, None).journals()
    if any(item["state"] == "COMMITTED" for item in records):
        return False
    if not records:
        return True
    latest = max(records, key=lambda item: item["envelope"]["sequence"])
    return latest.get("kind") != "bootstrap" or latest.get("legacy_start_allowed") is True


def file_hash(path, deadline):
    hashed = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "backup_file")
        while chunk := stream.read(65536):
            remaining(deadline)
            hashed.update(chunk)
    return hashed.hexdigest()


def restore_file(source, target, entry, deadline):
    """Fresh destination mtime is essential for the original legacy cache TTL.

    Stream, hash, fchown/fchmod and fsync before rename. No copy2/stale timestamps.
    Usage logs are never enumerated, copied, logged or replaced here.
    """
    require(file_hash(source, deadline) == entry["sha256"], "backup_hash")
    ensure_directory(target.parent)
    # Same-filesystem private staging survives SIGKILL without being confused
    # with unlisted application code. One deterministic owned slot per target;
    # retry truncates only that protected regular file, never a link or path
    # received from a caller. No wildcard removal or cleanup of legacy files.
    staging = target.parent / RESTORE_STAGE
    ensure_directory(staging)
    info = staging.lstat()
    require(info.st_uid == os.geteuid() and info.st_mode & 0o777 == 0o700, "restore_staging")
    name = staging / digest(str(target).encode())
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
            info = os.fstat(output.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "restore_staging")
            output.truncate(0)
            while chunk := input_file.read(65536):
                remaining(deadline)
                output.write(chunk)
            output.flush()
            os.fchown(output.fileno(), entry["uid"], entry["gid"])
            os.fchmod(output.fileno(), entry["mode"])
            os.fsync(output.fileno())
        require(file_hash(Path(name), deadline) == entry["sha256"], "restore_hash")
        os.replace(name, target)
        sync_dir(target.parent)
        sync_dir(staging)
    finally:
        Path(name).unlink(missing_ok=True)


def backup_inventory(root, window, deadline):
    """Root-owned, bounded full app manifest; roots are compiled, never supplied."""
    backup = root / "legacy"
    path = backup / "manifest.json"
    trusted_path(path)
    raw = read_file(path, 16 * 1024 * 1024)
    require(digest(raw) == window["backup_manifest_sha256"], "backup_manifest")
    value = parse(raw, 16 * 1024 * 1024)
    require(set(value) == {"schema_version", "app", "cache", "directories", "unit", "upstream", "interpreter_sha256"}
            and type(value["schema_version"]) is int and value["schema_version"] == 1, "backup_fields")
    require(matches(HEX, value["interpreter_sha256"]), "backup_interpreter")
    require(set(value["cache"]) == LEGACY_CACHE and isinstance(value["app"], dict)
            and 1 <= len(value["app"]) <= 20000, "backup_files")
    require({"scripts/v8std_mcp_server.py", "scripts/v8std_mcp_index.py", "scripts/v8std_retrieval_rules.py",
             "venv/pyvenv.cfg", "venv/bin/python"} <= set(value["app"]), "backup_incomplete")
    for component in ("app", "cache"):
        require(set(value["directories"]) == {"app", "cache"}, "backup_directories")
        directories = value["directories"][component]
        expected = {str(parent) for name in value[component] for parent in Path(name).parents}
        require(set(directories) == expected, "backup_directories")
        for entry in directories.values():
            require(set(entry) == {"mode", "uid", "gid"} and type(entry["mode"]) is int
                    and 0 <= entry["mode"] <= 0o777 and all(type(entry[k]) is int and
                    0 <= entry[k] <= 2**31-1 for k in ("uid", "gid")), "backup_metadata")
        for relative, entry in value[component].items():
            parts = relative.split("/")
            require(len(relative) <= 512 and all(matches(re.compile(r"[A-Za-z0-9_.+@-]+\Z"), p)
                    and p not in {".", ".."} for p in parts), "backup_path")
            require(isinstance(entry, dict), "backup_entry")
            if "link" in entry:
                require(component == "app" and set(entry) == {"link"}, "backup_link")
                link = entry["link"]
                require(isinstance(link, str) and len(link) <= 512, "backup_link")
                destination = Path(os.path.normpath(str(LEGACY_APP / relative / ".." / link)))
                require(destination == LEGACY_PYTHON or destination.is_relative_to(LEGACY_APP), "backup_link")
                # Manifest links are data; protected backup contains no symlinks.
                continue
            require(set(entry) == {"sha256", "mode", "uid", "gid"}, "backup_entry")
            require(matches(HEX, entry["sha256"]) and type(entry["mode"]) is int
                    and 0 <= entry["mode"] <= 0o777 and all(type(entry[k]) is int and
                    0 <= entry[k] <= 2**31-1 for k in ("uid", "gid")), "backup_metadata")
            source = backup / component / relative
            trusted_path(source)
            require(file_hash(source, deadline) == entry["sha256"], "backup_hash")
    for name in ("unit", "upstream"):
        require(set(value[name]) == {"sha256", "mode", "uid", "gid"}
                and matches(HEX, value[name]["sha256"]) and value[name]["uid"] == 0
                and value[name]["gid"] == 0 and value[name]["mode"] in {0o600, 0o644}, "backup_config")
        trusted_path(backup / name)
        require(file_hash(backup / name, deadline) == value[name]["sha256"], "backup_hash")
    return value


def validate_policy(policy):
    require(set(policy) == {"schema_version", "enabled", "runtime_enabled", "platform", "public_url", "configs",
            "capacity", "ports", "nginx_include", "static_root"}, "policy_fields")
    require(type(policy["schema_version"]) is int and policy["schema_version"] == 1
            and policy["enabled"] is True, "not_activated")
    require(type(policy["runtime_enabled"]) is bool, "runtime_activation")
    require(policy["platform"] in {"linux/amd64", "linux/arm64"}, "platform")
    require(policy["public_url"] == "https://ai.v8std.ru", "public_url")
    require(policy["nginx_include"] == "/etc/nginx/v8std-release/upstream.conf", "nginx_path")
    require(policy["static_root"] == "/srv/v8std-indexes/v1", "static_path")
    require(policy["ports"] == [18766, 18767], "ports")
    require(isinstance(policy["configs"], dict) and len(policy["configs"]) <= 16
            and (bool(policy["configs"]) or not policy["runtime_enabled"]), "configs")
    for key, config in policy["configs"].items():
        require(matches(HEX, key) and digest(canonical_json(config)) == key, "configuration_digest")
        require(set(config) == {"site_url", "refresh_seconds", "max_snippet_chars", "memory_bytes", "cpus"}, "config_fields")
        require(config["site_url"] == "https://v8std.ru/", "site_url")
        for field, low, high in (("refresh_seconds", 0, 86400), ("max_snippet_chars", 4000, 32000),
                                  ("memory_bytes", 268435456, 8589934592), ("cpus", 1, 64)):
            require(type(config[field]) is int and low <= config[field] <= high, "config_value")
    capacity = policy["capacity"]
    require(set(capacity) == {"disk_bytes", "available_memory_bytes", "file_descriptors", "network_evidence"}, "capacity")
    for name in ("disk_bytes", "available_memory_bytes", "file_descriptors"):
        require(type(capacity[name]) is int and capacity[name] > 0, "capacity")
    if policy["runtime_enabled"]:
        require(matches(HEX, capacity["network_evidence"]), "capacity_evidence")
        require(capacity["available_memory_bytes"] >= max(c["memory_bytes"] for c in policy["configs"].values()) + 128 * 1024 * 1024,
                "capacity_reserve")
    else:
        require(capacity["network_evidence"] is None or matches(HEX, capacity["network_evidence"]), "capacity_evidence")
    return policy


def verify_descriptors(index_raw, child_raw, envelope, platform):
    def decoded(raw, expected):
        # buildx adds a display newline on some versions; only discard it if
        # the exact remaining bytes match the requested content address.
        if "sha256:" + digest(raw) != expected and raw.endswith(b"\n"):
            raw = raw[:-1]
        require("sha256:" + digest(raw) == expected, "descriptor_digest")
        return parse(raw, 2 * 1024 * 1024)
    index = decoded(index_raw, envelope["image_digest"])
    child = decoded(child_raw, envelope["platform_digest"])
    require(index.get("mediaType") in INDEX_TYPES and index.get("schemaVersion") == 2, "index_media_type")
    require(child.get("mediaType") in MANIFEST_TYPES and child.get("schemaVersion") == 2, "child_media_type")
    os_name, architecture = platform.split("/")
    members = [item for item in index.get("manifests", []) if item.get("digest") == envelope["platform_digest"]
               and item.get("mediaType") in MANIFEST_TYPES
               and item.get("platform", {}).get("os") == os_name
               and item.get("platform", {}).get("architecture") == architecture
               and item.get("platform", {}).get("variant", "") in ({"", "v8"} if architecture == "arm64" else {""})]
    require(len(members) == 1, "platform_membership")
    require(members[0].get("size") in {len(child_raw), len(child_raw.rstrip(b"\n"))}, "descriptor_size")
    config = child.get("config", {})
    require(config.get("mediaType") in CONFIG_TYPES and matches(DIGEST, config.get("digest")), "config_descriptor")
    return {envelope["image_digest"]: index["mediaType"], envelope["platform_digest"]: child["mediaType"],
            config["digest"]: config["mediaType"]}


def attestation_command(subject, source_sha):
    return ["gh", "attestation", "verify", subject, "--repo", REPO, "--signer-workflow", WORKFLOW,
            "--source-ref", REF, "--source-digest", source_sha, "--deny-self-hosted-runners",
            "--cert-oidc-issuer", "https://token.actions.githubusercontent.com", "--format", "json"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ReleaseError("http_redirect")


def _http(url, deadline, body, limit):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "Accept-Encoding": "identity"})
    try:
        with opener.open(request, timeout=remaining(deadline, 3)) as response:
            require(response.status == 200, "http_status")
            raw = response.read(limit + 1)
            require(len(raw) <= limit, "http_size")
            remaining(deadline)
            return raw
    except (OSError, urllib.error.URLError):
        raise ReleaseError("http_failed") from None


def _http_worker(channel, url, deadline, body, limit):
    try:
        channel.send_bytes(b"1" + _http(url, deadline, body, limit))
    except Exception:
        channel.send_bytes(b"0")
    finally:
        channel.close()


def http(url, deadline, *, body=None, limit=1024 * 1024):
    # DNS and drip-fed bodies cannot spend rollback's reserved time. This process
    # has no host effects and is killed/reaped at the caller's actual deadline.
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_http_worker, args=(child, url, deadline, body, limit), daemon=True)
    process.start()
    child.close()
    try:
        require(parent.poll(remaining(deadline)), "deadline")
        raw = parent.recv_bytes(limit + 1)
        remaining(deadline)
        require(raw[:1] == b"1", "http_failed")
        return raw[1:]
    except (EOFError, OSError):
        raise ReleaseError("http_failed") from None
    finally:
        parent.close()
        if process.is_alive():
            process.kill()
        process.join()
        process.close()


def _rpc_reply(url, method, params, deadline, number, *, limit=1024 * 1024):
    raw = http(url + "/mcp", deadline, body=canonical_json({"jsonrpc": "2.0", "id": number,
                                               "method": method, "params": params}), limit=limit)
    if raw.startswith(b"event:") or raw.startswith(b"data:"):
        messages = [line[6:] for line in raw.splitlines() if line.startswith(b"data: ")]
        require(len(messages) == 1, "rpc_stream")
        raw = messages[0]
    reply = parse(raw, limit)
    require(reply.get("jsonrpc") == "2.0" and type(reply.get("id")) is type(number)
            and reply["id"] == number, "rpc")
    return reply


def rpc(url, method, params, deadline, number, *, limit=1024 * 1024):
    reply = _rpc_reply(url, method, params, deadline, number, limit=limit)
    require("error" not in reply and isinstance(reply.get("result"), dict), "rpc")
    result = reply["result"]
    require(not result.get("isError"), "rpc_tool")
    return result


def smoke(url, record, deadline):
    health = parse(http(url + "/healthz", deadline))
    require(health.get("ok") is True and health.get("runtime_sha") == record["runtime_source_sha"]
        and health.get("corpus_id") == record["corpus_id"]
        and health.get("archive_sha256") == record["archive_sha256"]
        and health.get("hold_token") == record["hold_token"], "health_identity")
    initialized = rpc(url, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                      "clientInfo": {"name": "v8std-release", "version": "1"}}, deadline, 1)
    require(initialized.get("serverInfo", {}).get("name") == "v8std", "server_identity")
    capabilities = initialized.get("capabilities")
    require(isinstance(capabilities, dict) and "resources" not in capabilities, "resource_capability")
    listed = rpc(url, "tools/list", {}, deadline, 2)
    expected = {"v8std_search", "v8std_get_page", "v8std_get_related", "v8std_explain_snippet", "v8std_explain_diagnostics"}
    require({item["name"] for item in listed.get("tools", [])} == expected, "tool_surface")
    result = rpc(url, "tools/call", {"name": "v8std_search", "arguments": {"query": "std437", "limit": 1}}, deadline, 3)
    # Successful JSON-RPC alone cannot establish a useful search/page response.
    def structured(value):
        if "structuredContent" in value:
            return value["structuredContent"]
        texts = [item["text"] for item in value.get("content", []) if item.get("type") == "text"]
        require(len(texts) == 1, "tool_content")
        return parse(texts[0].encode(), 1024 * 1024)
    search = structured(result)
    require(bool(search.get("results")), "search_empty")
    page_id = search["results"][0]["id"]
    page = structured(rpc(url, "tools/call", {"name": "v8std_get_page", "arguments":
                      {"id_or_alias_or_url": page_id}}, deadline, 4))
    require(page.get("found") is True and page.get("page", {}).get("id") == page_id, "page_smoke")
    structured(rpc(url, "tools/call", {"name": "v8std_explain_snippet", "arguments":
                      {"snippet": "Запрос = Новый Запрос;", "limit": 1}}, deadline, 5))
    structured(rpc(url, "tools/call", {"name": "v8std_get_related", "arguments":
                      {"id_or_alias_or_url": page_id, "limit": 1}}, deadline, 6))
    structured(rpc(url, "tools/call", {"name": "v8std_explain_diagnostics", "arguments":
                      {"codes": ["missing"]}}, deadline, 7))
    denied = _rpc_reply(url, "resources/read", {"uri": "v8std://llms-full.txt"}, deadline, 8)
    # Only a compact error is allowed: no result or additional payload fields.
    # The code carries the refusal semantics; message wording is not a contract.
    error = denied.get("error")
    require(set(denied) == {"jsonrpc", "id", "error"} and isinstance(error, dict)
            and set(error) == {"code", "message"} and error["code"] == -32601, "resource_disabled")
    message = error["message"]
    require(isinstance(message, str) and bool(message.strip()) and len(message) <= 256, "resource_disabled")
    # Bracket tool calls with the held identity so a health-only mismatch cannot
    # pass while the actual endpoint refreshes or nginx reload serves old workers.
    after = parse(http(url + "/healthz", deadline))
    require(all(after.get(k) == health.get(k) for k in (
        "runtime_sha", "corpus_id", "archive_sha256", "hold_token")), "smoke_generation_changed")
    return health


class HostAdapter:
    def __init__(self, root, policy):
        self.root, self.policy = Path(root), policy

    def config(self, envelope):
        config = self.policy["configs"].get(envelope["configuration_digest"])
        require(config is not None and digest(canonical_json(config)) == envelope["configuration_digest"], "untrusted_configuration")
        return config

    def verify(self, envelope, deadline):
        self.config(envelope)
        run(attestation_command("oci://" + IMAGE + "@" + envelope["image_digest"],
                                envelope["runtime_source_sha"]), deadline)
        # Certificate source-ref binds main at build time. Current eligibility of
        # both runtime and triggering commits additionally requires main ancestry.
        for sha in {envelope["runtime_source_sha"], envelope["trigger_sha"]}:
            result = parse(run(["gh", "api", f"repos/{REPO}/compare/{sha}...main"], deadline), 2 * 1024 * 1024)
            require(result.get("status") in {"ahead", "identical"}
                    and result.get("merge_base_commit", {}).get("sha") == sha, "main_ancestry")
        index = run(["docker", "buildx", "imagetools", "inspect", "--raw", IMAGE + "@" + envelope["image_digest"]], deadline)
        child = run(["docker", "buildx", "imagetools", "inspect", "--raw", IMAGE + "@" + envelope["platform_digest"]], deadline)
        return verify_descriptors(index, child, envelope, self.policy["platform"])

    def capacity(self, deadline, *, reclaim_bytes=0):
        limits = self.policy["capacity"]
        require(shutil.disk_usage(self.root).free >= limits["disk_bytes"], "disk_capacity")
        values = dict(re.findall(r"^(\w+):\s+(\d+)", read_file(Path("/proc/meminfo")).decode(), re.M))
        require(int(values.get("MemAvailable", 0)) * 1024 + reclaim_bytes >= limits["available_memory_bytes"], "memory_capacity")
        import resource
        require(resource.getrlimit(resource.RLIMIT_NOFILE)[0] >= limits["file_descriptors"], "fd_capacity")
        evidence = read_file(self.root / "capacity" / (limits["network_evidence"] + ".json"))
        require(digest(evidence) == limits["network_evidence"], "network_capacity")
        remaining(deadline)

    def pull(self, record, deadline):
        run(["docker", "pull", "--platform", self.policy["platform"], IMAGE + "@" + record["platform_digest"]], deadline)

    def inspect(self, record, deadline):
        try:
            result = json.loads(run(["docker", "inspect", "--type", "container", record["name"]], deadline))
        except ReleaseError as error:
            if error.code != "command_failed":
                raise
            # Only confirmed absence can authorize creation, not inspect failure.
            names = run(["docker", "ps", "-a", "--format", "{{.Names}}"], deadline).decode().splitlines()
            require(record["name"] not in names, "inspect_failed")
            return None
        info = result[0]
        labels = info["Config"].get("Labels") or {}
        require(labels.get("pro.v8std.release") == record["release_id"]
                and labels.get("pro.v8std.envelope") == record["envelope_hash"], "ownership")
        require(info["Config"]["Image"] == IMAGE + "@" + record["platform_digest"], "container_image")
        require(info["Image"] in record["descriptors"], "image_descriptor_identity")
        require(labels.get("org.opencontainers.image.revision") == record["runtime_source_sha"], "runtime_revision")
        return info

    def start(self, record, deadline):
        info = self.inspect(record, deadline)
        if info:
            check_usage_binding(info)
        prepare_usage_log(create=info is None)
        if info:
            if not info["State"]["Running"]:
                run(["docker", "start", record["name"]], deadline)
            return
        config = self.config(record)
        directory = self.root / "slots" / record["release_id"]
        cache = directory / "cache"
        ensure_directory(cache)
        os.chown(cache, 10001, 10001)
        # Dedicated cache/control paths are derived solely from the validated ID.
        run(["docker", "run", "-d", "--name", record["name"], "--pull", "never",
             "--label", "pro.v8std.release=" + record["release_id"],
             "--label", "pro.v8std.envelope=" + record["envelope_hash"],
             "--platform", self.policy["platform"], "--read-only", "--cap-drop", "ALL",
             "--security-opt", "no-new-privileges", "--init", "--user", "10001:10001",
             "--memory", str(config["memory_bytes"]), "--memory-swap", str(config["memory_bytes"]),
             "--cpus", str(config["cpus"]), "--pids-limit", "128", "--stop-timeout", "30",
             "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m,mode=1777",
             "--mount", f"type=bind,source={cache},target=/var/lib/v8std-mcp",
             "--mount", f"type=bind,source={directory / 'control'},target=/run/v8std-release,readonly",
             "--mount", f"type=bind,source={USAGE_LOG},target={USAGE_LOG_TARGET}",
             "-p", f"127.0.0.1:{record['port']}:8000", IMAGE + "@" + record["platform_digest"],
             "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000",
             "--site-url", config["site_url"], "--refresh-seconds", str(config["refresh_seconds"]),
             "--max-snippet-chars", str(config["max_snippet_chars"]),
             "--usage-log", USAGE_LOG_TARGET], deadline)
        self.inspect(record, deadline)

    def control(self, record, mode, token, manifest=None):
        control_directory = self.root / "slots" / record["release_id"] / "control"
        ensure_directory(control_directory, 0o755)
        # mkdir's mode is filtered by the recovery service's UMask=0077.
        # Publish final traversal/read permissions before making a command visible.
        os.chmod(control_directory, 0o755)
        sync_dir(control_directory)
        write_json(control_directory / "control.json", {"schema_version": 1, "token": token,
                                               "mode": mode, "manifest": manifest}, mode=0o644)

    def hold(self, record, token, deadline, manifest=None):
        self.control(record, "hold", token, manifest)
        if manifest is not None:
            self.start(record, deadline)
        while True:
            try:
                state = parse(http(self.url(record) + "/healthz", deadline))
                if state.get("ok") and state.get("hold_token") == token:
                    require(state.get("runtime_sha") == record["runtime_source_sha"], "runtime_identity")
                    require(matches(HEX, state.get("archive_sha256")) and matches(HEX, state.get("corpus_id")), "corpus_identity")
                    if manifest is not None:
                        require(state["archive_sha256"] == manifest["archive"]["sha256"]
                                and state["corpus_id"] == manifest["corpus_id"], "selection_identity")
                    return {**record, "corpus_id": state["corpus_id"], "archive_sha256": state["archive_sha256"],
                            "corpus_source_sha": state["corpus_source_sha"], "hold_token": token}
            except ReleaseError as error:
                if error.code not in {"http_failed", "http_status"}:
                    raise
            time.sleep(min(.1, remaining(deadline)))

    @staticmethod
    def url(record):
        return f"http://127.0.0.1:{record['port']}"

    def check(self, record, deadline, *, public=False):
        self.inspect(record, deadline)
        state = smoke(self.policy["public_url"] if public else self.url(record), record, deadline)
        if public:
            raw = http(self.policy["public_url"] + "/indexes/v1/" + record["archive_sha256"] + "/snapshot.tar.gz",
                       deadline, limit=MAX_ARCHIVE_BYTES)
            require(digest(raw) == record["archive_sha256"], "static_hash")
        return state

    def switch(self, record, deadline):
        path = Path(self.policy["nginx_include"])
        previous = read_file(path)
        atomic(path, (f"server 127.0.0.1:{record['port']} max_conns=8;\n").encode())
        try:
            run(["nginx", "-t"], deadline)
        except BaseException:
            atomic(path, previous)
            raise
        run(["nginx", "-s", "reload"], deadline)

    def stop(self, record, deadline):
        if self.inspect(record, deadline) is not None:
            # No automatic restart policy; deterministic named objects survive
            # controller death and are reconciled, not replaced by unrelated IDs.
            run(["docker", "stop", "--time", str(max(0, min(DRAIN, int(remaining(deadline)) - 5))), record["name"]], deadline)
            info = self.inspect(record, deadline)
            require(not info["State"]["Running"], "stop_failed")

    def resume(self, record, deadline):
        token = digest((record["release_id"] + ":resume").encode())[:32]
        self.control(record, "resume", token)
        while True:
            health = parse(http(self.url(record) + "/healthz", deadline))
            require(health.get("runtime_sha") == record["runtime_source_sha"] and health.get("ok"), "resume_identity")
            if health.get("hold_token") is None and health.get("release_control_token") == token:
                return
            time.sleep(min(.1, remaining(deadline)))

    def manifest(self, record):
        raw = read_file(self.root / "manifests" / (record["archive_sha256"] + ".json"))
        manifest = validate_manifest(raw)
        require(manifest["corpus_id"] == record["corpus_id"]
                and manifest["archive"]["sha256"] == record["archive_sha256"], "manifest_identity")
        return manifest

    def bootstrap_window(self, envelope):
        require(BOOTSTRAP_WINDOW.exists(), "bootstrap_window_required")
        trusted_path(BOOTSTRAP_WINDOW)
        return validate_bootstrap_window(parse(read_file(BOOTSTRAP_WINDOW)), envelope)

    def bootstrap_backup(self, window, deadline, *, current=False):
        saved = backup_inventory(self.root, window, deadline)
        require(file_hash(LEGACY_PYTHON, deadline) == saved["interpreter_sha256"], "legacy_interpreter_changed")
        if current:
            self.legacy_files(saved, deadline, restore=False)
            require(file_hash(LEGACY_CONFIG, deadline) == saved["unit"]["sha256"]
                    and file_hash(Path(self.policy["nginx_include"]), deadline) == saved["upstream"]["sha256"], "legacy_config_changed")
            # The only installed drop-in is our separately reviewed boot fence.
            unit = dict(line.split("=", 1) for line in run(["systemctl", "show", LEGACY_UNIT,
                "--property=MainPID", "--property=ActiveState", "--property=DropInPaths",
                "--property=EnvironmentFiles"], deadline).decode().splitlines())
            require(unit.get("ActiveState") == "active" and unit.get("MainPID", "0").isdigit()
                    and int(unit["MainPID"]) > 0 and not unit.get("EnvironmentFiles")
                    and unit.get("DropInPaths") == "/etc/systemd/system/v8std-mcp.service.d/10-release-guard.conf", "legacy_unit_changed")
        return saved

    def bootstrap_capacity(self, window, envelope, deadline, *, after_stop=False):
        limits = window["capacity"]
        require(limits["available_memory_bytes"] >= self.config(envelope)["memory_bytes"] + 128 * 1024 * 1024,
                "capacity_reserve")
        reclaim = 0
        if window["mode"] == "stop-start" and not after_stop:
            value = run(["systemctl", "show", LEGACY_UNIT, "--property=MemoryCurrent", "--value"], deadline).strip()
            require(value.isdigit(), "legacy_memory")
            reclaim = int(value)
        HostAdapter(self.root, self.policy | {"capacity": limits}).capacity(deadline, reclaim_bytes=reclaim)

    def bootstrap_prepared(self, candidate, deadline):
        # Artifacts must already exist. No pull/build during the migration window.
        info = json.loads(run(["docker", "image", "inspect", IMAGE + "@" + candidate["platform_digest"]], deadline))[0]
        require(info["Id"] in candidate["descriptors"] and info["Os"] + "/" + info["Architecture"] == self.policy["platform"]
                and info["Config"].get("Labels", {}).get("org.opencontainers.image.revision") == candidate["runtime_source_sha"],
                "prepared_image")
        manifest = self.manifest(candidate)
        verify_archive(read_file(Path(self.policy["static_root"]) / candidate["archive_sha256"] / "snapshot.tar.gz",
                                 MAX_ARCHIVE_BYTES), manifest)

    def arm_bootstrap_guard(self, deadline):
        for path, expected in (
            ("/etc/systemd/system/v8std-mcp.service.d/10-release-guard.conf", LEGACY_GUARD),
            ("/etc/systemd/system/v8std-bootstrap-recover.service", BOOTSTRAP_SERVICE),
            ("/etc/systemd/system/v8std-bootstrap-recover.timer", BOOTSTRAP_TIMER)):
            trusted_path(Path(path))
            require(read_file(Path(path)) == expected.encode(), "bootstrap_guard_config")
        require(run(["systemctl", "is-enabled", "v8std-bootstrap-recover.timer"], deadline).strip() == b"enabled", "bootstrap_guard")
        require(run(["systemctl", "is-active", "v8std-bootstrap-recover.timer"], deadline).strip() == b"active", "bootstrap_guard")
        for unit in (LEGACY_UNIT, "v8std-bootstrap-recover.service", "v8std-bootstrap-recover.timer"):
            properties = dict(line.split("=", 1) for line in run(["systemctl", "show", unit,
                "--property=NeedDaemonReload", "--property=LoadState", "--property=DropInPaths"], deadline).decode().splitlines())
            require(properties.get("NeedDaemonReload") == "no" and properties.get("LoadState") == "loaded"
                    and properties.get("DropInPaths") == (
                        "/etc/systemd/system/v8std-mcp.service.d/10-release-guard.conf" if unit == LEGACY_UNIT else ""),
                    "bootstrap_guard_loaded")

    def legacy_stop(self, deadline):
        run(["systemctl", "stop", LEGACY_UNIT], deadline)
        require(run(["systemctl", "show", LEGACY_UNIT, "--property=MainPID", "--value"], deadline).strip() == b"0", "legacy_stop")

    def legacy_files(self, saved, deadline, *, restore):
        for component, target_root in (("app", LEGACY_APP), ("cache", LEGACY_DATA)):
            require(not target_root.is_symlink(), "legacy_path")
            if component == "app" and target_root.exists():
                actual = set()
                for directory, dirs, files in os.walk(target_root, followlinks=False):
                    if RESTORE_STAGE in dirs:
                        info = (Path(directory) / RESTORE_STAGE).lstat()
                        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                                and info.st_mode & 0o777 == 0o700, "restore_staging")
                        dirs.remove(RESTORE_STAGE)
                    dirs[:] = [d for d in dirs if d != "__pycache__"]
                    actual.update(str((Path(directory) / name).relative_to(target_root)) for name in
                                  files + [d for d in dirs if (Path(directory) / d).is_symlink()])
                require(actual <= set(saved["app"]), "legacy_unlisted")
            for relative, metadata in sorted(saved["directories"][component].items(), key=lambda item: len(item[0])):
                directory = target_root / relative
                if restore:
                    ensure_directory(directory)
                    os.chown(directory, metadata["uid"], metadata["gid"])
                    os.chmod(directory, metadata["mode"])
                    sync_dir(directory)
                else:
                    info = directory.lstat()
                    require(stat.S_ISDIR(info.st_mode) and (info.st_mode & 0o777) == metadata["mode"]
                            and info.st_uid == metadata["uid"] and info.st_gid == metadata["gid"], "legacy_directory_changed")
            for relative, entry in sorted(saved[component].items()):
                target = target_root / relative
                # Reject symlink ancestors before any destination write.
                for parent in target.parents:
                    require(not parent.is_symlink(), "legacy_path")
                    if parent == target_root:
                        break
                if "link" in entry:
                    if restore and not target.exists() and not target.is_symlink():
                        ensure_directory(target.parent)
                        target.symlink_to(entry["link"])
                        sync_dir(target.parent)
                    require(target.is_symlink() and os.readlink(target) == entry["link"], "legacy_link_changed")
                elif restore:
                    restore_file(self.root / "legacy" / component / relative, target, entry, deadline)
                else:
                    if "__pycache__" in target.parts:
                        continue  # Derived bytecode changes on an exact-source restart.
                    require(file_hash(target, deadline) == entry["sha256"], "legacy_files_changed")

    def legacy_restore(self, window, deadline):
        saved = self.bootstrap_backup(window, deadline)
        self.legacy_files(saved, deadline, restore=True)
        restore_file(self.root / "legacy/unit", LEGACY_CONFIG, saved["unit"], deadline)
        restore_file(self.root / "legacy/upstream", Path(self.policy["nginx_include"]), saved["upstream"], deadline)
        run(["systemctl", "daemon-reload"], deadline)
        run(["nginx", "-t"], deadline)
        run(["nginx", "-s", "reload"], deadline)

    def legacy_start(self, deadline):
        run(["systemctl", "start", LEGACY_UNIT], deadline)

    def legacy_identity(self, deadline):
        pid = run(["systemctl", "show", LEGACY_UNIT, "--property=MainPID", "--value"], deadline).strip()
        require(pid.isdigit() and int(pid) > 0, "legacy_process")
        arguments = read_file(Path("/proc") / pid.decode() / "cmdline").split(b"\0")[:-1]
        expected = [str(LEGACY_APP / "venv/bin/python"), str(LEGACY_APP / "scripts/v8std_mcp_server.py"),
            "--index-url", "https://v8std.ru/ai/pages.jsonl", "--vectors-url", "https://v8std.ru/ai/search-vectors.jsonl",
            "--cache-dir", str(LEGACY_DATA), "--host", "127.0.0.1", "--port", "8765", "--mcp-path", "/mcp",
            "--max-snippet-chars", "4000", "--usage-log", str(LEGACY_DATA / "tool-usage.jsonl")]
        require(arguments == [arg.encode() for arg in expected]
                and Path(os.readlink(Path("/proc") / pid.decode() / "exe")) == LEGACY_PYTHON, "legacy_process")

    def legacy_check(self, window, deadline, *, public=False):
        saved = self.bootstrap_backup(window, deadline)
        self.legacy_files(saved, deadline, restore=False)
        url = self.policy["public_url"] if public else "http://127.0.0.1:8765"
        while True:
            try:
                self.legacy_identity(deadline)
                health = parse(http(url + "/healthz", deadline))
                require(health.get("ok") is True and health.get("sha256") == saved["cache"]["pages.jsonl"]["sha256"]
                        and health.get("vectors", {}).get("sha256") == saved["cache"]["search-vectors.jsonl"]["sha256"], "legacy_health_identity")
                rpc(url, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                    "clientInfo": {"name": "v8std-release", "version": "1"}}, deadline, 1)
                result = rpc(url, "tools/call", {"name": "v8std_search", "arguments": {"query": "std437", "limit": 1}}, deadline, 2)
                require(bool(result.get("content") or result.get("structuredContent")), "legacy_search")
                for number, (uri, name) in enumerate((("v8std://llms.txt", "llms.txt"),
                        ("v8std://llms-full.txt", "llms-full.txt"), ("v8std://ai/pages.jsonl", "pages.jsonl")), 3):
                    contents = rpc(url, "resources/read", {"uri": uri}, deadline, number, limit=32 * 1024 * 1024).get("contents", [])
                    require(len(contents) == 1 and isinstance(contents[0].get("text"), str)
                            and digest(contents[0]["text"].encode()) == saved["cache"][name]["sha256"], "legacy_resource")
                after = parse(http(url + "/healthz", deadline))
                require(after.get("sha256") == health["sha256"] and after.get("vectors", {}).get("sha256")
                        == health["vectors"]["sha256"], "legacy_generation_changed")
                return health
            except ReleaseError as error:
                if error.code not in {"http_failed", "legacy_process"}:
                    raise
                time.sleep(min(.1, remaining(deadline)))


class Controller:
    def __init__(self, root, adapter):
        self.root, self.adapter = Path(root), adapter

    def journals(self):
        directory = self.root / "releases"
        return [parse(read_file(path), 65536) for path in directory.glob("*.json")] if directory.exists() else []

    def status(self):
        records = self.journals()
        if not records:
            return {"state": "EMPTY"}
        journal = max(records, key=lambda item: item["envelope"]["sequence"])
        return self.result(journal)

    @staticmethod
    def result(journal):
        if journal["state"] == "REJECTED":
            return dict(journal)  # Durable queued rejection is already a public outcome.
        return {**journal["envelope"], "state": journal["state"], "intent": journal["intent"],
                "error_code": journal.get("error_code"), "cleanup_complete": bool(
                    journal.get("cleanup_complete", False) and not journal.get("active_recovery"))}

    def save(self, journal, state=None, intent=None):
        if state:
            journal["state"] = state
        if intent:
            journal["intent"] = intent
        journal["updated_at"] = time.time()
        write_json(self.root / "releases" / (journal["envelope"]["release_id"] + ".json"), journal)

    def existing(self, envelope):
        rejected_path = self.root / "rejected" / (envelope["release_id"] + ".json")
        if rejected_path.exists():
            rejected = read_record(rejected_path)
            require({key: rejected.get(key) for key in envelope} == envelope, "mutated_duplicate")
            return rejected
        records = self.journals()
        for item in records:
            if item["envelope"]["release_id"] == envelope["release_id"]:
                require(item["envelope"] == envelope, "mutated_duplicate")
                return item
        require(not records or envelope["sequence"] > max(x["envelope"]["sequence"] for x in records), "stale_sequence")
        require(not any(x.get("active_recovery") or x["state"] not in TERMINAL or x["state"] == "RECOVERY_REQUIRED"
                        or x["state"] == "COMMITTED" and not x.get("cleanup_complete") for x in records), "recovery_pending")
        return None

    def deploy(self, raw):
        envelope = validate_envelope(raw, expired=True)
        with locked(self.root):
            existing = self.existing(envelope)
            if existing:
                return self.result(existing)
            require(self.adapter.policy.get("runtime_enabled") is True, "runtime_not_activated")
            self.adapter.config(envelope)
            validate_envelope(raw)
            require(envelope["deadline"] - time.time() > RECOVERY_RESERVE, "insufficient_transaction_budget")
            require((self.root / "active.json").is_file(), "predecessor_required")
            previous = parse(read_file(self.root / "active.json"), 65536)
            self.adapter.config(previous)
            deadline = time.monotonic() + min(TRANSACTION, envelope["deadline"] - time.time())
            work = deadline - RECOVERY_RESERVE
            journal = {"envelope": envelope, "state": "RECEIVED", "intent": "verify", "predecessor": previous,
                       "candidate": None, "cleanup_complete": False}
            self.save(journal)
            try:
                descriptors = self.adapter.verify(envelope, work)
                self.adapter.capacity(work)
                manifest = self.adapter.manifest(envelope)
                self.save(journal, "VERIFIED", "hold_predecessor")
                token = digest(canonical_json(envelope))[:32]
                previous = self.adapter.hold(previous, token, min(work, time.monotonic() + READINESS))
                journal["predecessor"] = previous
                self.adapter.manifest(previous)  # Published record of observed, not disk-pointer, corpus.
                self.save(journal, intent="pin_predecessor")
                self.pins(journal)
                candidate = {**envelope, "name": "v8std-release-" + envelope["release_id"],
                    "envelope_hash": digest(canonical_json(envelope)), "descriptors": descriptors,
                    "port": next(p for p in self.adapter.policy["ports"] if p != previous["port"]),
                    "hold_token": token}
                journal["candidate"] = candidate
                self.save(journal, intent="pull_candidate")
                self.adapter.pull(candidate, work)
                self.save(journal, intent="start_candidate")
                candidate = self.adapter.hold(candidate, token, min(work, time.monotonic() + READINESS), manifest)
                journal["candidate"] = candidate
                self.save(journal, "PREPARED", "candidate_smoke")
                self.adapter.check(candidate, min(work, time.monotonic() + SMOKE))
                journal["switch_attempted"] = True
                self.save(journal, "READY", "switch")
                self.adapter.switch(candidate, work)
                self.save(journal, "SWITCHED", "public_smoke")
                self.adapter.check(candidate, min(work, time.monotonic() + SMOKE), public=True)
                self.save(journal, "COMMITTED", "accept_pointer")
                self.cleanup(journal, deadline)
            except Exception as error:
                journal["error_code"] = error.code if isinstance(error, ReleaseError) else "host_failure"
                self.save(journal)
                if journal["state"] == "RECEIVED":
                    # Rejected authority cannot trigger runtime mutation.
                    journal["cleanup_complete"] = True
                    self.save(journal, "FAILED", "complete")
                elif journal["state"] == "COMMITTED":
                    # Accepted release is never undone by post-commit cleanup failure.
                    self.save(journal, intent="cleanup_pending")
                else:
                    self.rollback(journal, deadline)
            return self.status()


    def pins(self, journal):
        # Pins retain public objects independent of the mutable manifest pointer.
        retained = {journal["envelope"]["archive_sha256"], journal["predecessor"]["archive_sha256"]}
        previous = self.root / "predecessor.json"
        if previous.exists():
            retained.add(parse(read_file(previous), 65536)["archive_sha256"])
        write_json(self.root / "pins.json", {"archives": sorted(retained)})

    def cleanup(self, journal, deadline):
        candidate = journal["candidate"]
        self.save(journal, intent="ensure_accepted_candidate")
        candidate = self.adapter.hold(candidate, candidate["hold_token"],
            min(deadline - STOP - SMOKE - 5, time.monotonic() + READINESS), self.adapter.manifest(candidate))
        journal["candidate"] = candidate
        self.adapter.switch(candidate, deadline - STOP - SMOKE)
        self.adapter.check(candidate, min(deadline - STOP, time.monotonic() + SMOKE), public=True)
        self.save(journal, intent="accept_pointer")
        write_json(self.root / "active.json", candidate)
        write_json(self.root / "predecessor.json", journal["predecessor"])
        self.pins(journal)
        self.save(journal, intent="drain_predecessor")
        self.adapter.stop(journal["predecessor"], min(deadline, time.monotonic() + STOP))
        self.save(journal, intent="resume_candidate")
        self.adapter.resume(candidate, min(deadline, time.monotonic() + SMOKE))
        journal["cleanup_complete"] = True
        journal.pop("error_code", None)
        self.save(journal, intent="complete")

    def rollback(self, journal, deadline):
        switched = journal.get("switch_attempted", False)
        try:
            previous = journal["predecessor"]
            self.save(journal, intent="restore_predecessor")
            # A crash during capture might leave no acknowledged identity. Select
            # the persisted previously accepted generation, never a newer cache pointer.
            token = previous.get("hold_token") or digest((previous["release_id"] + ":recover").encode())[:32]
            previous = self.adapter.hold(previous, token, min(deadline - STOP - SMOKE - 5,
                time.monotonic() + READINESS), self.adapter.manifest(previous))
            journal["predecessor"] = previous
            self.save(journal, intent="restore_upstream")
            self.adapter.switch(previous, deadline - STOP - SMOKE)
            self.adapter.check(previous, min(deadline - STOP, time.monotonic() + SMOKE), public=True)
            write_json(self.root / "active.json", previous)
            if journal["candidate"]:
                self.save(journal, intent="stop_candidate")
                self.adapter.stop(journal["candidate"], min(deadline, time.monotonic() + STOP))
            self.adapter.resume(previous, deadline)
            journal["cleanup_complete"] = True
            self.save(journal, "ROLLED_BACK" if switched else "FAILED", "complete")
        except Exception:
            journal["error_code"] = "rollback_failed"
            self.save(journal, "RECOVERY_REQUIRED", "operator_recovery")

    def recover(self):
        with locked(self.root):
            records = self.journals()
            if not records:
                return self.status()
            journal = max(records, key=lambda item: item["envelope"]["sequence"])
            if journal.get("kind") == "bootstrap":
                return BootstrapController(self.root, self.adapter).reconcile(journal)
            if journal.get("cleanup_complete"):
                active_path = self.root / "active.json"
                if active_path.exists():
                    active = parse(read_file(active_path), 65536)
                    deadline = time.monotonic() + TRANSACTION
                    try:
                        info = self.adapter.inspect(active, deadline)
                        if journal.get("active_recovery") or info is None or not info["State"]["Running"]:
                            # This is a new recovery transaction, not the old
                            # release's completed drain. Persist before start;
                            # Running alone never discharges switch/smoke/resume.
                            active = journal.get("active_recovery", {}).get("record", active)
                            journal["active_recovery"] = {"record": active}
                            self.save(journal, intent="recover_active_hold")
                            token = digest((active["release_id"] + ":restart").encode())[:32]
                            active = self.adapter.hold(active, token,
                                                       min(deadline - STOP - SMOKE, time.monotonic() + READINESS),
                                                       self.adapter.manifest(active))
                            journal["active_recovery"]["record"] = active
                            self.save(journal, intent="recover_active_switch")
                            self.adapter.switch(active, deadline - 2 * SMOKE)
                            self.save(journal, intent="recover_active_smoke")
                            self.adapter.check(active, min(deadline - SMOKE, time.monotonic() + SMOKE), public=True)
                            self.save(journal, intent="recover_active_pointer")
                            write_json(active_path, active)
                            self.save(journal, intent="recover_active_resume")
                            self.adapter.resume(active, min(deadline, time.monotonic() + SMOKE))
                            journal.pop("active_recovery")
                            journal["intent"] = "complete"
                        journal.pop("error_code", None)
                        self.save(journal)
                    except Exception:
                        journal["error_code"] = "active_recovery_failed"
                        self.save(journal)
                return self.status()
            if journal["state"] == "RECEIVED":
                journal["cleanup_complete"] = True
                journal["error_code"] = "interrupted_verification"
                self.save(journal, "FAILED", "complete")
                return self.status()
            # A separate detached recovery job has its own bounded 300s budget.
            # This never extends the candidate's original acceptance deadline.
            deadline = time.monotonic() + TRANSACTION
            if journal["state"] == "COMMITTED":
                try:
                    self.cleanup(journal, deadline)
                except Exception:
                    journal["error_code"] = "cleanup_failed"
                    self.save(journal, intent="cleanup_pending")
            else:
                self.rollback(journal, deadline)
            return self.status()


class BootstrapController(Controller):
    """Initial acceptance only. It never activates policy or invents a predecessor."""

    def submit(self, raw):
        envelope = validate_envelope(raw, expired=True)
        with locked(self.root):
            existing = self.existing(envelope)
            if existing:
                return self.result(existing)
            require(not (self.root / "active.json").exists(), "bootstrap_already_accepted")
            require(not any(x["state"] == "COMMITTED" for x in self.journals()), "bootstrap_already_accepted")
            validate_envelope(raw)
            require(envelope["deadline"] - time.time() > RECOVERY_RESERVE, "insufficient_transaction_budget")
            self.adapter.config(envelope)
            window = self.adapter.bootstrap_window(envelope)
            validate_bootstrap_window(window, envelope)
            journal = {"kind": "bootstrap", "envelope": envelope, "window": window, "state": "RECEIVED",
                "intent": "queued", "candidate": None, "cleanup_complete": False, "legacy_start_allowed": True}
            self.save(journal)
        schedule("bootstrap")
        return self.result(journal)

    def execute(self):
        with locked(self.root):
            records = self.journals()
            require(bool(records), "bootstrap_missing")
            journal = max(records, key=lambda item: item["envelope"]["sequence"])
            require(journal.get("kind") == "bootstrap", "bootstrap_missing")
            if journal["state"] != "RECEIVED":
                return self.result(journal)
            envelope, window = journal["envelope"], journal["window"]
            deadline = time.monotonic() + min(TRANSACTION, envelope["deadline"] - time.time())
            work = deadline - RECOVERY_RESERVE
            try:
                validate_bootstrap_window(window, envelope)
                validate_envelope(canonical_json(envelope))
                remaining(work)
                require(not (self.root / "active.json").exists(), "bootstrap_already_accepted")
                descriptors = self.adapter.verify(envelope, work)
                self.adapter.bootstrap_backup(window, work, current=True)
                self.adapter.bootstrap_capacity(window, envelope, work)
                token = digest(canonical_json(envelope))[:32]
                candidate = {**envelope, "name": "v8std-release-" + envelope["release_id"],
                    "envelope_hash": digest(canonical_json(envelope)), "descriptors": descriptors,
                    "port": self.adapter.policy["ports"][0], "hold_token": token}
                self.adapter.bootstrap_prepared(candidate, work)
                self.adapter.legacy_check(window, min(work, time.monotonic() + SMOKE))
                self.adapter.arm_bootstrap_guard(work)
                validate_bootstrap_window(window, envelope)
                journal.update(candidate=candidate, legacy_start_allowed=False)
                self.save(journal, "VERIFIED", "guard_armed")
                write_json(self.root / "pins.json", {"archives": [envelope["archive_sha256"]]})
                if window["mode"] == "stop-start":
                    self.save(journal, intent="stop_legacy")
                    self.adapter.legacy_stop(min(work, time.monotonic() + STOP))
                    self.adapter.bootstrap_capacity(window, envelope, work, after_stop=True)
                self.save(journal, intent="start_candidate")
                candidate = self.adapter.hold(candidate, token, min(work, time.monotonic() + READINESS),
                                               self.adapter.manifest(candidate))
                journal["candidate"] = candidate
                self.save(journal, "PREPARED", "candidate_smoke")
                self.adapter.check(candidate, min(work, time.monotonic() + SMOKE))
                self.save(journal, "READY", "switch")
                self.adapter.switch(candidate, work)
                self.save(journal, "SWITCHED", "public_smoke")
                self.adapter.check(candidate, min(work, time.monotonic() + SMOKE), public=True)
                remaining(work)
                # Durable COMMITTED is the acceptance point, never active.json.
                self.save(journal, "COMMITTED", "accept_pointer")
                self.finish(journal, deadline)
            except Exception as error:
                # A failed fsync/rename has an uncertain result: re-read the
                # durable journal instead of trusting a mutated in-memory state.
                journal = read_record(self.root / "releases" / (envelope["release_id"] + ".json"))
                journal["error_code"] = getattr(error, "code", "host_failure")
                if journal["state"] == "COMMITTED":
                    self.save(journal, intent="cleanup_pending")
                elif journal["state"] == "RECEIVED":
                    journal["cleanup_complete"] = True
                    self.save(journal, "FAILED", "complete")
                else:
                    self.rollback(journal, deadline)
            return self.result(journal)

    def finish(self, journal, deadline):
        # Also used after accepted crash/reboot. Fence before any candidate start.
        journal["cleanup_complete"] = False
        journal["legacy_start_allowed"] = False
        self.save(journal, intent="ensure_accepted_candidate")
        self.adapter.legacy_stop(min(deadline - READINESS - 2 * SMOKE, time.monotonic() + STOP))
        candidate = journal["candidate"]
        candidate = self.adapter.hold(candidate, candidate["hold_token"],
            min(deadline - 2 * SMOKE, time.monotonic() + READINESS), self.adapter.manifest(candidate))
        journal["candidate"] = candidate
        self.save(journal, intent="accepted_switch")
        self.adapter.switch(candidate, deadline - 2 * SMOKE)
        self.save(journal, intent="accepted_smoke")
        self.adapter.check(candidate, min(deadline - SMOKE, time.monotonic() + SMOKE), public=True)
        self.save(journal, intent="accept_pointer")
        write_json(self.root / "active.json", candidate)
        write_json(self.root / "pins.json", {"archives": [candidate["archive_sha256"]]})
        self.save(journal, intent="resume_candidate")
        self.adapter.resume(candidate, min(deadline, time.monotonic() + SMOKE))
        journal["cleanup_complete"] = True
        journal.pop("error_code", None)
        self.save(journal, intent="complete")

    def rollback(self, journal, deadline):
        try:
            journal["legacy_start_allowed"] = False
            self.save(journal, intent="stop_candidate")
            if journal["candidate"]:
                self.adapter.stop(journal["candidate"], min(deadline - READINESS - SMOKE - 5, time.monotonic() + STOP))
            # Stop legacy too if overlap was chosen; restore coherent bytes only
            # while the original process is stopped, then restart its exact unit.
            self.save(journal, intent="restore_legacy")
            self.adapter.legacy_stop(min(deadline - READINESS - SMOKE, time.monotonic() + STOP))
            self.adapter.legacy_restore(journal["window"], deadline - READINESS - SMOKE)
            journal["legacy_start_allowed"] = True
            self.save(journal, intent="start_legacy")
            self.adapter.legacy_start(min(deadline - SMOKE, time.monotonic() + READINESS))
            self.save(journal, intent="legacy_smoke")
            self.adapter.legacy_check(journal["window"], min(deadline, time.monotonic() + SMOKE), public=True)
            journal["cleanup_complete"] = True
            self.save(journal, "ROLLED_BACK", "complete")
        except Exception:
            journal["cleanup_complete"] = False
            journal["error_code"] = "legacy_recovery_failed"
            self.save(journal, "RECOVERY_REQUIRED", "restore_legacy")

    def reconcile(self, journal):
        # Caller holds the same global release/publication lock. No window gate:
        # restoring owed work remains required after expiry or policy disablement.
        if journal["state"] == "RECEIVED":
            journal["cleanup_complete"] = True
            self.save(journal, "FAILED", "interrupted_preparation")
        elif journal["state"] == "COMMITTED":
            candidate = journal["candidate"]
            deadline = time.monotonic() + TRANSACTION
            info = self.adapter.inspect(candidate, deadline)
            if not journal.get("cleanup_complete") or info is None or not info["State"]["Running"]:
                try:
                    self.finish(journal, deadline)
                except Exception:
                    journal.update(cleanup_complete=False, error_code="bootstrap_cleanup_failed")
                    self.save(journal, intent="cleanup_pending")
        elif not journal.get("cleanup_complete"):
            self.rollback(journal, time.monotonic() + TRANSACTION)
        return self.result(journal)


def validate_upload(header):
    require(set(header) == {"schema_version", "publication_id", "sequence", "trigger_sha",
            "manifest", "deadline", "action"}, "upload_fields")
    require(type(header["schema_version"]) is int and header["schema_version"] == 1, "schema")
    require(matches(ID, header["publication_id"]) and matches(SHA, header["trigger_sha"]), "upload_identity")
    require(type(header["sequence"]) is int and 0 < header["sequence"] <= 2**53 - 1, "sequence")
    require(type(header["deadline"]) is int and header["action"] in {"publish", "reference"}, "upload_action")
    manifest = validate_manifest(canonical_json(header["manifest"]))
    expected = "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["sha256"] + "/snapshot.tar.gz"
    require(manifest["archive"]["path"] == expected, "upload_archive_path")
    return header


def read_stream(fd, amount, deadline):
    """Actual fd reads, including pipes; a slow uploader cannot own the lock forever."""
    output = bytearray()
    while len(output) < amount:
        require(select.select([fd], [], [], remaining(deadline, 20))[0], "ingress_timeout")
        data = os.read(fd, min(65536, amount - len(output)))
        require(bool(data), "ingress_truncated")
        output.extend(data)
    return bytes(output)


def read_header(fd, deadline, limit=65536):
    output = bytearray()
    while len(output) <= limit:
        char = read_stream(fd, 1, deadline)
        if char == b"\n":
            return parse(bytes(output), limit)
        output.extend(char)
    raise ReleaseError("input_size")


def eof(fd, deadline):
    require(select.select([fd], [], [], remaining(deadline, 20))[0], "ingress_timeout")
    require(os.read(fd, 1) == b"", "ingress_extra_bytes")


def remove_upload(path):
    if not path.exists():
        return
    require(not path.is_symlink() and path.is_dir(), "stage_shape")
    require(all(item.name == "snapshot.tar.gz" and stat.S_ISREG(item.lstat().st_mode)
                for item in path.iterdir()), "stage_shape")
    shutil.rmtree(path)
    sync_dir(path.parent)


def cleanup_uploads(root, static_root):
    """Called only under release.lock, so no live ingress can own these files."""
    if not static_root.exists():
        return
    for path in static_root.iterdir():
        if re.fullmatch(r"\.upload-[a-z0-9_]+", path.name):
            remove_upload(path)
        elif path.name.startswith(".stage-") and matches(ID, path.name[7:]):
            receipt = root / "publications" / (path.name[7:] + ".json")
            if not receipt.exists() or read_record(receipt)["state"] in {"COMMITTED", "FAILED"}:
                remove_upload(path)


def publication_result(record):
    header = record["header"]
    manifest = header["manifest"]
    return {"publication_id": header["publication_id"], "sequence": header["sequence"],
            "action": header["action"], "state": record["state"], "trigger_sha": header["trigger_sha"],
            "corpus_source_sha": manifest["source_sha"], "corpus_id": manifest["corpus_id"],
            "archive_sha256": manifest["archive"]["sha256"], "error_code": record.get("error_code"),
            "cleanup_complete": record["state"] == "COMMITTED" and not record.get("cleanup_pending", False)}


def restore_index_inbox(root):
    """Under release.lock: the fsynced receipt also is an enqueue intent."""
    pending = root / "pending-index.json"
    if pending.exists():
        return
    directory = root / "publications"
    records = [read_record(path) for path in directory.glob("*.json")]
    unfinished = [r for r in records if r["state"] not in {"COMMITTED", "FAILED"} or r.get("cleanup_pending")]
    if unfinished:
        record = min(unfinished, key=lambda r: (r["header"]["sequence"], r["header"]["publication_id"]))
        write_json(pending, record["header"])


def query_status(root, adapter, query=None):
    if query is None:
        return Controller(root, adapter).status()
    require(set(query) == {"schema_version", "kind", "id"}
            and type(query["schema_version"]) is int and query["schema_version"] == 1
            and query["kind"] in {"release", "publication"} and matches(ID, query["id"]), "status_query")
    directory = "releases" if query["kind"] == "release" else "publications"
    path = Path(root) / directory / (query["id"] + ".json")
    if path.exists():
        record = read_record(path)
        return Controller.result(record) if query["kind"] == "release" else publication_result(record)
    if query["kind"] == "release":
        pending = Path(root) / "pending-deploy.json"
        if pending.exists():
            envelope = parse(read_file(pending))
            if envelope["release_id"] == query["id"]:
                return {**envelope, "state": "QUEUED", "cleanup_complete": False}
        rejected = Path(root) / "rejected" / (query["id"] + ".json")
        if rejected.exists():
            return parse(read_file(rejected))
    return {"state": "NOT_FOUND", "id": query["id"], "kind": query["kind"]}


def read_status_query(fd):
    deadline = time.monotonic() + 20
    require(select.select([fd], [], [], remaining(deadline))[0], "ingress_timeout")
    first = os.read(fd, 1)
    if first == b"":
        return None
    raw = bytearray(first)
    while not raw.endswith(b"\n") and len(raw) <= 1024:
        raw.extend(read_stream(fd, 1, deadline))
    eof(fd, deadline)
    return parse(bytes(raw), 1024)


def ingest(root, static_root, fd, *, seconds=30):
    """JSON line + exactly archive.bytes raw bytes + EOF; no client-side paths."""
    root, static_root = Path(root), Path(static_root)
    deadline = time.monotonic() + seconds
    header = validate_upload(read_header(fd, deadline))
    with locked(root):
        cleanup_uploads(root, static_root)
        restore_index_inbox(root)
        pending = root / "pending-index.json"
        record_path = root / "publications" / (header["publication_id"] + ".json")
        record = read_record(record_path) if record_path.exists() else None
        if record:
            require(record["header"] == header, "mutated_duplicate")
        else:
            if pending.exists():
                require(read_record(pending) == header, "publication_busy")
            require(time.time() < header["deadline"] <= time.time() + TRANSACTION, "deadline")
        manifest = header["manifest"]
        size = manifest["archive"]["bytes"] if header["action"] == "publish" else 0
        require(0 <= size <= MAX_ARCHIVE_BYTES, "input_size")
        ensure_directory(static_root, 0o755)
        require(shutil.disk_usage(static_root).free > 2 * MAX_ARCHIVE_BYTES, "disk_capacity")
        temporary = Path(tempfile.mkdtemp(prefix=".upload-", dir=static_root))
        try:
            archive = temporary / "snapshot.tar.gz"
            hashed = hashlib.sha256()
            with archive.open("xb") as stream:
                for start in range(0, size, 65536):
                    chunk = read_stream(fd, min(65536, size - start), deadline)
                    hashed.update(chunk)
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            eof(fd, deadline)
            if size:
                require(hashed.hexdigest() == manifest["archive"]["sha256"], "archive_hash")
            if record:
                return publication_result(record)
            if size:
                stage = static_root / (".stage-" + header["publication_id"])
                if stage.exists():
                    require(read_file(stage / "snapshot.tar.gz", MAX_ARCHIVE_BYTES) == read_file(archive, MAX_ARCHIVE_BYTES), "stage_conflict")
                else:
                    sync_dir(temporary)
                    os.rename(temporary, stage)
                    sync_dir(static_root)
            write_json(record_path, {"header": header, "state": "RECEIVED"})
            write_json(pending, header)
            return {"publication_id": header["publication_id"], "state": "QUEUED"}
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)


class Publisher:
    def __init__(self, root, static_root, verifier=None):
        self.root, self.static_root = Path(root), Path(static_root)
        self.verifier = verifier or self.verify

    @staticmethod
    def verify(archive, header, deadline):
        run(attestation_command(str(archive), header["manifest"]["source_sha"]), deadline)
        for sha in {header["manifest"]["source_sha"], header["trigger_sha"]}:
            comparison = parse(run(["gh", "api", f"repos/{REPO}/compare/{sha}...main"], deadline), 2 * 1024 * 1024)
            require(comparison.get("status") in {"ahead", "identical"}
                    and comparison.get("merge_base_commit", {}).get("sha") == sha, "main_ancestry")

    def unacknowledged_archives(self, after, *, through=None):
        """Caller holds release.lock; publish receipts outlive their inboxes.

        Until a later reference acknowledges Pages progress, an exposed archive
        may still be the public pointer's target. Age cannot resolve that gap.
        Include incomplete nonfailed receipts conservatively across recovery.
        """
        archives = set()
        for path in (self.root / "publications").glob("*.json"):
            record = read_record(path)
            header = record["header"]
            if (header["action"] == "publish" and record["state"] != "FAILED"
                    and header["sequence"] > after
                    and (through is None or header["sequence"] <= through)):
                archives.add(header["manifest"]["archive"]["sha256"])
        return archives

    def publish(self, header):
        header = validate_upload(header)
        with locked(self.root):
            manifest = header["manifest"]
            archive_hash = manifest["archive"]["sha256"]
            record_path = self.root / "publications" / (header["publication_id"] + ".json")
            record = read_record(record_path)
            require(record["header"] == header, "mutated_duplicate")
            if record["state"] == "COMMITTED":
                return self.finish_cleanup(record_path, record)
            verified = record["state"] in {"VERIFIED", "RECOVERY_REQUIRED"}
            require(record["state"] != "FAILED", "publication_terminal")
            deadline = time.monotonic() + (TRANSACTION if verified else min(TRANSACTION, header["deadline"] - time.time()))
            remaining(deadline)
            target = self.static_root / archive_hash
            stage = self.static_root / (".stage-" + header["publication_id"])
            if header["action"] == "publish":
                archive = (target if target.exists() else stage) / "snapshot.tar.gz"
                verify_archive(read_file(archive, MAX_ARCHIVE_BYTES), manifest)
                if not verified:
                    self.verifier(archive, header, deadline)
                # Bookkeeping precedes visibility. The durable publish receipt
                # also protects an unknown Pages outcome until a later reference.
                reference = self.root / "references" / (archive_hash + ".json")
                write_json(reference, {"last_reference": time.time()})
                write_json(self.root / "manifests" / (archive_hash + ".json"), manifest)
                record["state"] = "VERIFIED"
                write_json(record_path, record)
                if not target.exists():
                    os.chmod(archive, 0o644)
                    os.chmod(stage, 0o755)
                    sync_dir(stage)
                    os.rename(stage, target)
                    sync_dir(self.static_root)
                elif stage.exists():
                    shutil.rmtree(stage)  # Exact validated owned staging directory only.
            else:
                # A reference acknowledgment follows successful Pages publication;
                # it cannot introduce an object or change the verified manifest.
                require(read_record(self.root / "manifests" / (archive_hash + ".json")) == manifest, "unpublished_manifest")
                verify_archive(read_file(target / "snapshot.tar.gz", MAX_ARCHIVE_BYTES), manifest)
                if not verified:
                    self.verifier(target / "snapshot.tar.gz", header, deadline)
                current_path = self.root / "current-index.json"
                current = None
                if current_path.exists():
                    current = read_record(current_path)
                    require(header["sequence"] > current["sequence"] or current == header, "stale_sequence")
                record["state"] = "VERIFIED"
                write_json(record_path, record)
                displaced = self.unacknowledged_archives(current["sequence"] if current else 0,
                                                        through=header["sequence"])
                if current:
                    displaced.add(current["manifest"]["archive"]["sha256"])
                # Every displaced uncertain object gets a full grace period
                # BEFORE advancing the acknowledgement watermark. A crash here
                # leaves the old watermark protecting unfinished writes; a retry
                # after pointer persistence finds all timestamps already durable.
                for key in sorted(displaced | {archive_hash}):
                    write_json(self.root / "references" / (key + ".json"), {"last_reference": time.time()})
                write_json(current_path, header)
            record["state"] = "COMMITTED"
            record["cleanup_pending"] = True
            record.pop("error_code", None)
            write_json(record_path, record)
            return self.finish_cleanup(record_path, record)

    def finish_cleanup(self, record_path, record):
        self.clear_pending(record["header"])
        if record.get("cleanup_pending") or record.get("error_code"):
            record["cleanup_pending"] = False
            record.pop("error_code", None)
            write_json(record_path, record)
        return record

    def clear_pending(self, header):
        pending = self.root / "pending-index.json"
        if pending.exists() and read_record(pending) == header:
            pending.unlink()
            sync_dir(self.root)

    def recover(self):
        pending = self.root / "pending-index.json"
        with locked(self.root):
            cleanup_uploads(self.root, self.static_root)
            restore_index_inbox(self.root)
            header = read_record(pending) if pending.exists() else None
        if header is None:
            return {"state": "EMPTY"}
        try:
            return self.publish(header)
        except Exception as error:
            if isinstance(error, ReleaseError) and error.code == "busy":
                raise  # Another worker owns the journal; contention is not failure.
            # A failed verifier/deadline cannot permanently occupy the ingress
            # slot. Keep immutable ID outcome; a new attempt uses a new ID.
            with locked(self.root):
                record_path = self.root / "publications" / (header["publication_id"] + ".json")
                record = read_record(record_path)
                if record["state"] == "COMMITTED":
                    # Visibility/reference already accepted. Even unlink+fsync
                    # failure must only retry cleanup, never rewrite acceptance.
                    record.update(cleanup_pending=True, error_code="publication_cleanup_failed")
                    write_json(record_path, record)
                    return record
                # Visibility may precede COMMITTED after a crash: VERIFIED receipts
                # are reconciled on restart, never described as a committed job.
                verified = record["state"] in {"VERIFIED", "RECOVERY_REQUIRED"}
                record.update(state="RECOVERY_REQUIRED" if verified else "FAILED",
                              error_code=getattr(error, "code", "publication_failed"))
                write_json(record_path, record)
                if not verified:
                    self.clear_pending(header)
                    stage = self.static_root / (".stage-" + header["publication_id"])
                    remove_upload(stage)
                return record

    def gc(self, *, now=None):
        """Internal operator maintenance: references and pins, never mtime alone."""
        now = time.time() if now is None else now
        with locked(self.root):
            pins = parse(read_file(self.root / "pins.json"))["archives"]
            require(isinstance(pins, list) and all(matches(HEX, x) for x in pins), "pins_invalid")
            current = read_record(self.root / "current-index.json")
            retained = set(pins) | {current["manifest"]["archive"]["sha256"]}
            retained.update(self.unacknowledged_archives(current["sequence"]))
            pending = self.root / "pending-index.json"
            if pending.exists():
                retained.add(read_record(pending)["manifest"]["archive"]["sha256"])
            removed = []
            for path in self.static_root.iterdir():
                if not matches(HEX, path.name) or path.name in retained or path.is_symlink():
                    continue
                reference = self.root / "references" / (path.name + ".json")
                last = parse(read_file(reference))["last_reference"]
                require(type(last) in {int, float} and 0 <= last <= now, "reference_invalid")
                if now - last >= 7 * 86400:
                    # Only exact known immutable-layout objects are ours to remove.
                    require({p.name for p in path.iterdir()} == {"snapshot.tar.gz"}, "store_layout")
                    require(digest(read_file(path / "snapshot.tar.gz", MAX_ARCHIVE_BYTES)) == path.name, "store_corrupt")
                    shutil.rmtree(path)
                    sync_dir(self.static_root)
                    removed.append(path.name)
            return removed


def schedule(kind):
    require(kind in {"deploy", "index", "recover", "bootstrap"}, "job_kind")
    # Shared unit name and controller lock serialize all host effects. No --pipe,
    # --wait or inherited SSH stdin; timer recovers a crash before enqueue.
    return run(["systemd-run", "--unit=v8std-release-job", "--collect", "--no-block",
                "--property=Type=exec", "--property=RuntimeMaxSec=300s", "--property=TimeoutStopSec=5s",
                "--property=KillMode=control-group", "/usr/bin/python3", "-I", INSTALL, "_" + kind],
               time.monotonic() + 10)


def submit(root, adapter, raw):
    envelope = validate_envelope(raw, expired=True)
    controller = Controller(root, adapter)
    with locked(root):
        existing = controller.existing(envelope)
        if existing:
            return controller.result(existing)
        require(adapter.policy.get("runtime_enabled") is True, "runtime_not_activated")
        adapter.config(envelope)
        require((Path(root) / "active.json").is_file(), "predecessor_required")
        validate_envelope(raw)
        require(envelope["deadline"] - time.time() > RECOVERY_RESERVE, "insufficient_transaction_budget")
        pending = Path(root) / "pending-deploy.json"
        if pending.exists():
            previous = parse(read_file(pending))
            require(previous == envelope or any(item["envelope"] == previous and item.get("cleanup_complete")
                                               for item in controller.journals()), "busy")
        write_json(pending, envelope)
    schedule("deploy")
    return {"state": "QUEUED", "release_id": envelope["release_id"]}


def main():
    require(len(sys.argv) == 2, "command")
    command = sys.argv[1]
    require(command in {"validate-envelope", "deploy", "recover", "status", "publish-index",
                        "_deploy", "_index", "_recover", "bootstrap", "bootstrap-recover", "bootstrap-status",
                        "_bootstrap", "_legacy-allowed"}, "command")
    if command == "validate-envelope":
        header = read_header(sys.stdin.fileno(), time.monotonic() + 20, 8192)
        eof(sys.stdin.fileno(), time.monotonic() + 20)
        return validate_envelope(canonical_json(header))
    require(os.geteuid() == 0, "host_privilege")
    if command == "_legacy-allowed":
        require(legacy_start_allowed(ROOT), "legacy_fenced")
        return {"state": "LEGACY_ALLOWED"}
    policy = trusted_policy()
    adapter = HostAdapter(ROOT, policy)
    controller = Controller(ROOT, adapter)
    if command in {"status", "bootstrap-status"}:
        return query_status(ROOT, adapter, read_status_query(sys.stdin.fileno()))
    if command == "deploy":
        envelope = read_header(sys.stdin.fileno(), time.monotonic() + 20, 8192)
        eof(sys.stdin.fileno(), time.monotonic() + 20)
        return submit(ROOT, adapter, canonical_json(envelope))
    if command == "bootstrap":
        envelope = read_header(sys.stdin.fileno(), time.monotonic() + 20, 8192)
        eof(sys.stdin.fileno(), time.monotonic() + 20)
        return BootstrapController(ROOT, adapter).submit(canonical_json(envelope))
    if command == "_bootstrap":
        return BootstrapController(ROOT, adapter).execute()
    if command == "bootstrap-recover":
        return controller.recover()
    if command == "publish-index":
        result = ingest(ROOT, policy["static_root"], sys.stdin.fileno())
        if result["state"] not in {"COMMITTED", "FAILED"} or (
                result["state"] == "COMMITTED" and not result.get("cleanup_complete", True)):
            schedule("index")
        return result
    if command == "recover":
        schedule("recover")
        return {"state": "RECOVERY_QUEUED"}
    if command in {"_recover", "_deploy"}:
        controller.recover()
        pending = ROOT / "pending-deploy.json"
        if pending.exists():
            envelope = parse(read_file(pending))
            try:
                result = controller.deploy(canonical_json(envelope))
                if result["state"] == "REJECTED":
                    # Reconcile a crash after the durable rejection but before
                    # inbox deletion, without reconsidering its immutable ID.
                    with locked(ROOT):
                        if pending.exists() and parse(read_file(pending)) == envelope:
                            pending.unlink()
                            sync_dir(ROOT)
            except ReleaseError as error:
                if error.code not in {"deadline", "insufficient_transaction_budget", "runtime_not_activated", "predecessor_required", "stale_sequence"}:
                    raise
                with locked(ROOT):
                    write_json(ROOT / "rejected" / (envelope["release_id"] + ".json"),
                               {**envelope, "state": "REJECTED", "error_code": error.code})
                    if parse(read_file(pending)) == envelope:
                        pending.unlink()
                        sync_dir(ROOT)
    if command in {"_recover", "_index"}:
        return Publisher(ROOT, policy["static_root"]).recover()
    return controller.status()


if __name__ == "__main__":
    try:
        print(json.dumps(main(), sort_keys=True))
    except Exception as error:
        print(json.dumps({"state": "REJECTED", "error_code": error.code if isinstance(error, ReleaseError) else "host_failure"}))
        raise SystemExit(1)
