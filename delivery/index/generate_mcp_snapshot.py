#!/usr/bin/env python3
"""Build and atomically publish an immutable MCP corpus from existing docs outputs."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
from pathlib import Path
import tempfile

from runtime.v8std_mcp_presentation import PresentationError, validate_links

from runtime.v8std_mcp_snapshot_format import (
    DEFAULT_SITE_URL, JSONL_MEMBERS, MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES,
    MAX_UNPACKED_BYTES, MEMBER_LIMITS, MEMBERS, PUBLIC_DELIVERY_URL,
    SnapshotError, VECTOR_DIM, VECTOR_MODEL, canonical_json, jsonl_rows,
    normalize_site_url, portable_page, sha256, tar_header, validate_manifest, verify_archive,
)


def _read(path: Path, maximum: int) -> bytes:
    try:
        with path.open("rb") as stream:
            payload = stream.read(maximum + 1)
    except OSError:
        raise SnapshotError("source_io") from None
    if len(payload) > maximum:
        raise SnapshotError("member_size")
    return payload


def build_snapshot(docs_dir: Path, source_sha: str, canonical_site_url: str) -> tuple[bytes, dict]:
    site_url = normalize_site_url(canonical_site_url)
    docs_dir = Path(docs_dir)
    files = {
        name: _read(docs_dir / ("ai" if name in JSONL_MEMBERS else "") / name, MEMBER_LIMITS[name])
        for name in MEMBERS[1:]
    }
    pages = bytearray()
    page_count = 0
    for page in jsonl_rows(files["pages.jsonl"]):
        row = portable_page(page, site_url)
        pages.extend(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
        if len(pages) > MEMBER_LIMITS["pages.jsonl"]:
            raise SnapshotError("member_size")
        page_count += 1
    files["pages.jsonl"] = bytes(pages)
    rows = list(jsonl_rows(files["pages.jsonl"]))
    page_paths = {row["id"]: row for row in rows}
    for row in rows:
        validate_links(row.get("body_markdown", ""), canonical_site_url=site_url,
                       page_paths=page_paths, context=site_url + row["site_path"])
    for name in ("llms.txt", "llms-full.txt"):
        validate_links(files[name].decode("utf-8"), canonical_site_url=site_url,
                       page_paths=page_paths, generated_fields=True)
    vector_count = sum(1 for _ in jsonl_rows(files["search-vectors.jsonl"]))
    counts = dict(zip(JSONL_MEMBERS, (page_count, vector_count)))
    descriptor = {
        "schema_version": 1, "source_sha": source_sha, "canonical_site_url": site_url,
        "vector_model": VECTOR_MODEL, "vector_dim": VECTOR_DIM,
        "files": {
            name: {"sha256": sha256(payload), "bytes": len(payload),
                   **({"rows": counts[name]} if name in counts else {})}
            for name, payload in files.items()
        },
    }
    metadata = {**descriptor, "corpus_id": sha256(canonical_json(descriptor))}
    files = {"metadata.json": canonical_json(metadata), **files}
    if len(files["metadata.json"]) > MEMBER_LIMITS["metadata.json"]:
        raise SnapshotError("member_size")
    raw = bytearray()
    for name in MEMBERS:
        payload = files[name]
        raw.extend(tar_header(name, len(payload)))
        raw.extend(payload)
        raw.extend(b"\0" * (-len(payload) % 512))
    raw.extend(b"\0" * 1024)
    raw.extend(b"\0" * (-len(raw) % 10240))
    if len(raw) > MAX_UNPACKED_BYTES:
        raise SnapshotError("archive_unpacked_size")
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0, compresslevel=9) as stream:
        stream.write(raw)
    archive = output.getvalue()
    digest = sha256(archive)
    manifest = {
        "schema_version": 1, "source_sha": source_sha, "corpus_id": metadata["corpus_id"],
        "vector_model": VECTOR_MODEL, "vector_dim": VECTOR_DIM,
        "archive": {"path": digest + "/snapshot.tar.gz", "sha256": digest,
                    "bytes": len(archive), "unpacked_bytes": sum(map(len, files.values()))},
    }
    validate_manifest(canonical_json(manifest))
    verify_archive(archive, manifest)
    return archive, manifest


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_file(path: Path, payload: bytes, *, immutable: bool = False) -> None:
    """Install durable complete bytes. link() is an atomic no-clobber publish."""
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".snapshot-", delete=False) as stream:
            temporary_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
            os.fsync(stream.fileno())
        if immutable:
            os.link(temporary_path, path)
        else:
            os.replace(temporary_path, path)
        _fsync_directory(path.parent)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def publish_snapshot(docs_dir: Path, output_dir: Path, source_sha: str,
                     canonical_site_url: str, *, public_delivery: bool = False) -> Path:
    site_url = normalize_site_url(canonical_site_url)
    if public_delivery and site_url != DEFAULT_SITE_URL:
        raise SnapshotError("archive_path")
    archive, manifest = build_snapshot(docs_dir, source_sha, site_url)
    output_dir = Path(output_dir)
    archive_dir = output_dir / manifest["archive"]["sha256"]
    archive_path = archive_dir / "snapshot.tar.gz"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        if archive_dir.is_symlink():
            raise SnapshotError("immutable_conflict")
        archive_dir.mkdir(exist_ok=True)
        _fsync_directory(output_dir.parent)
        try:
            _atomic_file(archive_path, archive, immutable=True)
        except FileExistsError:
            if archive_path.is_symlink() or not archive_path.is_file():
                raise SnapshotError("immutable_conflict") from None
            existing = _read(archive_path, MAX_ARCHIVE_BYTES)
            if existing != archive:
                raise SnapshotError("immutable_conflict") from None
            verify_archive(existing, manifest)
        # Persist the directory entry before publishing a reference to it.
        _fsync_directory(archive_dir)
        _fsync_directory(output_dir)
        if public_delivery:
            manifest["archive"]["path"] = PUBLIC_DELIVERY_URL + manifest["archive"]["path"]
        encoded_manifest = canonical_json(manifest)
        validate_manifest(encoded_manifest)
        if len(encoded_manifest) > MAX_MANIFEST_BYTES:
            raise SnapshotError("manifest_size")
        manifest_path = output_dir / "manifest.json"
        _atomic_file(manifest_path, encoded_manifest + b"\n")
        return manifest_path
    except OSError:
        raise SnapshotError("publish_io") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, required=True,
                        help="Manifest directory; immutable hash directories are created below it.")
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--site-url", default=None)
    parser.add_argument("--public-delivery", action="store_true")
    args = parser.parse_args()
    site_url = args.site_url if args.site_url is not None else os.environ.get("V8STD_MCP_SITE_URL", DEFAULT_SITE_URL)
    try:
        path = publish_snapshot(args.docs, args.output, args.source_sha, site_url,
                                public_delivery=args.public_delivery)
    except (SnapshotError, PresentationError) as error:
        parser.exit(1, f"{error.code}\n")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
