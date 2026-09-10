"""Opt-in Task3 benchmark: real local corpus, supervised IPC, local HTTP only.

Run: .venv/bin/python -m tests.mcp_runtime_benchmark
Instrumentation exists only here; temporary observations are removed on exit.
"""
from functools import partial
import gc
import json
import os
from pathlib import Path
import pickle
import resource
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_mcp_snapshot import build_snapshot
from search_benchmark import collect_case_ids, read_case_payloads, run_ranked_case, run_diagnostics_case, percentile
from v8std_mcp_index import V8StdIndex
from v8std_mcp_runtime import SnapshotIndex, build_generation
from v8std_mcp_snapshots import SnapshotStore
from tests.test_v8std_mcp_runtime import Current
from tests.test_v8std_mcp_snapshots import Source
from tests import mcp_snapshot_fixtures as fixture


def record(path, phase, started, cpu, **fields):
    with Path(path).open("a") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "phase": phase,
            "seconds": time.perf_counter() - started, "cpu_seconds": time.process_time() - cpu,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
            **fields}) + "\n")


def observed_build(snapshot, *, profile, site_url):
    start, cpu = time.perf_counter(), time.process_time()
    generation = build_generation(snapshot, max_snippet_chars=4000, site_url=site_url)
    record(profile, "build", start, cpu)
    original = pickle.dumps

    def encode(*args, **kwargs):
        start, cpu = time.perf_counter(), time.process_time()
        value = original(*args, **kwargs)
        record(profile, "encode", start, cpu, bytes=len(value))
        return value

    pickle.dumps = encode
    return generation


class ObservedStore(SnapshotStore):
    def __init__(self, site, cache, profile):
        super().__init__(site, cache)
        self.profile = profile

    def _generation(self, *args, **kwargs):
        start, cpu = time.perf_counter(), time.process_time()
        try:
            return super()._generation(*args, **kwargs)
        finally:
            record(self.profile, "verify_cached", start, cpu)

    def _extract_verified(self, *args, **kwargs):
        start, cpu = time.perf_counter(), time.process_time()
        try:
            return super()._extract_verified(*args, **kwargs)
        finally:
            record(self.profile, "verify_stage", start, cpu)


def tree_rss():
    rows = subprocess.check_output(["ps", "-axo", "pid=,ppid=,rss="], text=True)
    rows = [tuple(map(int, row.split())) for row in rows.splitlines()]
    included = {os.getpid()}
    while True:
        more = {pid for pid, parent, _ in rows if parent in included}
        if more <= included:
            break
        included |= more
    return sum(rss * 1024 for pid, _, rss in rows if pid in included)


def ranked(index):
    cases, _ = read_case_payloads(ROOT / "tests/search_benchmark_cases.yml")
    records, ranks, times = [], [], []
    for case in cases:
        start = time.perf_counter()
        if case.get("tool") == "diagnostics":
            failures, ids = run_diagnostics_case(index, case)
            assert not failures, failures
            rank = None
        elif "expected_absent" in case:
            ids = collect_case_ids(index, case)
            assert case["expected_absent"] not in ids
            rank = None
        else:
            rank, ids = run_ranked_case(index, case)
            assert rank is not None and rank <= int(case.get("required_top", 3))
            ranks.append(0 if rank is None else 1 / rank)
        times.append((time.perf_counter() - start) * 1000)
        records.append((rank, ids))
    return {"cases": len(cases), "mrr": statistics.mean(ranks), "p95_ms": percentile(times, 95)}, records


def main():
    legacy = V8StdIndex(pages_path=ROOT / "docs/ai/pages.jsonl", vectors_path=ROOT / "docs/ai/search-vectors.jsonl")
    legacy.load()
    before, ranks_before = ranked(legacy)
    # Scores as well as rank order must survive the factory/presentation change.
    scores_before = {query: legacy.search(query) for query in ("std437", "модальные окна", "параметры запроса")}
    del legacy
    gc.collect()
    archive, manifest = build_snapshot(ROOT / "docs", "e07e1393c184a90968814af20fee0f7224c6d843", fixture.SITE_URL)
    source = Source()
    source.archive, source.manifest = archive, manifest
    print(json.dumps({"before": before, "archive_bytes": len(archive), "corpus_id": manifest["corpus_id"]}), flush=True)
    try:
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "profile.jsonl"
            store = ObservedStore(source.url, Path(directory) / "cache", profile)
            facade = SnapshotIndex(site_url=source.url, cache_dir=Path(directory) / "cache")
            active = None
            for phase in ("cold", "warm", "same_hash", "new_generation", "slow_source"):
                if phase == "new_generation":
                    from v8std_mcp_snapshot_format import verify_archive
                    files = dict(verify_archive(archive, manifest).files)
                    del files["metadata.json"]
                    files["llms.txt"] += b"\nBenchmark next generation\n"
                    source.archive, source.manifest = fixture.snapshot_fixture(files=fixture.with_metadata(files))
                    del files
                if phase == "slow_source":
                    source.fault = "headers"
                    source.release.clear()
                    timer = threading.Timer(2, source.release.set)
                    timer.start()
                samples, queries = [], []
                done = threading.Event()

                def sample():
                    while not done.is_set():
                        samples.append(tree_rss())
                        done.wait(.04)

                def query():
                    while not done.is_set():
                        start = time.perf_counter()
                        result = facade.search("параметры запроса")
                        assert result["results"]
                        queries.append((time.perf_counter() - start) * 1000)
                        done.wait(.01)

                sampler = threading.Thread(target=sample)
                reader = threading.Thread(target=query) if active else None
                sampler.start()
                if reader:
                    reader.start()
                original = pickle.loads
                def decode(*args, **kwargs):
                    start, cpu = time.perf_counter(), time.process_time()
                    value = original(*args, **kwargs)
                    record(profile, "parent_decode", start, cpu)
                    return value
                start, cpu = time.perf_counter(), time.process_time()
                try:
                    with patch("pickle.loads", side_effect=decode):
                        result, metadata = store._run("cached" if phase == "warm" else "refresh",
                                                     partial(observed_build, profile=profile, site_url=source.url))
                    elapsed = time.perf_counter() - start
                    parent_cpu = time.process_time() - cpu
                    samples.append(tree_rss())  # Both old and reconstructed new still retained.
                finally:
                    done.set()
                    sampler.join()
                    if reader:
                        reader.join()
                observations = [json.loads(line) for line in profile.read_text().splitlines()]
                profile.unlink()
                print(json.dumps({"phase": phase, "seconds": elapsed, "parent_cpu_seconds": parent_cpu,
                    "tree_peak_rss_bytes": max(samples), "query_count": len(queries),
                    "query_p95_ms": percentile(queries, 95), "query_max_ms": max(queries, default=0),
                    "observations": observations}), flush=True)
                active = result
                del result
                facade.coordinator = Current(active)
                gc.collect()
            after, ranks_after = ranked(facade)
            assert ranks_after == ranks_before
            for query, expected in scores_before.items():
                assert active.index.search(query) == expected
            print(json.dumps({"after": after, "identical_ranks": True, "identical_score_samples": True}), flush=True)
            for name in ("pages.jsonl", "llms.txt", "llms-full.txt"):
                start = time.perf_counter()
                body = facade.read_resource_text(name)
                print(json.dumps({"resource": name, "seconds": time.perf_counter() - start,
                                  "chars": len(body)}), flush=True)
    finally:
        source.close()


if __name__ == "__main__":
    main()
