from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import struct
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from v8std_retrieval_rules import RetrievalRules, normalize_text, tokenize


DEFAULT_INDEX_URL = "https://v8std.ru/ai/pages.jsonl"
DEFAULT_VECTORS_URL = "https://v8std.ru/ai/search-vectors.jsonl"
DEFAULT_CACHE_DIR = Path("/var/lib/v8std-mcp")
DEFAULT_REFRESH_SECONDS = 3600
MAX_QUERY_CHARS = 500
MAX_ID_OR_ALIAS_CHARS = 1000
MAX_LIMIT = 50
DEFAULT_LIMIT = 10
MAX_BODY_CHARS = 12000
MAX_BODY_LIMIT_CHARS = 30000
MAX_SNIPPET_CHARS = 4000
MAX_DIAGNOSTIC_CODES = 500
MAX_DIAGNOSTIC_CODE_CHARS = 200
MAX_ENUM_CHARS = 64
FETCH_CHUNK_BYTES = 64 * 1024
RESOURCE_MAX_BYTES = {
    "pages.jsonl": 16 * 1024 * 1024,
    "search-vectors.jsonl": 32 * 1024 * 1024,
    "llms.txt": 4 * 1024 * 1024,
    "llms-full.txt": 16 * 1024 * 1024,
}
VECTOR_DIM = 256
MAX_VECTOR_ROWS = 100000
MAX_VECTOR_BASE64_CHARS = 8192
VALID_TYPES = {"standard", "diagnostic", "pattern", "service"}
VALID_MODES = {"hybrid", "exact", "bm25", "semantic"}
VALID_RELATIONS = {"standard", "diagnostic", "edt_check", "related"}
LEGACY_RELATION_ALIASES = {
    "related_standard": "standard",
    "related_diagnostic": "diagnostic",
}

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_:-]+")
ACC_RE = re.compile(r"^(?:#?acc[:\s-]?|апк[:\s-]?)(\d+)$", re.IGNORECASE)
STD_RE = re.compile(r"^#?(?:std|стандарт)\s*?(\d+)$", re.IGNORECASE)
V8CS_RE = re.compile(r"^#?v8cs[:\s-]?(.+)$", re.IGNORECASE)
BSLLS_RE = re.compile(r"^#?bslls[:\s-]?(.+)$", re.IGNORECASE)


class IndexLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class IndexMetadata:
    source: str
    loaded_at: float
    row_count: int
    sha256: str


@dataclass(frozen=True)
class VectorMetadata:
    source: str
    loaded_at: float
    row_count: int
    sha256: str
    model: str
    dim: int


@dataclass(frozen=True)
class VectorEntry:
    page_id: str
    field: str
    chunk_index: int
    vector: tuple[float, ...]


def normalize_query(value: str) -> str:
    return normalize_text(value)


