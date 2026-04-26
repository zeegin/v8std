#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_social_cards import (  # noqa: E402
    build_page_metadata,
    discover_project_root,
    extract_front_matter,
    load_project,
    normalize_description,
    strip_markdown,
)


LLMS_TXT = "llms.txt"
LLMS_FULL_TXT = "llms-full.txt"
AI_DIR = "ai"
PAGES_JSONL = "pages.jsonl"
GRAPH_JSON = "graph.json"
SEARCH_ALIASES_JSON = "search-aliases.json"

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
DIRECT_URL_RE = re.compile(r"https?://[^\s)>\"']+")
MARKER_RE = re.compile(
    r"^#{6}\s+(?P<marker>#std\d+|(?:bslls|acc|v8cs):[A-Za-z0-9_-]+)\s*$",
    re.MULTILINE,
)
ACC_TITLE_CODE_RE = re.compile(r"\(ACC\s+(?P<code>\d+)\)", re.IGNORECASE)

TYPE_ORDER = {
    "standard": 0,
    "diagnostic": 1,
    "pattern": 2,
    "service": 3,
}


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)

    return result


def normalize_body(raw: str) -> str:
    _, content = extract_front_matter(raw)
    return content.replace("\r\n", "\n").replace("\r", "\n").strip()


def relative_route(relative: Path) -> str:
    if relative.name == "index.md":
        url_path = "/".join(relative.parts[:-1])
    else:
        url_path = "/".join(relative.with_suffix("").parts)
    return f"{url_path}/" if url_path else ""


def classify_page(relative: Path) -> str:
    parts = relative.parts
    if len(parts) == 2 and parts[0] == "std" and relative.stem.isdigit():
        return "standard"
    if len(parts) >= 3 and parts[0] == "diagnostics" and relative.name != "index.md":
        return "diagnostic"
    if parts and parts[0] == "patterns":
        return "pattern"
    return "service"


def fallback_page_id(relative: Path, page_type: str) -> str:
    parts = relative.parts
    if relative == Path("index.md"):
        return "home"
    if page_type == "standard":
        return f"std{relative.stem}"
    if page_type == "diagnostic":
        family = parts[1]
        if family == "acc":
            return f"acc:{relative.stem}"
        if family == "bslls":
            return f"bslls:{relative.stem}"
        if family == "v8-code-style":
            return f"v8cs:{relative.stem}"

    route = relative_route(relative).strip("/")
    normalized = route.replace("/", ":").replace("-", "_")
    return normalized or relative.stem


def build_page_id(relative: Path, content: str, page_type: str) -> str:
    match = MARKER_RE.search(content)
    if match:
        marker = match.group("marker")
        if marker.startswith("#std"):
            return marker[1:]
        return marker
    return fallback_page_id(relative, page_type)


def build_aliases(page_id: str, relative: Path, page_type: str, title: str) -> list[str]:
    aliases = [page_id]

    if page_type == "standard" and page_id.startswith("std"):
        number = page_id.removeprefix("std")
        aliases.extend(
            [
                f"#std{number}",
                f"std{number}",
                f"std {number}",
                f"стандарт {number}",
            ]
        )
    elif page_type == "diagnostic" and page_id.startswith("acc:"):
        code = page_id.split(":", 1)[1]
        aliases.extend(
            [
                f"#acc:{code}",
                f"acc {code}",
                f"acc{code}",
                f"апк {code}",
                f"АПК:{code}",
            ]
        )
    elif page_type == "diagnostic" and page_id.startswith("bslls:"):
        code = page_id.split(":", 1)[1]
        aliases.extend([f"#bslls:{code}", code])
    elif page_type == "diagnostic" and page_id.startswith("v8cs:"):
        code = page_id.split(":", 1)[1]
        aliases.extend(
            [
                f"#v8cs:{code}",
                code,
                f"edt {code}",
                f"edt:{code}",
            ]
        )

    acc_title_match = ACC_TITLE_CODE_RE.search(title)
    if acc_title_match:
        aliases.append(f"ACC {acc_title_match.group('code')}")

    if page_type not in {"standard", "diagnostic"} and relative.name != "index.md":
        aliases.append(relative.stem)

    return dedupe(aliases)


