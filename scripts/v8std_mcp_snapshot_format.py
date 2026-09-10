"""Bounded, stdlib-only validation for MCP_CORPUS_SNAPSHOT@1.0.

No filesystem extraction or network access occurs here. The cache loader owns
private staging and the trust decision for the selected site's archive URL.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import io
import ipaddress
import json
import math
import re
import struct
import tarfile
from urllib.parse import quote, unquote, urlsplit
import zlib

from v8std_mcp_chunks import page_chunks


DEFAULT_SITE_URL = "https://v8std.ru/"
PUBLIC_DELIVERY_URL = "https://ai.v8std.ru/indexes/v1/"
VECTOR_MODEL = "v8std-hash-embeddings-v1"
VECTOR_DIM = 256
MAX_MANIFEST_BYTES = 64 * 1024
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_UNPACKED_BYTES = 64 * 1024 * 1024
MAX_JSONL_LINE_BYTES = 1024 * 1024
MAX_JSONL_ROWS = 100_000
MAX_JSON_DEPTH = 32
MEMBER_LIMITS = {
    "metadata.json": 64 * 1024,
    "pages.jsonl": 16 * 1024 * 1024,
    "search-vectors.jsonl": 32 * 1024 * 1024,
    "llms.txt": 4 * 1024 * 1024,
    "llms-full.txt": 16 * 1024 * 1024,
}
MEMBERS = tuple(MEMBER_LIMITS)
JSONL_MEMBERS = ("pages.jsonl", "search-vectors.jsonl")
_READ_BYTES = 64 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SOURCE_SHA = re.compile(r"[0-9a-f]{40}\Z")
_ERROR_CODES = frozenset({
    "snapshot_invalid", "site_url", "manifest_schema", "manifest_size", "archive_path",
    "archive_size", "archive_hash", "archive_unpacked_size", "archive_gzip",
    "archive_member", "archive_header", "archive_padding", "member_size", "member_hash",
    "metadata_schema", "metadata_hash", "metadata_mismatch", "json_encoding", "json_syntax",
    "json_duplicate_key", "json_depth", "json_type", "json_number", "jsonl_line_size",
    "jsonl_rows", "page_schema", "page_id", "page_path", "vector_schema", "vector_identity",
    "vector_data", "vector_text_hash", "corpus_empty", "source_io", "publish_io",
    "immutable_conflict",
})


class SnapshotError(ValueError):
    """An error safe to put in status/logs; never embeds input data or paths."""

    def __init__(self, code: str):
        self.code = code if code in _ERROR_CODES else "snapshot_invalid"
        super().__init__(self.code)


@dataclass(frozen=True)
class VerifiedSnapshot:
    metadata: dict
    files: dict[str, bytes]
    archive_sha256: str


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SnapshotError(code)


def _path(value: str, *, absolute: bool, code: str) -> str:
    _require(isinstance(value, str), code)
    _require(not re.search(r"[\x00-\x20\x7f\\?#:]", value), code)
    _require(not re.search(r"%(?![0-9a-fA-F]{2})|%(?:2f|5c|25)", value, re.I), code)
    try:
        decoded = unquote(value, encoding="utf-8", errors="strict")
        decoded.encode("utf-8")
    except UnicodeError:
        raise SnapshotError(code) from None
    _require(not re.search(r"[\x00-\x20\x7f\\?#:]", decoded), code)
    _require("//" not in decoded and not any(p in {".", ".."} for p in decoded.split("/")), code)
    _require(not value or value.startswith("/") == absolute, code)
    # Decode/encode once to give percent-encoded Unicode and unreserved bytes a
    # single spelling, without allowing encoded separators or double decoding.
    return quote(decoded, safe="/!$&'()*+,;=@-._~")


def _url(value: str, code: str) -> tuple[str, str, str]:
    _require(isinstance(value, str) and bool(value), code)
    _require(not re.search(r"[\x00-\x20\x7f\\?#]", value), code)
    try:
        parts = urlsplit(value)
        _require(parts.scheme.lower() in {"https", "http"}, code)
        _require(bool(parts.netloc) and "@" not in parts.netloc, code)
        host = parts.hostname
        _require(bool(host) and "%" not in host, code)
        if ":" in host:
            host = "[" + ipaddress.IPv6Address(host).compressed + "]"
        else:
            host = host.encode("idna").decode("ascii").lower()
            _require(bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host)), code)
            _require(all(label and len(label) <= 63 and not label.startswith("-")
                         and not label.endswith("-") for label in host.split(".")), code)
        port = parts.port
        _require(port is None or 0 < port <= 65535, code)
        _require(not parts.netloc.endswith(":"), code)
        scheme = parts.scheme.lower()
        authority = host
        if port is not None and port != {"http": 80, "https": 443}[scheme]:
            authority += f":{port}"
        return scheme, authority, _path(parts.path or "/", absolute=True, code=code)
    except (ValueError, UnicodeError):
        raise SnapshotError(code) from None


def normalize_site_url(value: str) -> str:
    _require(isinstance(value, str), "site_url")
    scheme, host, path = _url(value.strip(), "site_url")
    return f"{scheme}://{host}{path.rstrip('/')}/"


def canonical_page_path(value: str, canonical_site_url: str) -> str:
    """Return a validated relative path, retaining the canonical site's prefix."""
    scheme, host, path = _url(value, "page_path")
    base_scheme, base_host, base_path = _url(canonical_site_url, "page_path")
    _require((scheme, host) == (base_scheme, base_host) and path.startswith(base_path), "page_path")
    return _path(path[len(base_path):], absolute=False, code="page_path")