def require_text(value: Any, field_name: str, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if len(value) > max_chars:
        raise ValueError(f"{field_name} is too long: max {max_chars} characters")
    return value


def require_string_list(values: Any, field_name: str, item_max_chars: int) -> list[str] | None:
    if values is None:
        return None
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    result = []
    for value in values:
        result.append(require_text(value, f"{field_name} item", item_max_chars))
    return result


def normalize_lookup_key(value: str) -> str:
    value = normalize_query(value)
    value = value.removeprefix("https://v8std.ru/").strip("/")

    std_match = STD_RE.match(value)
    if std_match:
        return f"std{std_match.group(1)}"

    acc_match = ACC_RE.match(value)
    if acc_match:
        return f"acc:{acc_match.group(1)}"

    v8cs_match = V8CS_RE.match(value)
    if v8cs_match:
        return f"v8cs:{v8cs_match.group(1)}"

    bslls_match = BSLLS_RE.match(value)
    if bslls_match:
        return f"bslls:{bslls_match.group(1)}"

    if value.startswith("std/") and value.endswith(".md"):
        return f"std{Path(value).stem}"
    if value.startswith("std/"):
        parts = value.split("/")
        if len(parts) >= 2 and parts[1].isdigit():
            return f"std{parts[1]}"

    if value.startswith("diagnostics/"):
        parts = value.split("/")
        if len(parts) >= 3:
            family, code = parts[1], parts[2].removesuffix(".md")
            if family == "acc":
                return f"acc:{code}"
            if family == "bslls":
                return f"bslls:{code}"
            if family == "v8-code-style":
                return f"v8cs:{code}"

    return value.lstrip("#")


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    try:
        value = int(limit)
    except (TypeError, ValueError) as error:
        raise ValueError("limit must be an integer") from error
    return min(max(value, 1), MAX_LIMIT)


def clamp_body_limit(body_limit: int | None) -> int:
    if body_limit is None:
        return MAX_BODY_CHARS
    try:
        value = int(body_limit)
    except (TypeError, ValueError) as error:
        raise ValueError("body_limit must be an integer") from error
    return max(1000, min(value, MAX_BODY_LIMIT_CHARS))


def trim_body(page: dict[str, Any], max_body_chars: int = MAX_BODY_CHARS) -> dict[str, Any]:
    result = dict(page)
    body = result.get("body_markdown") or ""
    if len(body) > max_body_chars:
        result["body_markdown"] = body[:max_body_chars].rstrip() + "\n\n..."
        result["body_truncated"] = True
    else:
        result["body_truncated"] = False
    return result


def derive_markdown_url(page: dict[str, Any]) -> str:
    markdown_url = page.get("markdown_url")
    if isinstance(markdown_url, str) and markdown_url:
        return markdown_url

    url = page.get("url")
    if isinstance(url, str) and url.startswith("https://v8std.ru/"):
        return url.rstrip("/") + ".md"

    source_path = page.get("source_path")
    if isinstance(source_path, str) and source_path:
        return f"https://v8std.ru/{source_path}"

    return ""


def normalize_page_schema(page: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(page)
    normalized.setdefault("type", "service")
    normalized.setdefault("title", normalized.get("id", ""))
    normalized.setdefault("description", "")
    normalized.setdefault("url", "")
    normalized.setdefault("source_path", "")
    normalized.setdefault("aliases", [normalized.get("id", "")])
    normalized.setdefault("related", [])
    normalized.setdefault("source_urls", [])
    normalized.setdefault("body_markdown", "")
    normalized["markdown_url"] = derive_markdown_url(normalized)
    return normalized


def canonical_relation(value: str) -> str | None:
    relation = LEGACY_RELATION_ALIASES.get(value, value)
    return relation if relation in VALID_RELATIONS else None


def relation_for_target(source: dict[str, Any], target: dict[str, Any], relation: str | None = None) -> str:
    canonical = canonical_relation(relation or "")
    if canonical == "edt_check":
        return "edt_check"
    if source.get("id", "").startswith("acc:") and target.get("id", "").startswith("v8cs:"):
        return "edt_check"
    if target.get("type") == "standard":
        return "standard"
    if target.get("type") == "diagnostic":
        return "diagnostic"
    return canonical or "related"


def page_is_section(page: dict[str, Any]) -> bool:
    source_path = page.get("source_path", "")
    page_id = page.get("id", "")
    return source_path.endswith("index.md") or page_id in {"patterns:engineering"}


def concrete_rank(page: dict[str, Any]) -> int:
    return 1 if page_is_section(page) else 0


def signed_hash(value: str) -> tuple[int, float]:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    number = int.from_bytes(digest, "little")
    return number, -1.0 if number & 1 else 1.0


def embed_query(value: str, dim: int) -> tuple[float, ...]:
    vector = [0.0] * dim
    tokens = tokenize(value)
    features: list[str] = []
    features.extend(tokens)
    features.extend(f"{left}_{right}" for left, right in zip(tokens, tokens[1:]))
    for token in tokens:
        if len(token) >= 5:
            for index in range(0, len(token) - 2):
                features.append(f"char:{token[index:index + 3]}")

    if not features:
        return tuple(vector)

    for feature in features:
        hashed, sign = signed_hash(feature)
        vector[hashed % dim] += sign

    norm = math.sqrt(sum(item * item for item in vector))
    if norm:
        vector = [item / norm for item in vector]
    return tuple(vector)


def dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right))


def decode_vector(encoded: str, dim: int) -> tuple[float, ...]:
    payload = base64.b64decode(encoded, validate=True)
    expected_bytes = dim * 4
    if len(payload) != expected_bytes:
        raise ValueError(f"vector byte length must be {expected_bytes}")
    return tuple(struct.unpack(f"<{dim}f", payload))


class BM25Corpus:
    def __init__(self, docs: dict[str, list[str]]) -> None:
        self.docs = docs
        self.doc_count = len(docs)
        self.lengths = {doc_id: len(tokens) for doc_id, tokens in docs.items()}
        self.avgdl = sum(self.lengths.values()) / self.doc_count if self.doc_count else 0.0
        self.term_freqs = {doc_id: Counter(tokens) for doc_id, tokens in docs.items()}
        document_frequencies: Counter[str] = Counter()
        for tokens in docs.values():
            document_frequencies.update(set(tokens))
        self.idf = {
            token: math.log(1 + (self.doc_count - freq + 0.5) / (freq + 0.5))
            for token, freq in document_frequencies.items()
        }

    def scores(self, query_tokens: list[str], *, k1: float = 1.4, b: float = 0.75) -> dict[str, float]:
        if not query_tokens or not self.docs or not self.avgdl:
            return {}

        query_counter = Counter(query_tokens)
        scores: dict[str, float] = {}
        for doc_id, term_freq in self.term_freqs.items():
            score = 0.0
            doc_length = self.lengths[doc_id]
            for token, query_weight in query_counter.items():
                freq = term_freq.get(token, 0)
                if not freq:
                    continue
                numerator = freq * (k1 + 1)
                denominator = freq + k1 * (1 - b + b * doc_length / self.avgdl)
                score += self.idf.get(token, 0.0) * numerator / denominator * query_weight
            if score > 0:
                scores[doc_id] = score
        return scores