def extract_source_urls(content: str) -> list[str]:
    urls = []
    for url in DIRECT_URL_RE.findall(content):
        urls.append(url.rstrip(".,;:"))
    return dedupe(urls)


def extract_markdown_links(content: str) -> list[tuple[str, str]]:
    return [(strip_markdown(text), target.strip()) for text, target in MARKDOWN_LINK_RE.findall(content)]


def local_link_target(source: Path, docs_dir: Path, target: str) -> Path | None:
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        return None

    normalized = unquote(target.split("#", 1)[0].split("?", 1)[0]).strip()
    if not normalized or normalized.startswith("/"):
        return None

    candidate = (source.parent / normalized).resolve()
    if candidate.is_dir():
        candidate = candidate / "index.md"
    elif candidate.suffix == "":
        md_candidate = candidate.with_suffix(".md")
        index_candidate = candidate / "index.md"
        if md_candidate.exists():
            candidate = md_candidate
        elif index_candidate.exists():
            candidate = index_candidate

    try:
        return candidate.relative_to(docs_dir.resolve())
    except ValueError:
        return None


def relation_kind(page: dict, target: dict) -> str:
    page_type = page["type"]
    target_type = target["type"]
    page_id = page["id"]
    target_id = target["id"]

    if page_type == "standard" and target_type == "diagnostic":
        return "diagnostic"
    if page_type == "diagnostic" and target_type == "standard":
        return "standard"
    if page_id.startswith("acc:") and target_id.startswith("v8cs:"):
        return "edt_check"
    if page_type == "diagnostic" and target_type == "diagnostic":
        return "related_diagnostic"
    if target_type == "standard":
        return "related_standard"
    return "related"


def related_entry(relation: str, target: dict) -> dict:
    return {
        "relation": relation,
        "id": target["id"],
        "type": target["type"],
        "title": target["title"],
        "url": target["url"],
        "source_path": target["source_path"],
    }


def sort_pages(pages: list[dict]) -> list[dict]:
    return sorted(
        pages,
        key=lambda page: (
            TYPE_ORDER.get(page["type"], 99),
            page["source_path"],
        ),
    )


def build_ai_page(source: Path, docs_dir: Path, project: dict) -> dict:
    relative = source.relative_to(docs_dir)
    raw = source.read_text(encoding="utf-8")
    content = normalize_body(raw)
    page_type = classify_page(relative)
    page_id = build_page_id(relative, content, page_type)
    metadata = build_page_metadata(source, docs_dir, project)

    return {
        "id": page_id,
        "type": page_type,
        "title": metadata["seo_title"],
        "description": metadata["description"],
        "url": metadata["canonical"],
        "source_path": str(relative),
        "aliases": build_aliases(page_id, relative, page_type, metadata["seo_title"]),
        "related": [],
        "source_urls": extract_source_urls(content),
        "body_markdown": content,
        "_links": extract_markdown_links(content),
    }


def resolve_relations(pages: list[dict], docs_dir: Path) -> None:
    pages_by_source = {page["source_path"]: page for page in pages}

    for page in pages:
        source = docs_dir / page["source_path"]
        related: list[dict] = []
        seen: set[tuple[str, str]] = set()

        for _, target in page["_links"]:
            relative_target = local_link_target(source, docs_dir, target)
            if relative_target is None:
                continue

            target_page = pages_by_source.get(str(relative_target))
            if not target_page or target_page["id"] == page["id"]:
                continue

            relation = relation_kind(page, target_page)
            key = (relation, target_page["id"])
            if key in seen:
                continue

            seen.add(key)
            related.append(related_entry(relation, target_page))

        page["related"] = sorted(related, key=lambda item: (item["relation"], item["id"]))
        del page["_links"]


