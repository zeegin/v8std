from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_INDEX_URL = "https://v8std.ru/ai/pages.jsonl"
DEFAULT_CACHE_DIR = Path("/var/lib/v8std-mcp")
DEFAULT_REFRESH_SECONDS = 3600
MAX_QUERY_CHARS = 300
MAX_LIMIT = 20
MAX_BODY_CHARS = 12000

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


def normalize_query(value: str) -> str:
    return " ".join(value.strip().lower().split())


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


def tokenize(value: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(value)]


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return 10
    return min(max(int(limit), 1), MAX_LIMIT)


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


class V8StdIndex:
    def __init__(
        self,
        *,
        pages_path: Path | None = None,
        index_url: str = DEFAULT_INDEX_URL,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
        request_timeout: int = 20,
    ) -> None:
        self.pages_path = pages_path
        self.index_url = index_url
        self.cache_dir = cache_dir
        self.refresh_seconds = refresh_seconds
        self.request_timeout = request_timeout
        self._lock = threading.RLock()
        self._pages: list[dict[str, Any]] = []
        self._pages_by_id: dict[str, dict[str, Any]] = {}
        self._pages_by_key: dict[str, dict[str, Any]] = {}
        self._search_text_by_id: dict[str, str] = {}
        self._metadata: IndexMetadata | None = None

    @property
    def metadata(self) -> IndexMetadata | None:
        return self._metadata

    def load(self, *, force_refresh: bool = False) -> None:
        with self._lock:
            payload, source = self._load_payload(force_refresh=force_refresh)
            pages = self._parse_pages(payload)
            self._replace_index(pages, source, payload)

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
            return {"ok": False, "row_count": 0}
        return {
            "ok": True,
            "source": metadata.source,
            "loaded_at": int(metadata.loaded_at),
            "row_count": metadata.row_count,
            "sha256": metadata.sha256,
        }

    def search(
        self,
        query: str,
        *,
        page_type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        self.refresh_if_needed()
        normalized_query = normalize_query(query)[:MAX_QUERY_CHARS]
        if not normalized_query:
            return {"query": query, "results": []}

        requested_limit = clamp_limit(limit)
        exact_page = self.resolve(normalized_query)
        tokens = tokenize(normalized_query)
        results: list[tuple[int, dict[str, Any], list[str]]] = []

        with self._lock:
            for page in self._pages:
                if page_type and page.get("type") != page_type:
                    continue
                score = 0
                matched_aliases: list[str] = []

                if exact_page is page:
                    score += 500

                page_id = page["id"].lower()
                if normalized_query == page_id:
                    score += 450

                for alias in page.get("aliases", []):
                    alias_norm = normalize_query(alias)
                    if alias_norm == normalized_query:
                        score += 400
                        matched_aliases.append(alias)
                    elif normalized_query in alias_norm:
                        score += 120
                        matched_aliases.append(alias)

                title = page.get("title", "").lower()
                description = page.get("description", "").lower()
                search_text = self._search_text_by_id[page["id"]]

                if normalized_query in title:
                    score += 100
                if normalized_query in description:
                    score += 60
                if normalized_query in search_text:
                    score += 20

                for token in tokens:
                    if token == page_id:
                        score += 120
                    elif token in title:
                        score += 24
                    elif token in description:
                        score += 12
                    elif token in search_text:
                        score += 2

                if score > 0:
                    results.append((score, page, matched_aliases[:5]))

        results.sort(key=lambda item: (-item[0], item[1]["type"], item[1]["id"]))
        return {
            "query": query,
            "normalized_query": normalized_query,
            "results": [
                self._search_entry(page, score, matched_aliases)
                for score, page, matched_aliases in results[:requested_limit]
            ],
        }

    def get(self, id_or_alias_or_url: str, *, max_body_chars: int = MAX_BODY_CHARS) -> dict[str, Any]:
        self.refresh_if_needed()
        page = self.resolve(id_or_alias_or_url)
        if page is None:
            return {
                "found": False,
                "query": id_or_alias_or_url,
                "candidates": self.search(id_or_alias_or_url, limit=5)["results"],
            }
        return {"found": True, "page": trim_body(page, max_body_chars=max_body_chars)}

    def related(
        self,
        id_or_alias_or_url: str,
        *,
        relation: str | None = None,
    ) -> dict[str, Any]:
        self.refresh_if_needed()
        page = self.resolve(id_or_alias_or_url)
        if page is None:
            return {"found": False, "query": id_or_alias_or_url, "related": []}

        related_entries = page.get("related", [])
        if relation:
            related_entries = [
                item for item in related_entries if item.get("relation") == relation
            ]

        enriched = []
        for item in related_entries:
            target = self.resolve(item.get("id", ""))
            enriched.append({**item, "description": target.get("description") if target else None})

        return {
            "found": True,
            "id": page["id"],
            "title": page["title"],
            "related": enriched,
        }

    def explain_diagnostic(self, code: str) -> dict[str, Any]:
        self.refresh_if_needed()
        page = self.resolve(code)
        if page is not None and page.get("type") == "diagnostic":
            return self._diagnostic_response(page)

        candidates = [
            entry
            for entry in self.search(code, page_type="diagnostic", limit=5)["results"]
        ]
        if not candidates:
            return {"found": False, "query": code, "candidates": []}

        candidate = self.resolve(candidates[0]["id"])
        if candidate is None:
            return {"found": False, "query": code, "candidates": candidates}
        return self._diagnostic_response(candidate, candidates=candidates)

    def resolve(self, id_or_alias_or_url: str) -> dict[str, Any] | None:
        key = normalize_lookup_key(id_or_alias_or_url)
        with self._lock:
            return self._pages_by_key.get(key)

    def _diagnostic_response(
        self,
        page: dict[str, Any],
        *,
        candidates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        standards = []
        edt_checks = []
        for item in page.get("related", []):
            target = self.resolve(item.get("id", ""))
            enriched = {**item, "description": target.get("description") if target else None}
            if item.get("relation") == "standard":
                standards.append(enriched)
            elif item.get("relation") == "edt_check":
                edt_checks.append(enriched)

        return {
            "found": True,
            "diagnostic": trim_body(page),
            "standards": standards,
            "edt_checks": edt_checks,
            "candidates": candidates or [],
        }

    def _search_entry(
        self,
        page: dict[str, Any],
        score: int,
        matched_aliases: list[str],
    ) -> dict[str, Any]:
        return {
            "id": page["id"],
            "type": page["type"],
            "title": page["title"],
            "description": page["description"],
            "url": page["url"],
            "markdown_url": page["markdown_url"],
            "score": score,
            "matched_aliases": matched_aliases,
            "related": page.get("related", [])[:8],
        }

    def _load_payload(self, *, force_refresh: bool) -> tuple[str, str]:
        if self.pages_path is not None:
            try:
                return self.pages_path.read_text(encoding="utf-8"), str(self.pages_path)
            except OSError as error:
                raise IndexLoadError(f"could not read {self.pages_path}: {error}") from error

        cache_path = self.cache_dir / "pages.jsonl"
        if not force_refresh and cache_path.is_file():
            return cache_path.read_text(encoding="utf-8"), str(cache_path)

        try:
            payload = self._fetch_index()
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(payload, encoding="utf-8")
            return payload, self.index_url
        except (OSError, URLError) as error:
            if cache_path.is_file():
                return cache_path.read_text(encoding="utf-8"), str(cache_path)
            raise IndexLoadError(f"could not load index from {self.index_url}: {error}") from error

    def _fetch_index(self) -> str:
        request = Request(
            self.index_url,
            headers={
                "Accept": "application/jsonl,text/plain,*/*",
                "User-Agent": "v8std-mcp/1.0",
            },
        )
        with urlopen(request, timeout=self.request_timeout) as response:
            return response.read().decode("utf-8")

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
            pages.append(normalize_page_schema(page))

        if not pages:
            raise IndexLoadError("index is empty")
        return pages

    def _replace_index(
        self,
        pages: list[dict[str, Any]],
        source: str,
        payload: str,
    ) -> None:
        pages_by_id: dict[str, dict[str, Any]] = {}
        pages_by_key: dict[str, dict[str, Any]] = {}
        search_text_by_id: dict[str, str] = {}

        for page in pages:
            pages_by_id[page["id"]] = page
            for value in self._lookup_values(page):
                pages_by_key.setdefault(normalize_lookup_key(value), page)
            search_text_by_id[page["id"]] = " ".join(
                [
                    page.get("id", ""),
                    page.get("title", ""),
                    page.get("description", ""),
                    " ".join(page.get("aliases", [])),
                    page.get("body_markdown", ""),
                ]
            ).lower()

        self._pages = pages
        self._pages_by_id = pages_by_id
        self._pages_by_key = pages_by_key
        self._search_text_by_id = search_text_by_id
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