def _check_tree(value, *, no_floats: bool = False, level: int = 0) -> None:
    if isinstance(value, (dict, list)):
        _require(level < MAX_JSON_DEPTH, "json_depth")
        if isinstance(value, list):
            _require(len(value) <= MAX_JSONL_ROWS, "json_type")
            children = value
        else:
            _require(all(isinstance(key, str) for key in value), "json_type")
            children = [*value.keys(), *value.values()]
        for child in children:
            _check_tree(child, no_floats=no_floats, level=level + 1)
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise SnapshotError("json_encoding") from None
    elif type(value) is float:
        _require(not no_floats and math.isfinite(value), "json_number")
    else:
        _require(value is None or type(value) in {int, bool}, "json_type")


def canonical_json(value: dict) -> bytes:
    """Descriptor encoding; floats, including floats in unknown fields, fail."""
    _check_tree(value, no_floats=True)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError):
        raise SnapshotError("json_type") from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "json_duplicate_key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise SnapshotError("json_number")


def strict_json(payload: bytes) -> dict:
    """Check nesting before json.loads can construct a deeply nested tree."""
    _require(isinstance(payload, bytes), "json_type")
    try:
        text = payload.decode("utf-8")
    except UnicodeError:
        raise SnapshotError("json_encoding") from None
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            _require(depth <= MAX_JSON_DEPTH, "json_depth")
        elif char in "]}":
            depth -= 1
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except SnapshotError:
        raise
    except (ValueError, RecursionError):
        raise SnapshotError("json_syntax") from None
    _require(isinstance(value, dict), "json_type")
    _check_tree(value)
    return value


def _integer(value, minimum: int, maximum: int, code: str) -> None:
    _require(type(value) is int and minimum <= value <= maximum, code)


def _hash(value, code: str) -> None:
    _require(isinstance(value, str) and bool(_SHA256.fullmatch(value)), code)


def _schema(value: dict, code: str) -> None:
    _integer(value.get("schema_version"), 1, 1, code)
    _integer(value.get("vector_dim"), VECTOR_DIM, VECTOR_DIM, code)
    _require(value.get("vector_model") == VECTOR_MODEL, code)
    source = value.get("source_sha")
    _require(isinstance(source, str) and bool(_SOURCE_SHA.fullmatch(source)), code)
    _hash(value.get("corpus_id"), code)


def _manifest(manifest: dict) -> dict:
    _require(isinstance(manifest, dict), "manifest_schema")
    _check_tree(manifest)
    # verify_archive is also a public entry point: a dict passed directly must
    # not bypass the byte limit enforced when reading manifest JSON from bytes.
    try:
        encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError):
        raise SnapshotError("json_number") from None
    _require(len(encoded) <= MAX_MANIFEST_BYTES, "manifest_size")
    _schema(manifest, "manifest_schema")
    archive = manifest.get("archive")
    _require(isinstance(archive, dict), "manifest_schema")
    _hash(archive.get("sha256"), "manifest_schema")
    _integer(archive.get("bytes"), 1, MAX_ARCHIVE_BYTES, "archive_size")
    _integer(archive.get("unpacked_bytes"), 1, MAX_UNPACKED_BYTES, "archive_unpacked_size")
    relative = archive["sha256"] + "/snapshot.tar.gz"
    _require(archive.get("path") in (relative, PUBLIC_DELIVERY_URL + relative), "archive_path")
    return manifest


def validate_manifest(payload: bytes) -> dict:
    _require(isinstance(payload, bytes), "manifest_schema")
    _require(len(payload) <= MAX_MANIFEST_BYTES, "manifest_size")
    return _manifest(strict_json(payload))