def build_graph(pages: list[dict]) -> dict:
    standard_to_diagnostics: dict[str, set[str]] = defaultdict(set)
    diagnostic_to_standards: dict[str, set[str]] = defaultdict(set)
    diagnostic_to_sources: dict[str, list[str]] = {}
    acc_to_edt: dict[str, set[str]] = defaultdict(set)

    for page in pages:
        if page["type"] == "standard":
            standard_to_diagnostics.setdefault(page["id"], set())
        if page["type"] == "diagnostic":
            diagnostic_to_standards.setdefault(page["id"], set())
            diagnostic_to_sources[page["id"]] = page["source_urls"]

        for item in page["related"]:
            if page["type"] == "standard" and item["type"] == "diagnostic":
                standard_to_diagnostics[page["id"]].add(item["id"])
                diagnostic_to_standards[item["id"]].add(page["id"])
            elif page["type"] == "diagnostic" and item["type"] == "standard":
                diagnostic_to_standards[page["id"]].add(item["id"])
                standard_to_diagnostics[item["id"]].add(page["id"])
            elif page["id"].startswith("acc:") and item["id"].startswith("v8cs:"):
                acc_to_edt[page["id"]].add(item["id"])

    diagnostics = {}
    for page in pages:
        if page["type"] != "diagnostic":
            continue
        diagnostics[page["id"]] = {
            "standards": sorted(diagnostic_to_standards.get(page["id"], set())),
            "sources": diagnostic_to_sources.get(page["id"], []),
            "edt_checks": sorted(acc_to_edt.get(page["id"], set())),
        }

    return {
        "standards": {
            key: sorted(value)
            for key, value in sorted(standard_to_diagnostics.items())
        },
        "diagnostics": dict(sorted(diagnostics.items())),
        "acc_to_edt": {
            key: sorted(value)
            for key, value in sorted(acc_to_edt.items())
        },
        "nodes": [
            {
                "id": page["id"],
                "type": page["type"],
                "title": page["title"],
                "url": page["url"],
                "source_path": page["source_path"],
            }
            for page in pages
        ],
    }


def related_ids(page: dict, relation: str) -> list[str]:
    return [item["id"] for item in page["related"] if item["relation"] == relation]


def format_id_list(ids: list[str], limit: int = 8) -> str:
    if not ids:
        return "нет"
    visible = ids[:limit]
    suffix = "" if len(ids) <= limit else f", +{len(ids) - limit}"
    return ", ".join(visible) + suffix


def page_link(page: dict, label: str | None = None) -> str:
    return f"[{label or page['title']}]({page['url']})"


def build_llms_txt(index: dict) -> str:
    project = index["project"]
    pages = index["pages"]
    site_url = (project.get("site_url") or "").rstrip("/")

    standards = [page for page in pages if page["type"] == "standard"]
    diagnostics = [page for page in pages if page["type"] == "diagnostic"]
    patterns = [page for page in pages if page["type"] == "pattern"]
    services = [page for page in pages if page["type"] == "service"]

    lines = [
        f"# {project.get('site_name', 'v8std.ru')}",
        "",
        f"> {project.get('site_description', '').strip()}",
        "",
        "Этот файл является компактной картой сайта для LLM. Полный корпус и машинные индексы лежат в отдельных статических файлах.",
        "",
        "## Machine-Readable Files",
        f"- [Full Markdown corpus]({site_url}/{LLMS_FULL_TXT}): полный текст всех Markdown-страниц без front matter.",
        f"- [Pages JSONL]({site_url}/{AI_DIR}/{PAGES_JSONL}): JSONL-индекс страниц, алиасов, связей и исходных Markdown-текстов.",
        f"- [Graph JSON]({site_url}/{AI_DIR}/{GRAPH_JSON}): граф связей стандартов, диагностик, EDT-проверок и внешних источников.",
        f"- [Search aliases JSON]({site_url}/{AI_DIR}/{SEARCH_ALIASES_JSON}): нормализованные формы запросов для стандартов и диагностик.",
        "",
        "## Standards",
    ]

    for page in standards:
        diagnostics_ids = related_ids(page, "diagnostic")
        lines.append(
            f"- {page_link(page, '#' + page['id'])}: {page['title']}. "
            f"Diagnostics: {format_id_list(diagnostics_ids)}. "
            f"{normalize_description(page['description'], 140)}"
        )

    lines.extend(["", "## Diagnostics"])
    for page in diagnostics:
        standards_ids = related_ids(page, "standard")
        edt_ids = related_ids(page, "edt_check")
        details = [f"Standards: {format_id_list(standards_ids)}"]
        if edt_ids:
            details.append(f"EDT: {format_id_list(edt_ids)}")
        lines.append(
            f"- {page_link(page, page['id'])}: {'; '.join(details)}. "
            f"{normalize_description(page['description'], 140)}"
        )

    lines.extend(["", "## Patterns"])
    for page in patterns:
        lines.append(f"- {page_link(page)}: {normalize_description(page['description'], 140)}")

    lines.extend(["", "## Service Pages"])
    for page in services:
        lines.append(f"- {page_link(page)}: {normalize_description(page['description'], 140)}")

    return "\n".join(lines).rstrip() + "\n"


