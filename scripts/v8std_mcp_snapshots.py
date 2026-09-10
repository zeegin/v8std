"""Bounded snapshot loading and immutable-generation coordination.

Only the application's own spawned worker uses pickle, over a private socketpair.
Disk and HTTP inputs are always bytes/strict JSON verified by the format module.
Builders and their results must be spawn-serializable (including bounded local
result reconstruction). Network, verification, build and commit run in the child;
the supervisor can terminate and reap it even inside DNS or a blocking builder.

Cache layout: <volume>/v1-<sha256(normalized site)>/{state.json,rollback.json,
pins.json,generations/<archive sha256>/...}. Host-owned pins.json is an atomic
JSON object {"archives": [<archive sha256>, ...]}. Invalid pins fail GC closed.
Python references returned by current() retain old in-memory generations for
in-flight requests; their lifetime is independent of disk-generation retention.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import http.client
import io
import multiprocessing
import os
from pathlib import Path
import pickle
import random
import re
import select
import shutil
import socket
import ssl
import stat
import struct
import tarfile
import tempfile
import threading
import time
from urllib.parse import urlsplit

from v8std_mcp_snapshot_format import (
    DEFAULT_SITE_URL, PUBLIC_DELIVERY_URL, MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES,
    MEMBER_LIMITS, SnapshotError, VerifiedSnapshot, canonical_json,
    canonical_page_path, normalize_site_url, sha256, strict_json,
    validate_manifest, verify_archive,
)

ATTEMPT_SECONDS = 60
READ_SECONDS = 20
CACHE_BYTES = 256 * 1024 * 1024
_CHUNK = 64 * 1024
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_TEMP = re.compile(r"\.(?:stage|pointer)-[a-z0-9_]+\Z")
_CODES = frozenset({
    "loader_failed", "INDEX_NOT_READY", "url_policy", "redirect_limit",
    "http_status", "http_headers", "http_encoding", "http_size", "network",
    "deadline", "closed", "cache_io", "cache_budget", "lock_timeout",
    "prepare_failed", "worker_failed", "configuration",
})


class LoaderError(ValueError):
    """Bounded loader diagnostics; never include URLs, input data or raw errors."""

    def __init__(self, code: str):
        self.code = code if code in _CODES else "loader_failed"
        super().__init__(self.code)


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LoaderError("deadline")
    return remaining


def _allowed_url(reference: str, current: str, boundary: str) -> str:
    # Do not urljoin first: it removes dot segments before they can be rejected.
    try:
        if not isinstance(reference, str) or not reference or reference.startswith("//"):
            raise LoaderError("url_policy")
        if not urlsplit(reference).scheme:
            if reference.startswith("/"):
                parts = urlsplit(current)
                reference = f"{parts.scheme}://{parts.netloc}" + reference
            else:
                reference = current.rsplit("/", 1)[0] + "/" + reference
        return boundary + canonical_page_path(reference, boundary)
    except (SnapshotError, ValueError):
        raise LoaderError("url_policy") from None


def _archive_url(manifest, manifest_url, site_url):
    path = manifest["archive"]["path"]
    boundary = site_url
    if site_url == DEFAULT_SITE_URL and path.startswith(PUBLIC_DELIVERY_URL):
        boundary = PUBLIC_DELIVERY_URL
    return _allowed_url(path, manifest_url, boundary), boundary


def _download(url, boundary, headers, limit, deadline, read_seconds, *, archive=False):
    """One bounded HTTP exchange, validating each redirect before connecting."""
    for redirects in range(4):
        url = _allowed_url(url, url, boundary)
        parts = urlsplit(url)
        timeout = min(read_seconds, _remaining(deadline))
        if parts.scheme == "https":
            connection = http.client.HTTPSConnection(
                parts.hostname, parts.port, timeout=timeout, context=ssl.create_default_context())
        else:
            connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=timeout)
        try:
            # Explicit connect retains the socket even when getresponse detaches
            # a Connection: close response. DNS is bounded by the parent process.
            connection.connect()
            stream_socket = connection.sock
            stream_socket.settimeout(min(read_seconds, _remaining(deadline)))
            connection.request("GET", parts.path, headers={
                "Accept-Encoding": "identity", "User-Agent": "v8std-snapshot/1", **headers})
            stream_socket.settimeout(min(read_seconds, _remaining(deadline)))
            response = connection.getresponse()
            with response:
                if response.status in {301, 302, 303, 307, 308}:
                    if redirects == 3:
                        raise LoaderError("redirect_limit")
                    locations = response.headers.get_all("Location", [])
                    if len(locations) != 1:
                        raise LoaderError("http_headers")
                    url = _allowed_url(locations[0], url, boundary)
                    continue
                if response.status == 304:
                    return 304, b"", {}, url
                if response.status != 200:
                    raise LoaderError("http_status")
                encodings = response.headers.get_all("Content-Encoding", [])
                if encodings and encodings != ["identity"]:
                    raise LoaderError("http_encoding")
                if archive and response.headers.get_content_type() != "application/gzip":
                    raise LoaderError("http_headers")
                lengths = response.headers.get_all("Content-Length", [])
                length = None
                if lengths:
                    if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
                        raise LoaderError("http_headers")
                    length = int(lengths[0])
                    if length > limit:
                        raise LoaderError("http_size")
                transfers = response.headers.get_all("Transfer-Encoding", [])
                if transfers and (transfers != ["chunked"] or lengths):
                    raise LoaderError("http_headers")
                payload = bytearray()
                while not response.isclosed():
                    stream_socket.settimeout(min(read_seconds, _remaining(deadline)))
                    chunk = response.read1(min(_CHUNK, limit - len(payload) + 1))
                    if not chunk:
                        break
                    payload.extend(chunk)
                    if len(payload) > limit:
                        raise LoaderError("http_size")
                if length is not None and length != len(payload):
                    raise LoaderError("http_size")
                _remaining(deadline)
                validators = {}
                for name in ("ETag", "Last-Modified"):
                    values = response.headers.get_all(name, [])
                    if len(values) == 1 and _safe_header(values[0]):
                        validators[name] = values[0]
                return 200, bytes(payload), validators, url
        except (TimeoutError, OSError, http.client.HTTPException):
            _remaining(deadline)
            raise LoaderError("network") from None
        finally:
            connection.close()
    raise LoaderError("redirect_limit")


def _safe_header(value):
    return (isinstance(value, str) and 0 < len(value) <= 1024
            and all(32 <= ord(char) < 127 for char in value))


def _directory(path, *, create=False):
    if create and not path.exists():
        _directory(path.parent, create=True)
        path.mkdir(mode=0o700, exist_ok=True)
        # Persist each newly created directory entry, including intermediate
        # parents. An existing mounted cache needs no writes to the container root.
        _fsync_directory(path.parent)
    if not stat.S_ISDIR(path.lstat().st_mode):
        raise LoaderError("cache_io")


def _read_file(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise LoaderError("cache_io")
        payload = stream.read(limit + 1)
        if len(payload) > limit:
            raise LoaderError("cache_io")
        return payload


def _fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _file_lock(path, deadline):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    waited = False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise LoaderError("cache_io")
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                waited = True
                if deadline - time.monotonic() <= 0:
                    raise LoaderError("lock_timeout")
                time.sleep(max(0, min(.025, deadline - time.monotonic())))
        yield waited
    finally:
        os.close(fd)  # OS releases flock even on process termination/crash.


def _prepare(snapshot, prepare, *, current_archive=None):
    try:
        metadata = {"corpus_id": snapshot.metadata["corpus_id"],
                    "source_sha": snapshot.metadata["source_sha"],
                    "archive_sha256": snapshot.archive_sha256}
        if current_archive == snapshot.archive_sha256:
            # Only a verified reusable entry may take this private path. The
            # caller's identity belongs to its already accepted ready generation.
            result = None
            metadata["unchanged"] = True
        else:
            result = snapshot if prepare is None else prepare(snapshot)
        # Serialization is also preparation: an unpickleable lock must not
        # advance the disk pointer. These bytes go ONLY to our private IPC socket.
        return pickle.dumps(("ok", result, metadata), protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        raise LoaderError("prepare_failed") from None


class SnapshotStore:
    def __init__(self, site_url: str, cache_dir: Path):
        self.site_url = normalize_site_url(site_url)
        self.cache_dir = Path(cache_dir).absolute()
        self.namespace = self.cache_dir / ("v1-" + sha256(self.site_url.encode("utf-8")))
        self._attempt_seconds = ATTEMPT_SECONDS
        self._read_seconds = READ_SECONDS
        self._transport = _download

    def _states(self):
        for name in ("state.json", "rollback.json"):
            try:
                state = strict_json(_read_file(self.namespace / name, MAX_MANIFEST_BYTES))
                if (type(state.get("schema_version")) is not int or state["schema_version"] != 1
                        or state.get("site_url") != self.site_url
                        or not self._digest(state.get("active"))
                        or (state.get("previous") is not None
                            and not self._digest(state["previous"]))):
                    continue
                # Recovery retains this record for the next rollback commit,
                # including unknown fields. Reject it before selecting a corpus
                # unless that same commit serializer can represent every field.
                canonical_json(state)
                yield state
            except (OSError, SnapshotError, LoaderError):
                continue

    @staticmethod
    def _digest(value):
        return isinstance(value, str) and bool(_DIGEST.fullmatch(value))

    def _generation(self, digest, manifest=None):
        directory = self.namespace / "generations" / digest
        _directory(directory)
        stored_manifest = validate_manifest(_read_file(directory / "manifest.json", MAX_MANIFEST_BYTES))
        if stored_manifest["archive"]["sha256"] != digest:
            raise LoaderError("cache_io")
        archive = _read_file(directory / "snapshot.tar.gz", MAX_ARCHIVE_BYTES)
        snapshot = verify_archive(archive, stored_manifest)
        if manifest is not None and manifest != stored_manifest:
            snapshot = verify_archive(archive, manifest)
        for name, payload in snapshot.files.items():
            if _read_file(directory / name, MEMBER_LIMITS[name]) != payload:
                raise LoaderError("cache_io")
        return snapshot, stored_manifest

    def _cached_entry(self):
        try:
            _directory(self.cache_dir)
            _directory(self.namespace)
            _directory(self.namespace / "generations")
            seen = set()
            for state in self._states():
                for digest in (state["active"], state.get("previous")):
                    if digest is None or digest in seen:
                        continue
                    seen.add(digest)
                    try:
                        snapshot, manifest = self._generation(digest)
                        validators = state.get("validators", {}) if digest == state["active"] else {}
                        if not isinstance(validators, dict):
                            validators = {}
                        recovered = {**state, "active": digest, "validators": {
                            k: v for k, v in validators.items()
                            if k in {"ETag", "Last-Modified"} and _safe_header(v)}}
                        return snapshot, manifest, recovered
                    except (OSError, SnapshotError, LoaderError):
                        continue
        except (OSError, LoaderError):
            pass
        return None

    def cached(self) -> VerifiedSnapshot | None:
        """Verify local bytes, without network; coordinator calls this in a child."""
        entry = self._cached_entry()
        return entry[0] if entry else None

    def refresh(self, *, prepare=None):
        """Supervise a complete attempt; return preparation only after commit."""
        return self._run("refresh", prepare)[0]

    def _usage(self):
        total = 0
        # Every namespace, pin and staging file in the shared cache volume
        # counts. Never follow a symlink into another tree.
        for directory, dirs, files in os.walk(self.cache_dir, followlinks=False,
                                               onerror=lambda error: _cache_walk_error()):
            for name in [*dirs, *files]:
                info = (Path(directory) / name).lstat()
                if not stat.S_ISDIR(info.st_mode):
                    total += info.st_size
        return total

    def _space(self, needed):
        if self._usage() + needed > CACHE_BYTES:
            raise LoaderError("cache_budget")

    def _write(self, path, payload, deadline):
        self._write_stream(path, io.BytesIO(payload), len(payload), deadline)

    def _write_stream(self, path, source, size, deadline):
        _remaining(deadline)
        self._space(size)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            remaining = size
            while remaining:
                _remaining(deadline)
                chunk = source.read(min(remaining, _CHUNK))
                if not chunk or len(chunk) > remaining:
                    raise LoaderError("cache_io")
                stream.write(chunk)
                remaining -= len(chunk)
            stream.flush()
            os.fsync(stream.fileno())

    def _extract_verified(self, source, snapshot, stage, deadline):
        """Stream the already-verified immutable archive into private staging.

        Task1 alone owns format/semantic rules. It verifies bytes before this
        filesystem step; its buffers are not a substitute for streaming disk
        extraction. Destinations and sizes come only from that verified result,
        never from unverified tar paths. No extract/extractall filesystem API.
        """
        with tarfile.open(fileobj=source, mode="r|gz") as reader:
            for name, payload in snapshot.files.items():
                with reader.extractfile(reader.next()) as member:
                    self._write_stream(stage / name, member, len(payload), deadline)

    def _atomic_file(self, path, payload, deadline):
        temporary = self.namespace / (".pointer-" + os.urandom(12).hex())
        try:
            self._write(temporary, payload, deadline)
            os.replace(temporary, path)
            _fsync_directory(self.namespace)
        finally:
            temporary.unlink(missing_ok=True)

    def _commit_state(self, state, old, deadline):
        old_bytes = canonical_json(old) if old else None
        if old_bytes is not None:
            self._atomic_file(self.namespace / "rollback.json", old_bytes, deadline)
        pointer = self.namespace / "state.json"
        temporary = self.namespace / (".pointer-" + os.urandom(12).hex())
        replaced = False
        try:
            self._write(temporary, canonical_json(state), deadline)
            _remaining(deadline)
            os.replace(temporary, pointer)
            replaced = True
            _fsync_directory(self.namespace)
        except OSError:
            if replaced:
                if old_bytes is not None:
                    # rollback.json was fsynced before activation. Its atomic
                    # rename restores the old pointer even if fsync keeps failing.
                    os.replace(self.namespace / "rollback.json", pointer)
                else:
                    pointer.unlink(missing_ok=True)
                try:
                    _fsync_directory(self.namespace)
                except OSError:
                    pass
            raise
        finally:
            temporary.unlink(missing_ok=True)

    def _gc(self, retained=()):
        states = list(self._states())
        protected = set(retained)
        if states:
            protected.update(d for d in (states[0]["active"], states[0].get("previous")) if d)
        try:
            pins = strict_json(_read_file(self.namespace / "pins.json", MAX_MANIFEST_BYTES))
        except FileNotFoundError:
            pins = {"archives": []}
        archives = pins.get("archives")
        if not isinstance(archives, list) or not all(self._digest(d) for d in archives):
            raise LoaderError("cache_io")
        protected.update(archives)
        for entry in self.namespace.iterdir():
            if _TEMP.fullmatch(entry.name):
                self._remove_owned(entry)
        generations = self.namespace / "generations"
        for entry in generations.iterdir():
            if self._digest(entry.name) and entry.name not in protected:
                self._remove_owned(entry)

    @staticmethod
    def _remove_owned(path):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            shutil.rmtree(path)  # fd-based, symlink-attack-resistant on supported POSIX.
        elif stat.S_ISREG(mode):
            path.unlink()
        # Unknown/symlink paths are not owned cleanup targets.

    def _reuse_checked_entry(self, entry, prepare, deadline, current_archive):
        result = _prepare(entry[0], prepare, current_archive=current_archive)
        if current_archive == entry[0].archive_sha256:
            # A rollback recovery can leave the on-disk current pointer damaged.
            # Metadata-only success must also leave a durable consistent pointer.
            self._commit_state(entry[2], entry[2], deadline)
        return result

    def _refresh(self, prepare, deadline, *, current_archive=None):
        _directory(self.cache_dir, create=True)
        _directory(self.namespace, create=True)
        _directory(self.namespace / "generations", create=True)
        with _file_lock(self.namespace / ".lock", deadline) as waited:
            with _file_lock(self.cache_dir / ".volume.lock", deadline):
                entry = self._cached_entry()
                if waited and entry:
                    return self._reuse_checked_entry(entry, prepare, deadline, current_archive)
                self._gc((entry[0].archive_sha256,) if entry else ())
                headers = {}
                if entry:
                    for field, header in (("ETag", "If-None-Match"), ("Last-Modified", "If-Modified-Since")):
                        if value := entry[2]["validators"].get(field):
                            headers[header] = value
                bootstrap = self.site_url + "ai/mcp/v1/manifest.json"
                status, raw, validators, final_url = self._transport(
                    bootstrap, self.site_url, headers, MAX_MANIFEST_BYTES,
                    deadline, self._read_seconds)
                if status == 304 and entry is None:
                    status, raw, validators, final_url = self._transport(
                        bootstrap, self.site_url, {}, MAX_MANIFEST_BYTES, deadline, self._read_seconds)
                if status == 304:
                    if entry is None:
                        raise LoaderError("http_status")
                    return self._reuse_checked_entry(entry, prepare, deadline, current_archive)
                manifest = validate_manifest(raw)
                archive_url, boundary = _archive_url(manifest, final_url, self.site_url)
                digest = manifest["archive"]["sha256"]
                old = entry[2] if entry else None
                state = {
                    "schema_version": 1, "site_url": self.site_url, "active": digest,
                    "previous": (entry[2].get("previous") if digest == entry[0].archive_sha256
                                 else entry[0].archive_sha256) if entry else None,
                    "validators": validators,
                }
                try:
                    if entry and manifest == entry[1]:
                        # The complete validated manifest equals the one just
                        # verified against archive AND expanded cache bytes.
                        # Any changed field takes the existing strict path below;
                        # no format/metadata consistency rules are duplicated here.
                        reusable = entry[0]
                    else:
                        reusable, _ = self._generation(digest, manifest)
                except (OSError, LoaderError):
                    reusable = None
                except SnapshotError:
                    # A new manifest disagreeing with a verified current archive
                    # is invalid, rather than a reason to fetch that archive again.
                    if entry and entry[0].archive_sha256 == digest:
                        raise
                    reusable = None
                if reusable is not None:
                    result = _prepare(reusable, prepare, current_archive=(
                        current_archive if entry and entry[0].archive_sha256 == digest else None))
                    self._commit_state(state, old, deadline)
                    return result
                self._space(manifest["archive"]["bytes"] + manifest["archive"]["unpacked_bytes"]
                            + len(raw) + 2 * MAX_MANIFEST_BYTES)
                stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=self.namespace))
                try:
                    self._write(stage / "manifest.json", raw, deadline)
                    status, archive, _, _ = self._transport(
                        archive_url, boundary, {}, manifest["archive"]["bytes"],
                        deadline, self._read_seconds, archive=True)
                    if status != 200:
                        raise LoaderError("http_status")
                    self._write(stage / "snapshot.tar.gz", archive, deadline)
                    snapshot = verify_archive(archive, manifest)
                    self._extract_verified(io.BytesIO(archive), snapshot, stage, deadline)
                    result = _prepare(snapshot, prepare)
                    _remaining(deadline)
                    _fsync_directory(stage)
                    target = self.namespace / "generations" / snapshot.archive_sha256
                    if target.exists() or target.is_symlink():
                        _directory(target)  # Never replace a symlink/foreign path.
                        # A verified download repairs corrupt bytes under the same
                        # immutable identity. Keep the old directory until commit;
                        # a crash at either rename still permits previous fallback.
                        damaged = self.namespace / (".stage-" + os.urandom(12).hex())
                        os.rename(target, damaged)
                    os.rename(stage, target)
                    _fsync_directory(target.parent)
                    self._commit_state(state, old, deadline)
                    try:
                        self._gc()
                    except (OSError, LoaderError, SnapshotError):
                        # Activation already succeeded. Leave garbage accounted
                        # in the volume budget for the next pre-attempt cleanup.
                        pass
                    return result
                finally:
                    if stage.exists():
                        self._remove_owned(stage)

    def _run(self, mode, prepare, stop=None, *, current_archive=None):
        deadline = time.monotonic() + self._attempt_seconds
        stop = stop if stop is not None else threading.Event()
        parent, child = socket.socketpair()
        process = multiprocessing.get_context("spawn").Process(
            target=_worker, args=(self, mode, prepare, deadline, child, current_archive),
            name="v8std-snapshot-worker", daemon=True)
        started = False
        try:
            if stop.is_set():
                raise LoaderError("closed")
            try:
                process.start()
                started = True
            except Exception:
                raise LoaderError("prepare_failed") from None
            child.close()
            parent.setblocking(False)
            payload = bytearray()
            length = None
            while length is None or len(payload) < length:
                if stop.is_set():
                    raise LoaderError("closed")
                remaining = _remaining(deadline)
                if not select.select([parent], [], [], min(.025, remaining))[0]:
                    continue
                chunk = parent.recv(_CHUNK if length is not None else 8 - len(payload))
                if not chunk:
                    raise LoaderError("worker_failed")
                payload.extend(chunk)
                if length is None and len(payload) == 8:
                    length = struct.unpack("!Q", payload)[0]
                    payload.clear()
            process.join(min(.1, _remaining(deadline)))
            # Local trusted IPC only. No filesystem or HTTP bytes reach loads.
            kind, result, metadata = pickle.loads(payload)
            _remaining(deadline)
            if kind == "format_error":
                raise SnapshotError(result)
            if kind == "loader_error":
                raise LoaderError(result)
            return result, metadata
        finally:
            parent.close()
            child.close()
            if started:
                if process.is_alive():
                    process.terminate()
                    process.join(.3)
                if process.is_alive():
                    process.kill()
                    process.join(.3)
                if not process.is_alive():
                    process.join()
                    process.close()


def _cache_walk_error():
    raise LoaderError("cache_io")


def _worker(store, mode, prepare, deadline, channel, current_archive):
    try:
        if mode == "cached":
            snapshot = store.cached()
            payload = _prepare(snapshot, prepare) if snapshot else pickle.dumps(("ok", None, None))
        else:
            payload = store._refresh(prepare, deadline, current_archive=current_archive)
        _remaining(deadline)
    except SnapshotError as error:
        payload = pickle.dumps(("format_error", error.code, None))
    except LoaderError as error:
        payload = pickle.dumps(("loader_error", error.code, None))
    except OSError:
        payload = pickle.dumps(("loader_error", "cache_io", None))
    except Exception:
        payload = pickle.dumps(("loader_error", "worker_failed", None))
    try:
        channel.settimeout(max(.001, deadline - time.monotonic()))
        channel.sendall(struct.pack("!Q", len(payload)))
        channel.sendall(payload)
    except OSError:
        pass
    finally:
        channel.close()


class SnapshotCoordinator:
    def __init__(self, store: SnapshotStore, build, *, refresh_seconds: int = 3600):
        if type(refresh_seconds) is not int or refresh_seconds < 0:
            raise LoaderError("configuration")
        self.store = store
        self.build = build
        self.refresh_seconds = refresh_seconds
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._current = None
        self._archive_sha256 = None
        self._state = {"ready": False, "corpus_id": None, "loaded_at": None,
                       "last_checked_at": None, "last_success_at": None,
                       "refresh_error_code": None}

    def start(self) -> None:
        with self._lock:
            if self._stop.is_set():
                raise LoaderError("closed")
            if self._thread is None:
                self._thread = threading.Thread(target=self._loop, name="v8std-snapshot-supervisor", daemon=True)
                self._thread.start()

    def current(self):
        with self._lock:
            if not self._state["ready"]:
                raise LoaderError("INDEX_NOT_READY")
            return self._current

    def status(self) -> dict:
        with self._lock:
            return dict(self._state)

    def _accept(self, result, metadata, *, checked):
        now = time.time()
        retired = None
        with self._lock:
            if metadata.get("unchanged") and (not self._state["ready"]
                    or metadata["archive_sha256"] != self._archive_sha256
                    or metadata["corpus_id"] != self._state["corpus_id"]):
                raise LoaderError("worker_failed")
            if metadata["archive_sha256"] != self._archive_sha256:
                retired = self._current
                self._current = result
                self._archive_sha256 = metadata["archive_sha256"]
                self._state.update(ready=True, corpus_id=metadata["corpus_id"], loaded_at=now)
            if checked:
                self._state.update(last_checked_at=now, last_success_at=now, refresh_error_code=None)
        # Dropping a large generation's final reference can release thousands of
        # objects. Even that CPU work belongs outside the query state lock.
        del retired

    def _delay(self, failures):
        if failures:
            base = min(3600, 30 * 2 ** min(failures - 1, 7))
            return min(3600, max(30, base * random.uniform(.8, 1.2)))
        return self.refresh_seconds * random.uniform(.8, 1.2)

    def _loop(self):
        try:
            result, metadata = self.store._run("cached", self.build, self._stop)
            if metadata:
                self._accept(result, metadata, checked=False)
            del result  # The active reference owns the accepted bootstrap result.
        except (LoaderError, SnapshotError):
            pass
        failures = 0
        while not self._stop.is_set():
            try:
                with self._lock:
                    current_archive = self._archive_sha256 if self._state["ready"] else None
                result, metadata = self.store._run("refresh", self.build, self._stop,
                                                   current_archive=current_archive)
                if self._stop.is_set():
                    return
                self._accept(result, metadata, checked=True)
                # Same-hash candidates are not adopted. Drop the loop's reference
                # outside the query lock, before sleeping for a refresh interval.
                del result
                failures = 0
            except (LoaderError, SnapshotError) as error:
                if self._stop.is_set():
                    return
                failures += 1
                with self._lock:
                    self._state.update(last_checked_at=time.time(), refresh_error_code=error.code)
            if self.refresh_seconds == 0 and self.status()["ready"]:
                return
            if self._stop.wait(self._delay(failures)):
                return

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(1.5)
            if thread.is_alive():
                raise LoaderError("worker_failed")