def jsonl_rows(payload: bytes):
    """Yield validated objects, checking every line (including whitespace)."""
    count = 0
    # BytesIO.readline avoids allocating a list containing every raw line.
    stream = io.BytesIO(payload)
    while line := stream.readline(MAX_JSONL_LINE_BYTES + 2):
        content = line.removesuffix(b"\n")
        _require(len(content) <= MAX_JSONL_LINE_BYTES, "jsonl_line_size")
        if not content.strip(b" \t\r"):
            continue
        count += 1
        _require(count <= MAX_JSONL_ROWS, "jsonl_rows")
        yield strict_json(content)


def _gunzip(payload: bytes) -> bytearray:
    _require(payload[:8] == b"\x1f\x8b\x08\x00\x00\x00\x00\x00", "archive_gzip")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    unpacked = bytearray()
    try:
        for offset in range(0, len(payload), _READ_BYTES):
            chunk = payload[offset:offset + _READ_BYTES]
            while chunk:
                block = decoder.decompress(chunk, min(_READ_BYTES, MAX_UNPACKED_BYTES - len(unpacked) + 1))
                unpacked.extend(block)
                _require(len(unpacked) <= MAX_UNPACKED_BYTES, "archive_unpacked_size")
                chunk = decoder.unconsumed_tail
                if decoder.eof:
                    _require(not decoder.unused_data and offset + _READ_BYTES >= len(payload), "archive_gzip")
                    break
        _require(decoder.eof, "archive_gzip")
    except zlib.error:
        raise SnapshotError("archive_gzip") from None
    return unpacked


def tar_header(name: str, size: int) -> bytes:
    """The producer and verifier share one exact USTAR header definition."""
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o644
    info.uid = info.gid = info.mtime = 0
    info.uname = info.gname = ""
    return info.tobuf(format=tarfile.USTAR_FORMAT, encoding="ascii", errors="strict")


def _tar_files(raw: bytearray) -> dict[str, bytes]:
    files = {}
    offset = 0
    for name in MEMBERS:
        header = bytes(raw[offset:offset + 512])
        _require(len(header) == 512 and any(header), "archive_member")
        # Check raw fields before tarfile can hide extensions or combine prefix/name.
        _require(header[:100].split(b"\0", 1)[0] == name.encode("ascii")
                 and header[156:157] == tarfile.REGTYPE, "archive_member")
        try:
            info = tarfile.TarInfo.frombuf(header, encoding="ascii", errors="strict")
        except (tarfile.HeaderError, ValueError, UnicodeError):
            raise SnapshotError("archive_header") from None
        _integer(info.size, 0, MEMBER_LIMITS[name], "member_size")
        _require(header == tar_header(name, info.size), "archive_header")
        start = offset + 512
        end = start + info.size
        offset = end + (-info.size % 512)
        _require(offset <= len(raw), "archive_member")
        _require(not any(raw[end:offset]), "archive_padding")
        files[name] = bytes(raw[start:end])
    _require(len(raw) - offset >= 1024 and len(raw) % 512 == 0, "archive_member")
    _require(not any(raw[offset:]), "archive_member")
    return files


def _string(value, code: str, *, nonempty: bool = False) -> None:
    _require(isinstance(value, str) and (not nonempty or bool(value.strip())), code)


def _page_schema(page: dict) -> None:
    _string(page.get("id"), "page_id", nonempty=True)
    for key in ("title", "description", "body_markdown", "type", "source_path"):
        if key in page:
            _string(page[key], "page_schema")
    for key in ("aliases", "source_urls"):
        values = page.get(key, [])
        _require(isinstance(values, list), "page_schema")
        for value in values:
            _string(value, "page_schema")
    related = page.get("related", [])
    _require(isinstance(related, list), "page_schema")
    for entry in related:
        _require(isinstance(entry, dict), "page_schema")
        _string(entry.get("id"), "page_schema", nonempty=True)
        for key in ("title", "type", "relation", "url", "markdown_url", "source_path"):
            if key in entry:
                _string(entry[key], "page_schema")
    if "source_path" in page:
        _path(page["source_path"], absolute=False, code="page_path")


def portable_page(page: dict, canonical_site_url: str) -> dict:
    """Add only presentation paths; retain the exact canonical retrieval fields."""
    _page_schema(page)
    paths = {
        "site_path": canonical_page_path(page.get("url"), canonical_site_url),
        "markdown_path": canonical_page_path(page.get("markdown_url"), canonical_site_url),
    }
    for key, expected in paths.items():
        if key in page:
            _require(page[key] == expected, "page_path")
    return {**page, **paths}