def build_llms_full_txt(index: dict) -> str:
    project = index["project"]
    lines = [
        f"# {project.get('site_name', 'v8std.ru')} - полный корпус",
        "",
        "> Полный Markdown/plain-text корпус сайта для LLM и локальной индексации.",
        "",
    ]

    current_type = None
    for page in index["pages"]:
        if page["type"] != current_type:
            current_type = page["type"]
            lines.extend(["", f"## {current_type}", ""])

        related = ", ".join(f"{item['relation']}:{item['id']}" for item in page["related"]) or "нет"
        sources = ", ".join(page["source_urls"]) or "нет"
        aliases = ", ".join(page["aliases"]) or "нет"
        lines.extend(
            [
                f"### {page['id']} - {page['title']}",
                f"URL: {page['url']}",
                f"Source path: {page['source_path']}",
                f"Aliases: {aliases}",
                f"Related: {related}",
                f"External sources: {sources}",
                "",
                page["body_markdown"],
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def build_pages_jsonl(pages: list[dict]) -> str:
    lines = []
    for page in pages:
        payload = {
            key: page[key]
            for key in (
                "id",
                "type",
                "title",
                "description",
                "url",
                "source_path",
                "aliases",
                "related",
                "source_urls",
                "body_markdown",
            )
        }
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + "\n"


def build_search_aliases(pages: list[dict]) -> dict:
    aliases = []
    seen: set[tuple[str, str]] = set()

    for page in pages:
        for alias in page["aliases"]:
            key = (alias.casefold(), page["id"])
            if key in seen:
                continue
            seen.add(key)
            aliases.append(
                {
                    "query": alias,
                    "target_id": page["id"],
                    "type": page["type"],
                    "title": page["title"],
                    "url": page["url"],
                }
            )

    aliases.sort(key=lambda item: (item["query"].casefold(), item["target_id"]))
    return {"aliases": aliases}


def build_site_ai_index(root: Path) -> dict:
    project = load_project(root)
    docs_dir = root / project.get("docs_dir", "docs")
    pages = sort_pages(
        [
            build_ai_page(source, docs_dir, project)
            for source in sorted(docs_dir.rglob("*.md"))
        ]
    )
    resolve_relations(pages, docs_dir)

    return {
        "project": project,
        "docs_dir": docs_dir,
        "pages": pages,
        "graph": build_graph(pages),
    }


def write_ai_artifacts(index: dict) -> None:
    docs_dir: Path = index["docs_dir"]
    ai_dir = docs_dir / AI_DIR
    ai_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / LLMS_TXT).write_text(build_llms_txt(index), encoding="utf-8")
    (docs_dir / LLMS_FULL_TXT).write_text(build_llms_full_txt(index), encoding="utf-8")
    (ai_dir / PAGES_JSONL).write_text(build_pages_jsonl(index["pages"]), encoding="utf-8")
    (ai_dir / GRAPH_JSON).write_text(
        json.dumps(index["graph"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (ai_dir / SEARCH_ALIASES_JSON).write_text(
        json.dumps(build_search_aliases(index["pages"]), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    root = discover_project_root()
    write_ai_artifacts(build_site_ai_index(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
