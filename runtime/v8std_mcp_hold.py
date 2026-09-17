"""Private, read-only host control mount; never an MCP method or source setting.

One control directory and cache per managed container. Host atomically replaces
control.json; the runtime can read it but cannot write it. Only the coordinator
acknowledges a command, after cancelling preparation and selecting actual bytes.
Missing/malformed control fails closed (keeps serving the last accepted data,
does not refresh or acknowledge). No persisted Python objects cross this path.
"""
from pathlib import Path
import re
import time

from runtime.v8std_mcp_snapshot_format import canonical_json, strict_json, validate_manifest, SnapshotError

CONTROL_PATH = Path("/run/v8std-release/control.json")


class ReleaseControl:
    def __init__(self, coordinator, path):
        self.coordinator = coordinator
        self.path = path

    def read(self):
        from runtime.v8std_mcp_snapshots import _read_file, LoaderError
        request = strict_json(_read_file(self.path, 65536))
        if (set(request) != {"schema_version", "token", "mode", "manifest"}
                or type(request["schema_version"]) is not int or request["schema_version"] != 1
                or not isinstance(request["token"], str)
                or not re.fullmatch("[a-f0-9]{32}", request["token"])
                or request["mode"] not in {"hold", "resume"}):
            raise LoaderError("configuration")
        if request["manifest"] is not None:
            validate_manifest(canonical_json(request["manifest"]))
            if request["mode"] != "hold":
                raise LoaderError("configuration")
        return request

    def pin(self, archive):
        from runtime.v8std_mcp_snapshots import _file_lock
        store = self.coordinator.store
        deadline = time.monotonic() + 1
        with _file_lock(store.namespace / ".lock", deadline):
            with _file_lock(store.cache_dir / ".volume.lock", deadline):
                store._atomic_file(store.namespace / "runtime-pin.json",
                                   canonical_json({"archive": archive}), deadline)

    def run(self):
        from runtime.v8std_mcp_snapshots import LoaderError
        owner = self.coordinator
        initial = True
        last = None
        seen = None
        next_refresh = 0
        failures = 0

        def read_request():
            nonlocal seen
            try:
                return self.read()
            except (LoaderError, SnapshotError, OSError):
                # Recovery of the command file starts a fresh validation, even
                # for the same token. Do not bypass build-failure backoff.
                seen = None
                raise

        while not owner._stop.is_set():
            try:
                request = read_request()
                changed = request != seen
                if changed:
                    next_refresh = 0
                seen = request
                if request["mode"] == "hold":
                    if request != last and time.monotonic() >= next_refresh:
                        manifest = request["manifest"]
                        if manifest is not None:
                            result, metadata = owner.store._run("refresh", owner.build,
                                CommandStop(self, request), selected_manifest=manifest)
                            if read_request() != request or owner._stop.is_set():
                                continue
                            owner._accept(result, metadata, checked=False)
                            del result
                        elif not owner.status()["ready"]:
                            raise LoaderError("INDEX_NOT_READY")
                        # Capture uses the actual process identity, never state.json.
                        self.pin(owner.status()["archive_sha256"])
                        with owner._lock:
                            owner._state["hold_token"] = request["token"]
                            owner._state["release_control_token"] = request["token"]
                        last = request
                        initial = False
                else:
                    with owner._lock:
                        owner._state["hold_token"] = None
                        owner._state["release_control_token"] = request["token"]
                    last = request
                    if initial:
                        result, metadata = owner.store._run("cached", owner.build, CommandStop(self, request))
                        if read_request() != request or owner._stop.is_set():
                            continue
                        if metadata:
                            owner._accept(result, metadata, checked=False)
                        del result
                        initial = False
                    if time.monotonic() >= next_refresh:
                        result, metadata = owner.store._run("refresh", owner.build,
                            CommandStop(self, request), current_archive=owner._archive_sha256)
                        if read_request() != request or owner._stop.is_set():
                            continue
                        owner._accept(result, metadata, checked=True)
                        del result
                        failures = 0
                        next_refresh = (time.monotonic() + owner._delay(0)
                                        if owner.refresh_seconds else float("inf"))
            except (LoaderError, SnapshotError, OSError) as error:
                failures += 1
                last = None  # Revoked acknowledgement must be earned again.
                with owner._lock:
                    owner._state["refresh_error_code"] = getattr(error, "code", "configuration")
                    # A stale acknowledgment is never proof of a new hold.
                    owner._state["hold_token"] = None
                    owner._state["release_control_token"] = None
                next_refresh = time.monotonic() + owner._delay(failures)
            owner._stop.wait(.1)


class CommandStop:
    def __init__(self, control, request):
        self.control, self.request = control, request

    def is_set(self):
        try:
            return self.control.coordinator._stop.is_set() or self.control.read() != self.request
        except (ValueError, OSError):
            return True
