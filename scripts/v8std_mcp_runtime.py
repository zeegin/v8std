"""One immutable index generation per complete data call."""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path

from v8std_mcp_index import (
    V8StdIndex, DEFAULT_CACHE_DIR, MAX_BODY_CHARS, MAX_QUERY_CHARS, MAX_ID_OR_ALIAS_CHARS,
    MAX_SNIPPET_CHARS, MAX_ENUM_CHARS, MAX_DIAGNOSTIC_CODES, MAX_DIAGNOSTIC_CODE_CHARS,
    clamp_body_limit, clamp_limit, require_text, trim_body, validate_max_snippet_chars,
)
from v8std_mcp_presentation import LinkCatalog, present_result
from v8std_mcp_snapshot_format import DEFAULT_SITE_URL, VerifiedSnapshot, normalize_site_url
from v8std_mcp_snapshots import LoaderError, SnapshotCoordinator, SnapshotStore
from v8std_mcp_hold import CONTROL_PATH


@dataclass(frozen=True)
class IndexGeneration:
    corpus_id: str
    index: V8StdIndex
    canonical_site_url: str
    page_paths: dict


def build_generation(snapshot: VerifiedSnapshot, *, max_snippet_chars: int,
                     site_url: str | None = None) -> IndexGeneration:
    index = V8StdIndex.from_validated_bytes(snapshot.files["pages.jsonl"],
                snapshot.files["search-vectors.jsonl"], max_snippet_chars=max_snippet_chars)
    paths = {page["id"]: {key: page[key] for key in ("site_path", "markdown_path")}
             for page in index._pages}
    canonical = snapshot.metadata["canonical_site_url"]
    return IndexGeneration(snapshot.metadata["corpus_id"], index, canonical, paths)


class SnapshotIndex:
    def __init__(self, *, site_url: str = DEFAULT_SITE_URL, cache_dir: Path = DEFAULT_CACHE_DIR,
                 refresh_seconds: int = 3600, max_snippet_chars: int = MAX_SNIPPET_CHARS,
                 runtime_sha: str | None = None, release_control: Path | None = None):
        self.site_url = normalize_site_url(site_url)
        self._max_snippet_chars = validate_max_snippet_chars(max_snippet_chars)
        self.runtime_sha = runtime_sha if runtime_sha and len(runtime_sha) == 40 and all(
            char in "0123456789abcdef" for char in runtime_sha) else None
        self.coordinator = SnapshotCoordinator(SnapshotStore(self.site_url, cache_dir),
            partial(build_generation, max_snippet_chars=max_snippet_chars, site_url=self.site_url),
            refresh_seconds=refresh_seconds, release_control=(release_control if release_control is not None
                                                            else CONTROL_PATH if CONTROL_PATH.parent.exists() else None))

    @property
    def max_snippet_chars(self):
        return self._max_snippet_chars

    def start(self):
        self.coordinator.start()

    def close(self):
        self.coordinator.close()

    def status(self):
        state = self.coordinator.status()
        counts = {"row_count": 0, "semantic_enabled": False}
        if state["ready"]:
            generation = self.coordinator.current()
            if generation.corpus_id == state["corpus_id"]:
                counts = {"row_count": generation.index.metadata.row_count,
                          "semantic_enabled": generation.index.vector_metadata is not None}
        # No source paths or unbounded missing-target list.
        return {"ok": state["ready"], **counts, "runtime_sha": self.runtime_sha, **state}

    def _current(self):
        try:
            return self.coordinator.current()
        except LoaderError as error:
            if error.code == "INDEX_NOT_READY":
                raise ValueError("INDEX_NOT_READY: retry later") from None
            raise

    def _present(self, generation, result):
        return present_result(result, canonical_site_url=generation.canonical_site_url,
                              site_url=self.site_url, page_paths=generation.page_paths)

    def _lookup(self, generation, value):
        return LinkCatalog(generation.canonical_site_url, self.site_url, generation.page_paths).lookup(value)

    def search(self, query, *, types=None, mode="hybrid", limit=None):
        require_text(query, "query", MAX_QUERY_CHARS)
        clamp_limit(limit)
        V8StdIndex._validate_types(types)
        V8StdIndex._validate_mode(mode)
        generation = self._current()
        return self._present(generation, generation.index.search(query, types=types, mode=mode, limit=limit))

    def page(self, id_or_alias_or_url, *, body_limit=MAX_BODY_CHARS):
        require_text(id_or_alias_or_url, "id_or_alias_or_url", MAX_ID_OR_ALIAS_CHARS)
        body_limit = clamp_body_limit(body_limit)
        generation = self._current()
        lookup = self._lookup(generation, id_or_alias_or_url)
        page = generation.index.resolve(lookup)
        if page is not None:
            # Parse the full link before trimming. A longer local prefix cannot
            # enlarge the inherited body budget or leave a cut public link.
            presented = self._present(generation, page)
            return {"found": True, "page": trim_body(presented, body_limit), "candidates": []}
        return self._present(generation, generation.index.page(lookup, body_limit=body_limit))

    def related(self, id_or_alias_or_url, *, relations=None, limit=None):
        require_text(id_or_alias_or_url, "id_or_alias_or_url", MAX_ID_OR_ALIAS_CHARS)
        clamp_limit(limit)
        V8StdIndex._validate_relations(relations)
        generation = self._current()
        return self._present(generation, generation.index.related(self._lookup(generation, id_or_alias_or_url),
                                                                  relations=relations, limit=limit))

    def explain_snippet(self, snippet, *, language="auto", limit=None):
        require_text(snippet, "snippet", self.max_snippet_chars)
        require_text(language, "language", MAX_ENUM_CHARS)
        if language not in {"auto", "bsl", "sdbl"}:
            raise ValueError("language must be one of: auto, bsl, sdbl")
        clamp_limit(limit)
        generation = self._current()
        return self._present(generation, generation.index.explain_snippet(snippet, language=language, limit=limit))

    def explain_diagnostics(self, codes):
        if not isinstance(codes, list):
            raise ValueError("codes must be a list")
        if len(codes) > MAX_DIAGNOSTIC_CODES:
            raise ValueError(f"codes list is too long: max {MAX_DIAGNOSTIC_CODES}")
        for code in codes:
            require_text(code, "diagnostic code", MAX_DIAGNOSTIC_CODE_CHARS)
        generation = self._current()
        return self._present(generation, generation.index.explain_diagnostics(codes))