def _semantics(files: dict[str, bytes], site_url: str) -> dict[str, int]:
    ids = set()
    expected = {}
    for page in jsonl_rows(files["pages.jsonl"]):
        portable = portable_page(page, site_url)
        _require(all(key in page and page[key] == portable[key]
                     for key in ("site_path", "markdown_path")), "page_path")
        _require(page["id"] not in ids, "page_id")
        ids.add(page["id"])
        for field, index, text in page_chunks(page):
            expected[page["id"], field, index] = sha256(text.encode("utf-8"))
            _require(len(expected) <= MAX_JSONL_ROWS, "jsonl_rows")
    _require(bool(ids), "corpus_empty")
    count = 0
    for row in jsonl_rows(files["search-vectors.jsonl"]):
        _string(row.get("id"), "vector_schema", nonempty=True)
        _string(row.get("field"), "vector_schema")
        _integer(row.get("chunk_index"), 0, MAX_JSONL_ROWS - 1, "vector_schema")
        _integer(row.get("dim"), VECTOR_DIM, VECTOR_DIM, "vector_schema")
        _require(row.get("model") == VECTOR_MODEL, "vector_schema")
        identity = row["id"], row["field"], row["chunk_index"]
        # Removing matched identities detects duplicates, missing chunks, and
        # dangling rows with the same rule; no partially valid vectors survive.
        _require(identity in expected, "vector_identity")
        _hash(row.get("text_sha256"), "vector_text_hash")
        _require(row["text_sha256"] == expected.pop(identity), "vector_text_hash")
        encoded = row.get("vector_base64")
        _require(isinstance(encoded, str) and len(encoded) == 1368, "vector_data")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise SnapshotError("vector_data") from None
        _require(len(decoded) == 4 * VECTOR_DIM
                 and base64.b64encode(decoded).decode("ascii") == encoded, "vector_data")
        _require(all(math.isfinite(value) for value in struct.unpack("<256f", decoded)), "vector_data")
        count += 1
    _require(count > 0, "corpus_empty")
    _require(not expected, "vector_identity")
    return {"pages.jsonl": len(ids), "search-vectors.jsonl": count}


def _metadata(files: dict[str, bytes], manifest: dict) -> dict:
    metadata = strict_json(files["metadata.json"])
    _schema(metadata, "metadata_schema")
    descriptor = {key: value for key, value in metadata.items() if key != "corpus_id"}
    _require(sha256(canonical_json(descriptor)) == metadata["corpus_id"], "metadata_hash")
    for key in ("schema_version", "source_sha", "corpus_id", "vector_model", "vector_dim"):
        _require(metadata[key] == manifest[key], "metadata_mismatch")
    site_url = metadata.get("canonical_site_url")
    _require(normalize_site_url(site_url) == site_url, "metadata_schema")
    entries = metadata.get("files")
    _require(isinstance(entries, dict) and set(entries) == set(MEMBERS[1:]), "metadata_schema")
    for name, entry in entries.items():
        _require(isinstance(entry, dict), "metadata_schema")
        _integer(entry.get("bytes"), 0, MEMBER_LIMITS[name], "member_size")
        _hash(entry.get("sha256"), "metadata_schema")
        _require(len(files[name]) == entry["bytes"], "member_size")
        _require(sha256(files[name]) == entry["sha256"], "member_hash")
        if name in JSONL_MEMBERS:
            _integer(entry.get("rows"), 1, MAX_JSONL_ROWS, "jsonl_rows")
        else:
            try:
                files[name].decode("utf-8")
            except UnicodeError:
                raise SnapshotError("json_encoding") from None
    counts = _semantics(files, site_url)
    for name, count in counts.items():
        _require(count == entries[name]["rows"], "jsonl_rows")
    return metadata


def verify_archive(payload: bytes, manifest: dict) -> VerifiedSnapshot:
    """Verify exact compressed bytes, framing, descriptors and complete semantics."""
    _manifest(manifest)
    _require(isinstance(payload, bytes), "archive_size")
    _require(len(payload) <= MAX_ARCHIVE_BYTES
             and len(payload) == manifest["archive"]["bytes"], "archive_size")
    digest = sha256(payload)
    _require(digest == manifest["archive"]["sha256"], "archive_hash")
    files = _tar_files(_gunzip(payload))
    _require(sum(map(len, files.values())) == manifest["archive"]["unpacked_bytes"], "archive_unpacked_size")
    metadata = _metadata(files, manifest)
    return VerifiedSnapshot(metadata=metadata, files=files, archive_sha256=digest)
