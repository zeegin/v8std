"""Docker command seam for the real HostAdapter; never overrides start/stop."""
import json
import gzip
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
from unittest.mock import patch

from tests import mcp_snapshot_fixtures as corpus

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v8std_mcp_release as release

HOST_LOG = Path("/var/log/v8std-mcp/tool-usage.jsonl")
CONTAINER_LOG = "/var/log/v8std-mcp-usage.jsonl"


def launch_inputs(name="candidate"):
    config = {"site_url": "http://127.0.0.1:9/", "refresh_seconds": 0,
              "max_snippet_chars": 4000, "memory_bytes": 512 * 1024 * 1024, "cpus": 1}
    key = release.digest(release.canonical_json(config))
    record = {"release_id": name, "name": "v8std-release-" + name,
              "envelope_hash": "a" * 64, "runtime_source_sha": "b" * 40,
              "platform_digest": "sha256:" + "c" * 64, "port": 18765,
              "configuration_digest": key,
              "descriptors": {"sha256:" + "d" * 64: next(iter(release.CONFIG_TYPES))}}
    return record, {"platform": "linux/arm64", "configs": {key: config}}


class DockerCommands:
    """Complete inspect fields consumed at this boundary; no runtime proof."""
    def __init__(self, record, info=None):
        self.record, self.info, self.calls = record, info, []

    def __call__(self, argv, deadline):
        argv = list(map(str, argv))
        self.calls.append(argv)
        if argv[:2] == ["docker", "inspect"]:
            if self.info is None:
                raise release.ReleaseError("command_failed")
            return json.dumps([self.info]).encode()
        if argv[:2] == ["docker", "ps"]:
            return b"" if self.info is None else (self.record["name"] + "\n").encode()
        if argv[:2] == ["docker", "run"]:
            image = release.IMAGE + "@" + self.record["platform_digest"]
            mounts = []
            for i, arg in enumerate(argv[:-1]):
                if arg == "--mount":
                    values = dict(part.split("=", 1) if "=" in part else (part, True)
                                  for part in argv[i + 1].split(","))
                    mounts.append({"Type": values["type"], "Source": values["source"],
                                   "Destination": values["target"], "RW": not values.get("readonly", False)})
            self.info = {"Config": {"Image": image, "Cmd": argv[argv.index(image) + 1:],
                         "Labels": {"pro.v8std.release": self.record["release_id"],
                                    "pro.v8std.envelope": self.record["envelope_hash"],
                                    "org.opencontainers.image.revision": self.record["runtime_source_sha"]}},
                         "Image": "sha256:" + "d" * 64, "Mounts": mounts, "State": {"Running": True}}
            return b"fixture-container\n"
        if argv[:2] in (["docker", "start"], ["docker", "stop"]):
            self.info["State"]["Running"] = argv[1] == "start"
            return (self.record["name"] + "\n").encode()
        raise AssertionError("unexpected fixture command: " + repr(argv))


def native_initialize():
    """Only called in the named root helper's disposable /fixture volume."""
    root = Path("/fixture")
    root.chmod(0o755)  # Legacy su user can traverse; private logs still0700.
    archive, manifest = corpus.snapshot_fixture()
    destination = root / "source/ai/mcp/v1"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / manifest["archive"]["sha256"]).mkdir(exist_ok=True)
    (destination / manifest["archive"]["sha256"] / "snapshot.tar.gz").write_bytes(archive)
    (destination / "manifest.json").write_bytes(corpus.json_bytes(manifest))
    legacy = root / "legacy"
    legacy.mkdir(mode=0o750)
    legacy.chmod(0o750)
    os.chown(legacy, 10002, 10002)
    history = legacy / "tool-usage.jsonl"
    history.write_bytes(b'{"ts":"legacy-before","tool":"legacy"}\n')
    os.chown(history, 10002, 10002)
    history.chmod(0o640)
    return manifest


def native_plan(name, port):
    """Capture the real launcher; the host test executes its Docker run argv.

    Only fixture identities and bind-source roots are translated on the host.
    This is a command-boundary rehearsal, not attestation/controller acceptance.
    """
    root = Path("/fixture")
    record, policy = launch_inputs(name)
    config = next(iter(policy["configs"].values())) | {"site_url": "http://source:8080/"}
    key = release.digest(release.canonical_json(config))
    policy["configs"] = {key: config}
    record.update(name=name, port=port, configuration_digest=key)
    daemon = DockerCommands(record)
    adapter = release.HostAdapter(root / "state", policy)
    with patch.object(release, "USAGE_LOG", root / "logs/tool-usage.jsonl"), patch.object(release, "run", daemon):
        adapter.control(record, "resume", "a" * 32)
        adapter.start(record, time.monotonic() + 10)
    return next(argv for argv in daemon.calls if argv[:2] == ["docker", "run"])


def native_observe():
    result = {}
    for name in ("logs", "legacy"):
        path = Path("/fixture") / name / "tool-usage.jsonl"
        info, parent = path.stat(), path.parent.stat()
        result[name] = {"inode": info.st_ino, "uid": info.st_uid, "gid": info.st_gid,
                        "mode": stat.S_IMODE(info.st_mode), "parent_mode": stat.S_IMODE(parent.st_mode),
                        "events": [json.loads(line) for line in path.read_text().splitlines()],
                        "archives": {p.name: gzip.decompress(p.read_bytes()).decode()
                                     for p in path.parent.glob("tool-usage.jsonl.*.gz")}}
    return result


def native_rotate():
    stanza = (ROOT / "scripts/v8std_mcp_usage.logrotate").read_text()
    config = Path("/fixture/logrotate.conf")
    config.write_text(stanza.replace("/var/lib/v8std-mcp/tool-usage.jsonl", "/fixture/legacy/tool-usage.jsonl")
                     .replace("/var/log/v8std-mcp/tool-usage.jsonl", "/fixture/logs/tool-usage.jsonl"))
    config.chmod(0o600)
    result = subprocess.run(["logrotate", "--force", "--state", "/fixture/logrotate.state", str(config)],
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise AssertionError(result.stderr)
    return {"logrotate": result.stderr, "files": native_observe()}