class V8StdIndex:
    def __init__(
        self,
        *,
        pages_path: Path | None = None,
        vectors_path: Path | None = None,
        index_url: str = DEFAULT_INDEX_URL,
        vectors_url: str = DEFAULT_VECTORS_URL,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
        request_timeout: int = 20,
        rules_path: Path | None = None,
    ) -> None:
        self.pages_path = pages_path
        self.vectors_path = vectors_path
        self.index_url = index_url
        self.vectors_url = vectors_url
        self.cache_dir = cache_dir
        self.refresh_seconds = refresh_seconds
        self.request_timeout = request_timeout
        self.rules = RetrievalRules.load(rules_path)
        self._lock = threading.RLock()
        self._pages: list[dict[str, Any]] = []
        self._pages_by_id: dict[str, dict[str, Any]] = {}
        self._pages_by_key: dict[str, dict[str, Any]] = {}
        self._metadata: IndexMetadata | None = None
        self._vector_metadata: VectorMetadata | None = None
        self._vectors: list[VectorEntry] = []
        self._bm25_metadata = BM25Corpus({})
        self._bm25_body = BM25Corpus({})
        self._missing_rule_targets: list[dict[str, str]] = []

    @property
    def metadata(self) -> IndexMetadata | None:
        return self._metadata

    @property
    def vector_metadata(self) -> VectorMetadata | None:
        return self._vector_metadata

    def load(self, *, force_refresh: bool = False) -> None:
        with self._lock:
            payload, source = self._load_payload(force_refresh=force_refresh)
            pages = self._parse_pages(payload)
            vectors, vector_metadata = self._load_vectors(force_refresh=force_refresh)
            self._replace_index(pages, source, payload, vectors, vector_metadata)

    def refresh_if_needed(self) -> None:
        if self.pages_path is not None:
            return
        metadata = self._metadata
        if metadata is None or time.time() - metadata.loaded_at >= self.refresh_seconds:
            try:
                self.load(force_refresh=True)
            except IndexLoadError:
                if metadata is None:
                    raise

    def status(self) -> dict[str, Any]:
        metadata = self._metadata
        if metadata is None:
            return {"ok": False, "row_count": 0, "semantic_enabled": False}

        vector_metadata = self._vector_metadata
        return {
            "ok": True,
            "source": metadata.source,
            "loaded_at": int(metadata.loaded_at),
            "row_count": metadata.row_count,
            "sha256": metadata.sha256,
            "missing_rule_targets": [dict(item) for item in self._missing_rule_targets],
            "semantic_enabled": vector_metadata is not None and bool(self._vectors),
            "vectors": None
            if vector_metadata is None
            else {
                "source": vector_metadata.source,
                "loaded_at": int(vector_metadata.loaded_at),
                "row_count": vector_metadata.row_count,
                "sha256": vector_metadata.sha256,
                "model": vector_metadata.model,
                "dim": vector_metadata.dim,
            },
        }

    def search(
        self,
        query: str,
        *,
        types: list[str] | None = None,
        mode: str = "hybrid",
        limit: int | None = None,
    ) -> dict[str, Any]:
        query = require_text(query, "query", MAX_QUERY_CHARS)
        requested_limit = clamp_limit(limit)
        allowed_types = self._validate_types(types)
        mode = self._validate_mode(mode)
        self.refresh_if_needed()
        normalized_query = normalize_query(query)
        if not normalized_query:
            return {
                "query": query,
                "normalized_query": normalized_query,
                "mode": mode,
                "types": sorted(allowed_types) if allowed_types else None,
                "results": [],
            }

        query_tokens = self._query_tokens(query)
        candidates: dict[str, dict[str, Any]] = {}

        if mode in {"hybrid", "exact"}:
            self._add_exact_scores(candidates, query, normalized_query)

        if mode in {"hybrid", "bm25"}:
            self._add_bm25_scores(candidates, query_tokens)

        if mode in {"hybrid", "semantic"}:
            self._add_semantic_scores(candidates, query)

        if mode == "hybrid":
            self._add_related_boosts(candidates)

        entries = []
        with self._lock:
            for page_id, candidate in candidates.items():
                page = self._pages_by_id.get(page_id)
                if not page:
                    continue
                if allowed_types and page.get("type") not in allowed_types:
                    continue
                score = candidate["score"]
                if page_is_section(page) and not candidate["details"].get("exact"):
                    score *= 0.65
                    candidate["details"]["section_penalty"] = 0.65
                if score <= 0:
                    continue
                entries.append((score, page, candidate))

        entries.sort(key=lambda item: (-item[0], concrete_rank(item[1]), item[1]["type"], item[1]["id"]))
        return {
            "query": query,
            "normalized_query": normalized_query,
            "mode": mode,
            "types": sorted(allowed_types) if allowed_types else None,
            "semantic_enabled": self._vector_metadata is not None and bool(self._vectors),
            "results": [
                self._search_entry(page, score, candidate)
                for score, page, candidate in entries[:requested_limit]
            ],
        }

    def page(self, id_or_alias_or_url: str, *, body_limit: int = MAX_BODY_CHARS) -> dict[str, Any]:
        id_or_alias_or_url = require_text(
            id_or_alias_or_url,
            "id_or_alias_or_url",
            MAX_ID_OR_ALIAS_CHARS,
        )
        body_limit = clamp_body_limit(body_limit)
        self.refresh_if_needed()
        page = self.resolve(id_or_alias_or_url)
        if page is None:
            candidates = []
            if len(id_or_alias_or_url) <= MAX_QUERY_CHARS:
                candidates = self.search(id_or_alias_or_url, limit=5)["results"]
            return {
                "found": False,
                "query": id_or_alias_or_url,
                "candidates": candidates,
            }
        return {"found": True, "page": trim_body(page, max_body_chars=body_limit), "candidates": []}

    def related(
        self,
        id_or_alias_or_url: str,
        *,
        relations: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        id_or_alias_or_url = require_text(
            id_or_alias_or_url,
            "id_or_alias_or_url",
            MAX_ID_OR_ALIAS_CHARS,
        )
        requested_limit = clamp_limit(limit)
        allowed_relations = self._validate_relations(relations)
        self.refresh_if_needed()
        page = self.resolve(id_or_alias_or_url)
        if page is None:
            return {"found": False, "query": id_or_alias_or_url, "related": []}

        related_entries = page.get("related", [])
        if allowed_relations:
            related_entries = [
                item for item in related_entries if item.get("relation") in allowed_relations
            ]

        enriched = []
        for item in related_entries[:requested_limit]:
            target = self.resolve(item.get("id", ""))
            enriched.append({**item, "description": target.get("description") if target else None})

        return {
            "found": True,
            "id": page["id"],
            "title": page["title"],
            "relations": sorted(allowed_relations) if allowed_relations else None,
            "related": enriched,
        }

    def explain_snippet(
        self,
        snippet: str,
        *,
        language: str = "auto",
        limit: int | None = None,
    ) -> dict[str, Any]:
        snippet = require_text(snippet, "snippet", MAX_SNIPPET_CHARS)
        language = require_text(language, "language", MAX_ENUM_CHARS)
        if language not in {"auto", "bsl", "sdbl"}:
            raise ValueError("language must be one of: auto, bsl, sdbl")

        requested_limit = clamp_limit(limit)
        self.refresh_if_needed()
        analysis = self.rules.analyze_snippet(snippet)
        signal_targets = [
            target_id
            for signal in analysis["signals"]
            for target_id in signal.get("target_ids", [])
        ]
        signal_text = " ".join(
            [
                analysis["normalized_text"],
                *[signal["value"] for signal in analysis["signals"]],
                *signal_targets,
            ]
        )
        search_result = self.search(signal_text or snippet, types=None, mode="hybrid", limit=limit)

        diagnostics = []
        standards = []
        for result in search_result["results"]:
            if result["type"] == "diagnostic":
                diagnostics.append(result)
            elif result["type"] in {"standard", "pattern"}:
                standards.append(result)

        confidence = 0.0
        if analysis["signals"]:
            confidence += 0.45
        if search_result["results"]:
            confidence += min(search_result["results"][0]["score"] / 5000, 0.55)

        return {
            "language": language,
            "normalized_text": analysis["normalized_text"],
            "tokens": analysis["tokens"],
            "signals": analysis["signals"],
            "diagnostics": diagnostics[:requested_limit],
            "standards": standards[:requested_limit],
            "confidence": round(min(confidence, 1.0), 3),
        }

    def explain_diagnostics(self, codes: list[str]) -> dict[str, Any]:
        if not isinstance(codes, list):
            raise ValueError("codes must be a list")
        if len(codes) > MAX_DIAGNOSTIC_CODES:
            raise ValueError(f"codes list is too long: max {MAX_DIAGNOSTIC_CODES}")

        self.refresh_if_needed()
        normalized_codes = []
        for code in codes:
            code_text = require_text(code, "diagnostic code", MAX_DIAGNOSTIC_CODE_CHARS)
            if code_text.strip():
                normalized_codes.append(normalize_lookup_key(code_text))
        frequencies = Counter(normalized_codes)
        diagnostics = []
        standards_by_id: dict[str, dict[str, Any]] = {}
        unknown_codes = []

        for normalized_code, frequency in frequencies.most_common():
            page = self.resolve(normalized_code)
            if page is None or page.get("type") != "diagnostic":
                unknown_codes.append({"code": normalized_code, "frequency": frequency})
                continue
            related_standards = []
            for item in page.get("related", []):
                if item.get("relation") != "standard":
                    continue
                target = self.resolve(item.get("id", ""))
                enriched = {**item, "description": target.get("description") if target else None}
                related_standards.append(enriched)
                standards_by_id[item["id"]] = {
                    "id": item["id"],
                    "title": item["title"],
                    "url": item["url"],
                    "markdown_url": item["markdown_url"],
                    "frequency": standards_by_id.get(item["id"], {}).get("frequency", 0) + frequency,
                }
            diagnostics.append(
                {
                    "id": page["id"],
                    "title": page["title"],
                    "url": page["url"],
                    "markdown_url": page["markdown_url"],
                    "frequency": frequency,
                    "standards": related_standards,
                }
            )

        standards = sorted(standards_by_id.values(), key=lambda item: (-item["frequency"], item["id"]))
        return {
            "diagnostics": diagnostics,
            "standards": standards,
            "unknown_codes": unknown_codes,
            "total_input": len(codes),
            "unique_codes": len(frequencies),
        }

    def resolve(self, id_or_alias_or_url: str) -> dict[str, Any] | None:
        key = normalize_lookup_key(id_or_alias_or_url)
        with self._lock:
            return self._pages_by_key.get(key)

    def read_resource_text(self, resource_name: str) -> str:
        self.refresh_if_needed()
        if resource_name == "pages.jsonl" and self.pages_path is not None:
            return self.pages_path.read_text(encoding="utf-8")

        if self.pages_path is not None:
            docs_dir = self.pages_path.parent.parent
            local = {
                "llms.txt": docs_dir / "llms.txt",
                "llms-full.txt": docs_dir / "llms-full.txt",
                "pages.jsonl": self.pages_path,
            }.get(resource_name)
            if local and local.is_file():
                return local.read_text(encoding="utf-8")

        remote_path = {
            "llms.txt": "https://v8std.ru/llms.txt",
            "llms-full.txt": "https://v8std.ru/llms-full.txt",
            "pages.jsonl": self.index_url,
        }.get(resource_name)
        if not remote_path:
            raise ValueError(f"unknown resource: {resource_name}")
        payload, _source = self._load_remote_resource(resource_name, remote_path)
        return payload

    def _validate_types(self, types: list[str] | None) -> set[str] | None:
        values = require_string_list(types, "types", MAX_ENUM_CHARS)
        if values is None:
            return None
        if any(value not in VALID_TYPES for value in values):
            raise ValueError("invalid page type")
        return set(values)

    def _validate_mode(self, mode: str) -> str:
        mode = require_text(mode, "mode", MAX_ENUM_CHARS)
        if mode not in VALID_MODES:
            raise ValueError("invalid search mode")
        return mode

    def _validate_relations(self, relations: list[str] | None) -> set[str] | None:
        values = require_string_list(relations, "relations", MAX_ENUM_CHARS)
        if values is None:
            return None
        result = set()
        for relation in values:
            canonical = canonical_relation(relation)
            if canonical is None:
                raise ValueError("invalid relation")
            result.add(canonical)
        return result

    def _query_tokens(self, query: str) -> list[str]:
        analysis = self.rules.analyze_snippet(query)
        signal_values = [signal["value"] for signal in analysis["signals"]]
        return tokenize(" ".join([query, *signal_values]))

    def _add_candidate(
        self,
        candidates: dict[str, dict[str, Any]],
        page_id: str,
        score: float,
        reason: str,
        detail_key: str,
        detail_score: float,
    ) -> None:
        if page_id not in candidates:
            candidates[page_id] = {"score": 0.0, "reasons": [], "details": defaultdict(float)}
        candidates[page_id]["score"] += score
        if reason not in candidates[page_id]["reasons"]:
            candidates[page_id]["reasons"].append(reason)
        candidates[page_id]["details"][detail_key] += detail_score

    def _add_exact_scores(
        self,
        candidates: dict[str, dict[str, Any]],
        query: str,
        normalized_query: str,
    ) -> None:
        exact_page = self.resolve(normalized_query)
        if exact_page is not None:
            self._add_candidate(candidates, exact_page["id"], 5000.0, "exact_lookup", "exact", 5000.0)

        with self._lock:
            for page in self._pages:
                page_id = normalize_query(page["id"])
                if normalized_query == page_id:
                    self._add_candidate(candidates, page["id"], 4800.0, "exact_id", "exact", 4800.0)
                for alias in page.get("aliases", []):
                    alias_norm = normalize_query(alias)
                    if alias_norm == normalized_query:
                        self._add_candidate(
                            candidates, page["id"], 4400.0, f"exact_alias:{alias}", "exact", 4400.0
                        )
                    elif alias_norm and (alias_norm in normalized_query or normalized_query in alias_norm):
                        self._add_candidate(
                            candidates, page["id"], 900.0, f"alias:{alias}", "alias", 900.0
                        )

        for match in self.rules.match_text(query):
            targets = match.rule.target_ids
            for target_id in targets:
                if not target_id:
                    continue
                score = 4200.0 if target_id == match.rule.primary else 2200.0
                self._add_candidate(
                    candidates,
                    target_id,
                    score,
                    f"rule:{match.rule.id}:{match.alias}",
                    "rules",
                    score,
                )

    def _add_bm25_scores(self, candidates: dict[str, dict[str, Any]], query_tokens: list[str]) -> None:
        metadata_scores = self._bm25_metadata.scores(query_tokens)
        body_scores = self._bm25_body.scores(query_tokens)
        for rank, (page_id, score) in enumerate(
            sorted(metadata_scores.items(), key=lambda item: item[1], reverse=True), start=1
        ):
            rrf = 9000.0 / (60 + rank)
            self._add_candidate(
                candidates,
                page_id,
                score * 80.0 + rrf,
                "bm25_metadata",
                "bm25_metadata",
                score,
            )
        for rank, (page_id, score) in enumerate(
            sorted(body_scores.items(), key=lambda item: item[1], reverse=True), start=1
        ):
            rrf = 5000.0 / (60 + rank)
            self._add_candidate(
                candidates,
                page_id,
                score * 35.0 + rrf,
                "bm25_body",
                "bm25_body",
                score,
            )

    def _add_semantic_scores(self, candidates: dict[str, dict[str, Any]], query: str) -> None:
        metadata = self._vector_metadata
        if metadata is None or not self._vectors:
            return
        query_vector = embed_query(query, metadata.dim)
        per_page: dict[str, tuple[float, str]] = {}
        for entry in self._vectors:
            score = dot(query_vector, entry.vector)
            if score <= 0:
                continue
            previous = per_page.get(entry.page_id)
            if previous is None or score > previous[0]:
                per_page[entry.page_id] = (score, f"{entry.field}:{entry.chunk_index}")
        for rank, (page_id, (score, chunk)) in enumerate(
            sorted(per_page.items(), key=lambda item: item[1][0], reverse=True), start=1
        ):
            rrf = 6500.0 / (60 + rank)
            self._add_candidate(
                candidates,
                page_id,
                score * 1200.0 + rrf,
                f"semantic:{chunk}",
                "semantic",
                score,
            )

    def _add_related_boosts(self, candidates: dict[str, dict[str, Any]]) -> None:
        boosts: dict[str, float] = defaultdict(float)
        source_reasons: dict[str, list[str]] = defaultdict(list)
        with self._lock:
            for page_id, candidate in list(candidates.items()):
                page = self._pages_by_id.get(page_id)
                if not page:
                    continue
                boost = min(candidate["score"] * 0.04, 180.0)
                for item in page.get("related", [])[:12]:
                    target_id = item.get("id")
                    if not target_id or target_id == page_id:
                        continue
                    boosts[target_id] += boost
                    source_reasons[target_id].append(page_id)
        for page_id, boost in boosts.items():
            if page_id in candidates and candidates[page_id]["details"].get("exact"):
                continue
            self._add_candidate(
                candidates,
                page_id,
                boost,
                f"related_boost:{','.join(source_reasons[page_id][:3])}",
                "related_boost",
                boost,
            )

    def _search_entry(
        self,
        page: dict[str, Any],
        score: float,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        details = {
            key: round(value, 6)
            for key, value in dict(candidate["details"]).items()
            if value
        }
        return {
            "id": page["id"],
            "type": page["type"],
            "title": page["title"],
            "description": page["description"],
            "url": page["url"],
            "markdown_url": page["markdown_url"],
            "score": round(score, 6),
            "match_reasons": candidate["reasons"][:12],
            "score_details": details,
            "related_preview": page.get("related", [])[:8],
        }

    def _load_payload(self, *, force_refresh: bool) -> tuple[str, str]:
        if self.pages_path is not None:
            try:
                return self.pages_path.read_text(encoding="utf-8"), str(self.pages_path)
            except OSError as error:
                raise IndexLoadError(f"could not read {self.pages_path}: {error}") from error

        try:
            return self._load_remote_resource(
                "pages.jsonl",
                self.index_url,
                force_refresh=force_refresh,
            )
        except IndexLoadError as error:
            raise IndexLoadError(f"could not load index from {self.index_url}: {error}") from error

    def _load_vectors(self, *, force_refresh: bool) -> tuple[list[VectorEntry], VectorMetadata | None]:
        source = ""
        payload = ""
        if self.vectors_path is not None:
            if not self.vectors_path.is_file():
                return [], None
            source = str(self.vectors_path)
            payload = self.vectors_path.read_text(encoding="utf-8")
        elif self.pages_path is not None:
            derived_path = self.pages_path.parent / "search-vectors.jsonl"
            if not derived_path.is_file():
                return [], None
            source = str(derived_path)
            payload = derived_path.read_text(encoding="utf-8")
        else:
            try:
                payload, source = self._load_remote_resource(
                    "search-vectors.jsonl",
                    self.vectors_url,
                    force_refresh=force_refresh,
                )
            except IndexLoadError:
                return [], None

        vectors: list[VectorEntry] = []
        model = ""
        dim = 0
        row_count = 0
        for line_number, line in enumerate(payload.splitlines(), start=1):
            if not line.strip():
                continue
            row_count += 1
            if row_count > MAX_VECTOR_ROWS:
                raise IndexLoadError(f"too many vector rows: max {MAX_VECTOR_ROWS}")
            try:
                row = json.loads(line)
                row_dim = int(row["dim"])
                if row_dim != VECTOR_DIM:
                    raise ValueError(f"vector dim must be {VECTOR_DIM}")
                encoded = str(row["vector_base64"])
                if len(encoded) > MAX_VECTOR_BASE64_CHARS:
                    raise ValueError(
                        f"vector_base64 is too long: max {MAX_VECTOR_BASE64_CHARS} characters"
                    )
                row_model = str(row.get("model", ""))
                if model and row_model and row_model != model:
                    raise ValueError("inconsistent vector model")
                if dim and row_dim != dim:
                    raise ValueError("inconsistent vector dim")
                vectors.append(
                    VectorEntry(
                        page_id=str(row["id"]),
                        field=str(row.get("field", "body")),
                        chunk_index=int(row.get("chunk_index", 0)),
                        vector=decode_vector(encoded, row_dim),
                    )
                )
                model = model or row_model
                dim = dim or row_dim
            except Exception as error:
                raise IndexLoadError(f"invalid vector payload at line {line_number}: {error}") from error

        if not vectors:
            return [], None
        metadata = VectorMetadata(
            source=source,
            loaded_at=time.time(),
            row_count=len(vectors),
            sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            model=model,
            dim=dim,
        )
        return vectors, metadata

    def _cache_is_fresh(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if self.refresh_seconds <= 0:
            return False
        try:
            return time.time() - path.stat().st_mtime < self.refresh_seconds
        except OSError:
            return False

    def _load_remote_resource(
        self,
        resource_name: str,
        url: str,
        *,
        force_refresh: bool = False,
    ) -> tuple[str, str]:
        max_bytes = RESOURCE_MAX_BYTES[resource_name]
        cache_path = self.cache_dir / resource_name
        if not force_refresh and self._cache_is_fresh(cache_path):
            return self._read_limited_text(cache_path, max_bytes=max_bytes), str(cache_path)

        try:
            payload = self._fetch_url(url, max_bytes=max_bytes)
            self._write_cache_text(cache_path, payload)
            return payload, url
        except (OSError, URLError, IndexLoadError) as error:
            if cache_path.is_file():
                return self._read_limited_text(cache_path, max_bytes=max_bytes), str(cache_path)
            raise IndexLoadError(f"could not load {resource_name}: {error}") from error

    def _read_limited_text(self, path: Path, *, max_bytes: int) -> str:
        try:
            if path.stat().st_size > max_bytes:
                raise IndexLoadError(f"cached resource is too large: {path.name}")
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise IndexLoadError(f"cached resource is not valid UTF-8: {path.name}") from error
        except OSError as error:
            raise IndexLoadError(f"could not read cached resource {path.name}: {error}") from error

    def _write_cache_text(self, path: Path, payload: str) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{threading.get_ident()}.{time.time_ns()}.tmp")
        try:
            temp_path.write_text(payload, encoding="utf-8")
            temp_path.replace(path)
        finally:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

    def _fetch_url(self, url: str, *, max_bytes: int) -> str:
        request = Request(
            url,
            headers={
                "Accept": "application/jsonl,text/plain,*/*",
                "User-Agent": "v8std-mcp/2.0",
            },
        )
        with urlopen(request, timeout=self.request_timeout) as response:
            status = int(getattr(response, "status", getattr(response, "code", 200)) or 200)
            if status >= 400:
                raise URLError(f"HTTP status {status}")

            headers = getattr(response, "headers", None)
            content_length = headers.get("Content-Length") if headers else None
            if content_length:
                try:
                    if int(content_length) > max_bytes:
                        raise IndexLoadError("remote response is too large")
                except ValueError:
                    pass

            chunks = []
            total = 0
            while True:
                chunk = response.read(FETCH_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise IndexLoadError("remote response is too large")
                chunks.append(chunk)

        try:
            return b"".join(chunks).decode("utf-8")
        except UnicodeDecodeError as error:
            raise IndexLoadError("remote response is not valid UTF-8") from error

    def _parse_pages(self, payload: str) -> list[dict[str, Any]]:
        pages = []
        for line_number, line in enumerate(payload.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                page = json.loads(line)
            except json.JSONDecodeError as error:
                raise IndexLoadError(f"invalid JSONL at line {line_number}: {error}") from error

            if not isinstance(page, dict) or not page.get("id"):
                raise IndexLoadError(f"invalid page payload at line {line_number}")
            normalized = normalize_page_schema(page)
            normalized["aliases"] = self._merged_aliases(normalized)
            pages.append(normalized)

        if not pages:
            raise IndexLoadError("index is empty")
        return pages

    def _merged_aliases(self, page: dict[str, Any]) -> list[str]:
        aliases = list(page.get("aliases", []))
        aliases.extend(self.rules.aliases_for_page(page["id"]))
        result = []
        seen = set()
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip():
                continue
            if alias not in seen:
                result.append(alias)
                seen.add(alias)
        return result

    def _related_entry(self, relation: str, target: dict[str, Any]) -> dict[str, Any]:
        return {
            "relation": relation,
            "id": target["id"],
            "type": target["type"],
            "title": target["title"],
            "url": target["url"],
            "markdown_url": target["markdown_url"],
            "source_path": target["source_path"],
        }

    def _append_relation(
        self,
        relations: list[dict[str, Any]],
        seen: set[tuple[str, str, str]],
        source: dict[str, Any],
        target: dict[str, Any],
        relation: str | None = None,
    ) -> None:
        if source["id"] == target["id"]:
            return
        canonical = relation_for_target(source, target, relation)
        key = (source["id"], target["id"], canonical)
        if key in seen:
            return
        seen.add(key)
        relations.append(self._related_entry(canonical, target))

    def _apply_related_graph(self, pages: list[dict[str, Any]], pages_by_id: dict[str, dict[str, Any]]) -> None:
        missing: list[dict[str, str]] = []
        missing_seen: set[tuple[str, str]] = set()

        for page in pages:
            related = []
            seen: set[tuple[str, str, str]] = set()
            for item in page.get("related", []):
                target_id = item.get("id")
                if not isinstance(target_id, str):
                    continue
                target = pages_by_id.get(target_id)
                if target is None:
                    continue
                self._append_relation(related, seen, page, target, item.get("relation"))
            page["related"] = related

        for rule in self.rules.rules:
            for target_id in rule.target_ids:
                if not target_id or target_id in pages_by_id:
                    continue
                key = (rule.id, target_id)
                if key not in missing_seen:
                    missing.append({"rule": rule.id, "id": target_id})
                    missing_seen.add(key)

            valid_targets = [
                pages_by_id[target_id]
                for target_id in rule.target_ids
                if target_id in pages_by_id
            ]
            primary = pages_by_id.get(rule.primary)
            if primary is not None:
                seen = {
                    (primary["id"], item["id"], item["relation"])
                    for item in primary.get("related", [])
                }
                related = list(primary.get("related", []))
                for target in valid_targets:
                    self._append_relation(related, seen, primary, target)
                primary["related"] = related

            valid_standards = [
                pages_by_id[standard_id]
                for standard_id in rule.standards
                if standard_id in pages_by_id
            ]
            for diagnostic_id in rule.diagnostics:
                diagnostic = pages_by_id.get(diagnostic_id)
                if diagnostic is None or diagnostic.get("type") != "diagnostic":
                    continue
                seen = {
                    (diagnostic["id"], item["id"], item["relation"])
                    for item in diagnostic.get("related", [])
                }
                related = list(diagnostic.get("related", []))
                for standard in valid_standards:
                    self._append_relation(related, seen, diagnostic, standard)
                diagnostic["related"] = related

        for page in pages:
            page["related"] = sorted(page.get("related", []), key=lambda item: (item["relation"], item["id"]))

        self._missing_rule_targets = sorted(missing, key=lambda item: (item["rule"], item["id"]))

    def _replace_index(
        self,
        pages: list[dict[str, Any]],
        source: str,
        payload: str,
        vectors: list[VectorEntry],
        vector_metadata: VectorMetadata | None,
    ) -> None:
        pages_by_id: dict[str, dict[str, Any]] = {}
        pages_by_key: dict[str, dict[str, Any]] = {}
        metadata_docs: dict[str, list[str]] = {}
        body_docs: dict[str, list[str]] = {}

        for page in pages:
            pages_by_id[page["id"]] = page

        self._apply_related_graph(pages, pages_by_id)

        for page in pages:
            for value in self._lookup_values(page):
                pages_by_key.setdefault(normalize_lookup_key(value), page)
            metadata_docs[page["id"]] = tokenize(
                " ".join(
                    [
                        page.get("id", ""),
                        page.get("title", ""),
                        page.get("description", ""),
                        " ".join(page.get("aliases", [])),
                    ]
                )
            )
            body_docs[page["id"]] = tokenize(page.get("body_markdown", ""))

        page_ids = set(pages_by_id)
        vectors = [entry for entry in vectors if entry.page_id in page_ids]
        self._pages = pages
        self._pages_by_id = pages_by_id
        self._pages_by_key = pages_by_key
        self._bm25_metadata = BM25Corpus(metadata_docs)
        self._bm25_body = BM25Corpus(body_docs)
        self._vectors = vectors
        self._vector_metadata = vector_metadata if vectors else None
        self._metadata = IndexMetadata(
            source=source,
            loaded_at=time.time(),
            row_count=len(pages),
            sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )

    def _lookup_values(self, page: dict[str, Any]) -> list[str]:
        values = [
            page.get("id", ""),
            page.get("url", ""),
            page.get("markdown_url", ""),
            page.get("source_path", ""),
        ]
        values.extend(page.get("aliases", []))
        return [value for value in values if isinstance(value, str) and value.strip()]
