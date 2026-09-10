import base64
import copy
import gzip
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tests import mcp_snapshot_fixtures as fixture


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class SnapshotFormatTests(unittest.TestCase):
    def modules(self):
        self.assertIsNotNone(importlib.util.find_spec("generate_mcp_snapshot"))
        return (importlib.import_module("v8std_mcp_snapshot_format"),
                importlib.import_module("generate_mcp_snapshot"))

    def verify_rejected(self, archive, manifest, code=None):
        fmt, _ = self.modules()
        with self.assertRaises(fmt.SnapshotError) as caught:
            fmt.verify_archive(archive, manifest)
        self.assertRegex(caught.exception.code, r"^[a-z_]{1,64}$")
        self.assertEqual(str(caught.exception), caught.exception.code)
        if code:
            self.assertEqual(caught.exception.code, code)

    def test_00_producer_exists_and_rebuilds_identical_archive(self):
        # This assertion must run before any production module import in RED.
        self.assertIsNotNone(importlib.util.find_spec("generate_mcp_snapshot"))
        fmt, producer = self.modules()
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory)
            original = fixture.write_docs(docs)
            first, manifest = producer.build_snapshot(docs, fixture.SOURCE_SHA, fixture.SITE_URL)
            second, again = producer.build_snapshot(docs, fixture.SOURCE_SHA, fixture.SITE_URL)
            self.assertEqual(first, second)
            self.assertEqual(manifest, again)
            verified = fmt.verify_archive(first, fmt.validate_manifest(fixture.json_bytes(manifest)))
            page = json.loads(verified.files["pages.jsonl"])
            self.assertEqual(page["site_path"], "std/437/")
            self.assertEqual(page["markdown_path"], "std/437.md")
            self.assertEqual(verified.metadata["vector_dim"], 256)
            self.assertEqual(page["body_markdown"], fixture.BODY)
            for name in ("search-vectors.jsonl", "llms.txt", "llms-full.txt"):
                self.assertEqual(verified.files[name], original[name])
            self.assertEqual((docs / "ai/pages.jsonl").read_bytes(), original["pages.jsonl"])

    def test_independent_fixture_and_descriptor_hash(self):
        fmt, _ = self.modules()
        archive, manifest = fixture.snapshot_fixture()
        verified = fmt.verify_archive(archive, manifest)
        descriptor = dict(verified.metadata)
        corpus_id = descriptor.pop("corpus_id")
        self.assertEqual(corpus_id, fixture.sha256(fixture.json_bytes(descriptor)))
        self.assertEqual(verified.archive_sha256, fixture.sha256(archive))
        self.assertNotEqual(corpus_id, verified.archive_sha256)
        self.assertEqual(tuple(verified.files), fixture.MEMBERS)

    def test_tar_gzip_metadata_is_exact_and_deterministic(self):
        _, producer = self.modules()
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory)
            fixture.write_docs(docs)
            archive, manifest = producer.build_snapshot(docs, fixture.SOURCE_SHA, fixture.SITE_URL)
        self.assertEqual(archive[:10], b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff")
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            members = tar.getmembers()
            self.assertEqual([m.name for m in members], list(fixture.MEMBERS))
            for member in members:
                self.assertEqual((member.uid, member.gid, member.mode, member.mtime), (0, 0, 0o644, 0))
                self.assertEqual((member.uname, member.gname), ("", ""))
                self.assertEqual(member.type, tarfile.REGTYPE)
                self.assertEqual(member.pax_headers, {})
            self.assertEqual(sum(m.size for m in members), manifest["archive"]["unpacked_bytes"])

    def test_normalized_site_url_and_prefix(self):
        fmt, producer = self.modules()
        for given, expected in [
            (" HTTPS://V8STD.RU:443/knowledge ", "https://v8std.ru/knowledge/"),
            ("http://LOCALHOST:80/base/", "http://localhost/base/"),
            ("http://[::1]:8080/base", "http://[::1]:8080/base/"),
            ("https://example.org", "https://example.org/"),
        ]:
            with self.subTest(given=given):
                self.assertEqual(fmt.normalize_site_url(given), expected)
                self.assertEqual(fmt.normalize_site_url(expected), expected)
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory)
            fixture.write_docs(docs, site_url="https://example.org/knowledge/")
            archive, manifest = producer.build_snapshot(docs, fixture.SOURCE_SHA,
                                                        "HTTPS://EXAMPLE.ORG:443/knowledge")
            page = json.loads(fmt.verify_archive(archive, manifest).files["pages.jsonl"])
            self.assertEqual(page["site_path"], "std/437/")
            self.assertEqual(page["markdown_path"], "std/437.md")

    def test_site_url_rejects_ambiguous_or_credentialed_inputs(self):
        fmt, _ = self.modules()
        for value in ["", " ", None, 1, "ftp://host/", "//host/base", "https://user:secret@host/",
                      "https://host/?", "https://host/#", "https://host/a/../b", "https://host/./",
                      "https://host/%2e%2e/", "https://host/a%2fb/", "https://host/%5c/",
                      "https://host/%252e%252e/", "https://host/a\\b", "https://host//base/",
                      "https://ho\nst/", "https://host:abc/", "https://host:65536/",
                      "https://host/%", "https://host/%00/", "https://host/a b/"]:
            with self.subTest(value=value), self.assertRaisesRegex(fmt.SnapshotError, "site_url"):
                fmt.normalize_site_url(value)

    def test_manifest_schema_types_hashes_and_path(self):
        fmt, _ = self.modules()
        _, manifest = fixture.snapshot_fixture()
        variants = []
        for key, value in [("schema_version", True), ("schema_version", 2), ("source_sha", "abc"),
                           ("corpus_id", "A" * 64), ("vector_dim", 128), ("vector_dim", 256.0),
                           ("vector_model", "other")]:
            variants.append({**manifest, key: value})
        for key, value in [("bytes", True), ("bytes", -1), ("unpacked_bytes", "32"),
                           ("sha256", "g" * 64), ("path", "../snapshot.tar.gz"),
                           ("path", "//evil.test/snapshot.tar.gz"), ("path", "https://evil.test/a"),
                           ("path", "0" * 64 + "/snapshot.tar.gz")]:
            variants.append({**manifest, "archive": {**manifest["archive"], key: value}})
        for value in variants + [[], None, {k: v for k, v in manifest.items() if k != "archive"}]:
            with self.subTest(value=value), self.assertRaises(fmt.SnapshotError):
                fmt.validate_manifest(fixture.json_bytes(value))
        optional = {**manifest, "future_optional": {"enabled": True, "weight": 0.5}}
        self.assertEqual(fmt.validate_manifest(fixture.json_bytes(optional))["corpus_id"], manifest["corpus_id"])

    def test_direct_verifier_cannot_bypass_manifest_byte_budget(self):
        archive, manifest = fixture.snapshot_fixture()
        self.verify_rejected(archive, {**manifest, "future_optional": "x" * (64 * 1024)}, "manifest_size")

    def test_strict_json_duplicate_keys_depth_utf8_and_numbers(self):
        fmt, _ = self.modules()
        _, manifest = fixture.snapshot_fixture()
        raw = fixture.json_bytes(manifest)
        invalid = [b"\xff", raw[:-1] + b',"schema_version":1}',
                   raw[:-1] + b',"extra":{"x":1,"x":2}}',
                   raw[:-1] + b',"extra":NaN}', raw[:-1] + b',"extra":1e9999}',
                   raw[:-1] + b',"extra":"\\ud800"}',
                   raw[:-1] + b',"extra":' + b"[" * 32 + b"0" + b"]" * 32 + b"}"]
        for value in invalid:
            with self.subTest(value=value[:40]), self.assertRaises(fmt.SnapshotError):
                fmt.validate_manifest(value)
        valid = raw[:-1] + b',"extra":' + b"[" * 31 + b"0" + b"]" * 31 + b"}"
        fmt.validate_manifest(valid)

    def test_independent_hostile_tar_members(self):
        files = fixture.with_metadata(fixture.corpus_files())
        hostile = []
        for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE,
                     tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE,
                     tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME,
                     tarfile.GNUTYPE_SPARSE]:
            info = tarfile.TarInfo("metadata.json")
            info.type = kind
            info.linkname = "secret"
            hostile.append([(info, b""), *fixture.MEMBERS[1:]])
        for name in ["../metadata.json", "/metadata.json", "./metadata.json", "a/../metadata.json"]:
            info = tarfile.TarInfo(name)
            info.size = len(files["metadata.json"])
            hostile.append([(info, files["metadata.json"]), *fixture.MEMBERS[1:]])
        hostile += [list(reversed(fixture.MEMBERS)), list(fixture.MEMBERS[:-1]),
                    [*fixture.MEMBERS, "llms.txt"], ["metadata.json", *fixture.MEMBERS]]
        for members in hostile:
            with self.subTest(members=members):
                archive, manifest = fixture.snapshot_fixture(files=files, members=members)
                self.verify_rejected(archive, manifest, "archive_member")

    def test_gzip_trailing_members_truncation_and_headers(self):
        files = fixture.with_metadata(fixture.corpus_files())
        archive, _ = fixture.snapshot_fixture(files=files)
        raw = fixture.tar_bytes(files)
        for bad in [archive + b"secret", archive + gzip.compress(b""), archive[:-1],
                    fixture.gzip_bytes(raw, filename="untrusted"), fixture.gzip_bytes(raw, mtime=1),
                    archive[:-8] + bytes([archive[-8] ^ 1]) + archive[-7:]]:
            with self.subTest(size=len(bad)):
                self.verify_rejected(bad, fixture.manifest_for(bad, files))

    def test_tar_checksum_padding_and_hidden_trailing_payload(self):
        files = fixture.with_metadata(fixture.corpus_files())
        raw = fixture.tar_bytes(files)
        corrupted = bytearray(raw)
        corrupted[148] ^= 1
        padded = bytearray(raw)
        padded[512 + len(files["metadata.json"])] = 1
        for bad in [bytes(corrupted), bytes(padded), raw + b"secret", raw + raw,
                    raw[:512], raw[:512 + len(files["metadata.json"])]]:
            archive = fixture.gzip_bytes(bad)
            self.verify_rejected(archive, fixture.manifest_for(archive, files))

    def test_extensions_and_noncanonical_tar_header_fields(self):
        files = fixture.with_metadata(fixture.corpus_files())
        for field, value in [("uid", 12), ("gid", 12), ("mode", 0o777), ("mtime", 1),
                             ("uname", "secret"), ("gname", "secret")]:
            info = tarfile.TarInfo("metadata.json")
            info.mode, info.size = 0o644, len(files["metadata.json"])
            setattr(info, field, value)
            self.verify_rejected(*fixture.snapshot_fixture(
                files=files, members=[(info, files["metadata.json"]), *fixture.MEMBERS[1:]]))
        info = tarfile.TarInfo("metadata.json")
        info.mode, info.size = 0o644, len(files["metadata.json"])
        info.pax_headers = {"comment": "hidden extension"}
        self.verify_rejected(*fixture.snapshot_fixture(
            files=files, members=[(info, files["metadata.json"]), *fixture.MEMBERS[1:]],
            tar_format=tarfile.PAX_FORMAT), "archive_member")
        self.verify_rejected(*fixture.snapshot_fixture(files=files, tar_format=tarfile.GNU_FORMAT))

    def test_member_headers_enforce_every_real_limit_before_reading(self):
        fmt, _ = self.modules()
        files = fixture.with_metadata(fixture.corpus_files())
        original = fixture.tar_bytes(files)
        offset = 0
        for name, maximum in fmt.MEMBER_LIMITS.items():
            info = tarfile.TarInfo(name)
            info.mode, info.size = 0o644, maximum + 1
            raw = original[:offset] + info.tobuf(format=tarfile.USTAR_FORMAT) + original[offset + 512:]
            archive = fixture.gzip_bytes(raw)
            self.verify_rejected(archive, fixture.manifest_for(archive, files), "member_size")
            offset += 512 + len(files[name]) + (-len(files[name]) % 512)

    def test_archive_hash_size_and_unpacked_count_are_independent(self):
        archive, manifest = fixture.snapshot_fixture()
        for key, value in [("sha256", "0" * 64), ("bytes", len(archive) + 1),
                           ("unpacked_bytes", manifest["archive"]["unpacked_bytes"] + 1)]:
            bad = copy.deepcopy(manifest)
            bad["archive"][key] = value
            if key == "sha256":
                bad["archive"]["path"] = value + "/snapshot.tar.gz"
            self.verify_rejected(archive, bad)

    def test_metadata_descriptors_counts_and_manifest_agreement(self):
        def bad_size(meta):
            meta["files"]["pages.jsonl"]["bytes"] += 1
        def bad_rows(meta):
            meta["files"]["search-vectors.jsonl"]["rows"] += 1
        def bad_hash(meta):
            meta["files"]["llms.txt"]["sha256"] = "0" * 64
        def missing_file(meta):
            del meta["files"]["llms.txt"]
        for mutate in [bad_size, bad_rows, bad_hash, missing_file,
                       lambda m: m.update(vector_dim=128),
                       lambda m: m.update(schema_version=True),
                       lambda m: m.update(extra=1.5),
                       lambda m: m.update(canonical_site_url="https://v8std.ru/../")]:
            with self.subTest(mutate=mutate):
                files = fixture.with_metadata(fixture.corpus_files(), mutate=mutate)
                self.verify_rejected(*fixture.snapshot_fixture(files=files))
        files = fixture.with_metadata(fixture.corpus_files())
        metadata = json.loads(files["metadata.json"])
        metadata["corpus_id"] = "0" * 64
        files["metadata.json"] = fixture.json_bytes(metadata)
        self.verify_rejected(*fixture.snapshot_fixture(files=files))
        archive, manifest = fixture.snapshot_fixture()
        self.verify_rejected(archive, {**manifest, "source_sha": "2" * 40})

    def test_page_schema_identity_and_portable_path_validation(self):
        page = fixture.page_fixture()
        for key, value in [("id", []), ("title", 4), ("body_markdown", []),
                           ("aliases", "std437"), ("aliases", [None]), ("related", ["bad"]),
                           ("source_urls", [1]), ("site_path", "../437/"),
                           ("site_path", "https://evil.test/"), ("site_path", "std%2f437/"),
                           ("site_path", "std/other/"), ("markdown_path", "/std/437.md"),
                           ("url", "https://evil.test/std/437/")]:
            with self.subTest(key=key, value=value):
                files = fixture.with_metadata(fixture.corpus_files(pages=[{**page, key: value}]))
                self.verify_rejected(*fixture.snapshot_fixture(files=files))
        for pages in [[], [page, page]]:
            files = fixture.with_metadata(fixture.corpus_files(pages=pages))
            self.verify_rejected(*fixture.snapshot_fixture(files=files))

    def test_vector_semantics_include_every_original_chunk(self):
        rows = fixture.vector_fixtures()
        corruptions = [("id", "missing"), ("field", "unknown"), ("chunk_index", True),
                       ("chunk_index", -1), ("chunk_index", 1), ("text_sha256", "0" * 64),
                       ("model", "unsupported"), ("dim", 128), ("dim", 256.0),
                       ("vector_base64", "not base64!"), ("vector_base64", "AA==")]
        for number in [float("nan"), float("inf"), -float("inf")]:
            corruptions.append(("vector_base64", base64.b64encode(
                struct.pack("<256f", number, *([0.0] * 255))).decode()))
        for key, value in corruptions:
            with self.subTest(key=key, value=str(value)[:24]):
                vectors = [{**rows[0], key: value}, rows[1]]
                files = fixture.with_metadata(fixture.corpus_files(vectors=vectors))
                self.verify_rejected(*fixture.snapshot_fixture(files=files))
        for vectors in [[], rows[:1], rows + [rows[0]]]:
            files = fixture.with_metadata(fixture.corpus_files(vectors=vectors))
            self.verify_rejected(*fixture.snapshot_fixture(files=files))

    def test_jsonl_duplicate_keys_invalid_utf8_and_nonobject_rows(self):
        for name in ["pages.jsonl", "search-vectors.jsonl"]:
            for payload in [b"[]\n", b"null\n", b"\xff\n", b'{"id":"a","id":"b"}\n']:
                files = fixture.corpus_files()
                files[name] = payload
                self.verify_rejected(*fixture.snapshot_fixture(files=fixture.with_metadata(files)))

    def test_real_line_row_manifest_and_compressed_limits(self):
        fmt, _ = self.modules()
        archive, manifest = fixture.snapshot_fixture()
        with self.assertRaisesRegex(fmt.SnapshotError, "manifest_size"):
            fmt.validate_manifest(fixture.json_bytes(manifest) + b" " * (64 * 1024))
        too_large = b"x" * (16 * 1024 * 1024 + 1)
        oversized = copy.deepcopy(manifest)
        digest = fixture.sha256(too_large)
        oversized["archive"].update(bytes=len(too_large), sha256=digest, path=digest + "/snapshot.tar.gz")
        self.verify_rejected(too_large, oversized, "archive_size")
        for name in ("pages.jsonl", "search-vectors.jsonl"):
            files = fixture.corpus_files()
            files[name] = b" " * (1024 * 1024 + 1) + b"\n" + files[name]
            self.verify_rejected(*fixture.snapshot_fixture(files=fixture.with_metadata(files)), "jsonl_line_size")
        files = fixture.corpus_files()
        files["search-vectors.jsonl"] = b"{}\n" * 100001
        self.verify_rejected(*fixture.snapshot_fixture(files=fixture.with_metadata(files)), "jsonl_rows")

    def test_chunk_boundaries_match_existing_generator_without_reembedding(self):
        fmt, _ = self.modules()
        generator = importlib.import_module("generate_search_vectors")
        for length in [2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 4400]:
            with self.subTest(length=length):
                page = fixture.page_fixture()
                page["body_markdown"] = "  " + "x" * length + "\n\nя\n\n尾  \n"
                rows = []
                for field, index, text in generator.page_chunks(page):
                    row = dict(fixture.vector_fixtures()[0])
                    row.update(field=field, chunk_index=index, text_sha256=fixture.sha256(text.encode()))
                    rows.append(row)
                archive, manifest = fixture.snapshot_fixture(files=fixture.with_metadata(
                    fixture.corpus_files(pages=[page], vectors=rows)))
                fmt.verify_archive(archive, manifest)

    def test_contract_budget_constants_and_boundary_enforcement(self):
        fmt, _ = self.modules()
        self.assertEqual(fmt.MAX_MANIFEST_BYTES, 64 * 1024)
        self.assertEqual(fmt.MAX_ARCHIVE_BYTES, 16 * 1024 * 1024)
        self.assertEqual(fmt.MAX_UNPACKED_BYTES, 64 * 1024 * 1024)
        self.assertEqual(fmt.MAX_JSONL_LINE_BYTES, 1024 * 1024)
        self.assertEqual(fmt.MAX_JSONL_ROWS, 100000)
        self.assertEqual(fmt.MAX_JSON_DEPTH, 32)
        self.assertEqual(fmt.MEMBER_LIMITS, dict(zip(fixture.MEMBERS,
                         [64 * 1024, 16 * 1024**2, 32 * 1024**2, 4 * 1024**2, 16 * 1024**2])))
        archive, manifest = fixture.snapshot_fixture()
        raw_manifest = fixture.json_bytes(manifest)
        with patch.object(fmt, "MAX_MANIFEST_BYTES", len(raw_manifest)):
            fmt.validate_manifest(raw_manifest)
        with patch.object(fmt, "MAX_MANIFEST_BYTES", len(raw_manifest) - 1):
            with self.assertRaises(fmt.SnapshotError):
                fmt.validate_manifest(raw_manifest)
        with patch.object(fmt, "MAX_ARCHIVE_BYTES", len(archive) - 1):
            self.verify_rejected(archive, manifest)
        files = fixture.with_metadata(fixture.corpus_files())
        for name in fixture.MEMBERS:
            with self.subTest(member=name), patch.dict(fmt.MEMBER_LIMITS, {name: len(files[name]) - 1}):
                self.verify_rejected(archive, manifest)
        with patch.object(fmt, "MAX_JSONL_ROWS", 1):
            self.verify_rejected(archive, manifest)
        with patch.object(fmt, "MAX_JSONL_LINE_BYTES", 20):
            self.verify_rejected(archive, manifest)
        # Files fit, framing does not: the decompression counter must include tar bytes.
        with patch.object(fmt, "MAX_UNPACKED_BYTES", manifest["archive"]["unpacked_bytes"] + 1):
            self.verify_rejected(archive, manifest)

    def test_real_decompressed_budget_includes_zero_tar_framing(self):
        files = fixture.with_metadata(fixture.corpus_files())
        output = io.BytesIO()
        with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as stream:
            stream.write(fixture.tar_bytes(files))
            for _ in range(64):
                stream.write(b"\0" * (1024 * 1024))
        archive = output.getvalue()
        self.verify_rejected(archive, fixture.manifest_for(archive, files), "archive_unpacked_size")

    def test_publish_local_public_atomic_order_and_immutable_reuse(self):
        fmt, producer = self.modules()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs, output = root / "docs", root / "output"
            fixture.write_docs(docs)
            manifest_path = producer.publish_snapshot(docs, output, fixture.SOURCE_SHA, fixture.SITE_URL)
            self.assertEqual(manifest_path, output / "manifest.json")
            manifest = fmt.validate_manifest(manifest_path.read_bytes())
            archive_path = output / manifest["archive"]["path"]
            before = archive_path.stat()
            local_bytes = archive_path.read_bytes()
            producer.publish_snapshot(docs, output, fixture.SOURCE_SHA, fixture.SITE_URL)
            self.assertEqual(archive_path.stat().st_mtime_ns, before.st_mtime_ns)
            public = producer.publish_snapshot(docs, root / "public", fixture.SOURCE_SHA,
                                               fixture.SITE_URL, public_delivery=True)
            public_manifest = fmt.validate_manifest(public.read_bytes())
            self.assertEqual(public_manifest["archive"]["path"],
                             "https://ai.v8std.ru/indexes/v1/" + manifest["archive"]["path"])
            self.assertEqual((public.parent / manifest["archive"]["path"]).read_bytes(), local_bytes)
            previous_manifest = manifest_path.read_bytes()
            archive_path.write_bytes(b"corrupt")
            with self.assertRaises(fmt.SnapshotError):
                producer.publish_snapshot(docs, output, fixture.SOURCE_SHA, fixture.SITE_URL)
            self.assertEqual(archive_path.read_bytes(), b"corrupt")
            self.assertEqual(manifest_path.read_bytes(), previous_manifest)

    def test_manifest_is_replaced_only_after_verified_archive_exists(self):
        fmt, producer = self.modules()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root / "docs")
            original_replace = os.replace
            observed = []
            def inspect_replace(source, target):
                if Path(target).name == "manifest.json":
                    manifest = fmt.validate_manifest(Path(source).read_bytes())
                    archive = (Path(target).parent / manifest["archive"]["path"]).read_bytes()
                    fmt.verify_archive(archive, manifest)
                    observed.append(True)
                return original_replace(source, target)
            with patch.object(producer.os, "replace", side_effect=inspect_replace):
                producer.publish_snapshot(root / "docs", root / "output", fixture.SOURCE_SHA, fixture.SITE_URL)
            self.assertEqual(observed, [True])

    def test_publish_failure_retains_previous_manifest_and_removes_temporary_files(self):
        fmt, producer = self.modules()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root / "docs")
            manifest_path = producer.publish_snapshot(root / "docs", root / "output",
                                                     fixture.SOURCE_SHA, fixture.SITE_URL)
            before = manifest_path.read_bytes()
            for target in ("link", "replace", "fsync"):
                with self.subTest(target=target), patch.object(producer.os, target, side_effect=OSError("secret")):
                    with self.assertRaisesRegex(fmt.SnapshotError, "publish_io") as caught:
                        producer.publish_snapshot(root / "docs", root / "output", "2" * 40, fixture.SITE_URL)
                self.assertNotIn("secret", str(caught.exception))
                self.assertEqual(manifest_path.read_bytes(), before)
                self.assertEqual(list((root / "output").rglob(".snapshot-*")), [])
            old = fmt.validate_manifest(before)
            fmt.verify_archive((root / "output" / old["archive"]["path"]).read_bytes(), old)

    def test_existing_immutable_symlinks_are_rejected(self):
        fmt, producer = self.modules()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root / "docs")
            archive, manifest = producer.build_snapshot(root / "docs", fixture.SOURCE_SHA, fixture.SITE_URL)
            output = root / "output"
            output.mkdir()
            foreign = root / "foreign"
            foreign.mkdir()
            (foreign / "snapshot.tar.gz").write_bytes(archive)
            target = output / manifest["archive"]["sha256"]
            target.symlink_to(foreign, target_is_directory=True)
            with self.assertRaisesRegex(fmt.SnapshotError, "immutable_conflict"):
                producer.publish_snapshot(root / "docs", output, fixture.SOURCE_SHA, fixture.SITE_URL)
            target.unlink()
            target.mkdir()
            (target / "snapshot.tar.gz").symlink_to(foreign / "snapshot.tar.gz")
            with self.assertRaisesRegex(fmt.SnapshotError, "immutable_conflict"):
                producer.publish_snapshot(root / "docs", output, fixture.SOURCE_SHA, fixture.SITE_URL)
            self.assertEqual((foreign / "snapshot.tar.gz").read_bytes(), archive)
            self.assertFalse((output / "manifest.json").exists())

    def test_invalid_source_corpus_cannot_publish_manifest(self):
        fmt, producer = self.modules()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root / "docs")
            (root / "docs/ai/search-vectors.jsonl").write_bytes(fixture.jsonl_bytes(fixture.vector_fixtures()[:1]))
            with self.assertRaises(fmt.SnapshotError):
                producer.publish_snapshot(root / "docs", root / "output", fixture.SOURCE_SHA, fixture.SITE_URL)
            self.assertFalse((root / "output/manifest.json").exists())
            fixture.write_docs(root / "docs", site_url="https://example.test/base/")
            with self.assertRaisesRegex(fmt.SnapshotError, "archive_path"):
                producer.publish_snapshot(root / "docs", root / "output", fixture.SOURCE_SHA,
                                          "https://example.test/base/", public_delivery=True)

    def test_cli_site_precedence_public_delivery_and_explicit_empty_env(self):
        self.modules()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root / "docs")
            command = [sys.executable, "-S", str(ROOT / "scripts/generate_mcp_snapshot.py"),
                       "--docs", str(root / "docs"), "--output", str(root / "output"),
                       "--source-sha", fixture.SOURCE_SHA]
            environment = {**os.environ, "V8STD_MCP_SITE_URL": ""}
            result = subprocess.run(command, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stderr.strip(), "site_url")
            result = subprocess.run(command + ["--site-url", fixture.SITE_URL, "--public-delivery"],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((root / "output/manifest.json").read_bytes())
            self.assertTrue(manifest["archive"]["path"].startswith("https://ai.v8std.ru/indexes/v1/"))

    def test_cli_and_stdlib_only_import(self):
        self.modules()
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "scripts")}
        result = subprocess.run([sys.executable, "-S", "-c",
                                 "import generate_mcp_snapshot, v8std_mcp_snapshot_format"],
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture.write_docs(root / "docs")
            command = [sys.executable, "-S", str(ROOT / "scripts/generate_mcp_snapshot.py"),
                       "--docs", str(root / "docs"), "--output", str(root / "output"),
                       "--source-sha", fixture.SOURCE_SHA, "--site-url", fixture.SITE_URL]
            result = subprocess.run(command, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "output/manifest.json").is_file())
            result = subprocess.run(command[:-1] + [""], env=environment, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_current_corpus_round_trip_and_chunk_rule_parity(self):
        fmt, producer = self.modules()
        original_vectors = (ROOT / "docs/ai/search-vectors.jsonl").read_bytes()
        archive, manifest = producer.build_snapshot(ROOT / "docs", fixture.SOURCE_SHA, fixture.SITE_URL)
        second, _ = producer.build_snapshot(ROOT / "docs", fixture.SOURCE_SHA, fixture.SITE_URL)
        self.assertEqual(archive, second)
        verified = fmt.verify_archive(archive, manifest)
        self.assertEqual(verified.files["search-vectors.jsonl"], original_vectors)
        original_pages = [json.loads(line) for line in (ROOT / "docs/ai/pages.jsonl").read_bytes().splitlines()]
        pages = [json.loads(line) for line in verified.files["pages.jsonl"].splitlines()]
        self.assertEqual(len(pages), len(original_pages))
        generator = importlib.import_module("generate_search_vectors")
        expected_hashes = {(p["id"], field, index): hashlib.sha256(text.encode()).hexdigest()
                           for p in original_pages for field, index, text in generator.page_chunks(p)}
        for page, original in zip(pages, original_pages):
            self.assertEqual({k: v for k, v in page.items() if k not in {"site_path", "markdown_path"}}, original)
        for line in verified.files["search-vectors.jsonl"].splitlines():
            row = json.loads(line)
            self.assertEqual(row["text_sha256"], expected_hashes.pop((row["id"], row["field"], row["chunk_index"])))
        self.assertEqual(expected_hashes, {})


if __name__ == "__main__":
    unittest.main()
