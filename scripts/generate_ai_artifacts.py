#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
import textwrap
from argparse import ArgumentParser
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlsplit

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
from v8std_retrieval_rules import RetrievalRules  # noqa: E402


LLMS_TXT = "llms.txt"
LLMS_FULL_TXT = "llms-full.txt"
AI_DIR = "ai"
PAGES_JSONL = "pages.jsonl"
REMOVED_AI_ARTIFACTS = ("graph.json", "search-aliases.json")

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
DIRECT_URL_RE = re.compile(r"https?://[^\s)>\"']+")
MARKER_RE = re.compile(
    r"^#{6}\s+(?P<marker>#std\d+|(?:bslls|acc|v8cs):[A-Za-z0-9_-]+)\s*$",
    re.MULTILINE,
)
ACC_TITLE_CODE_RE = re.compile(r"\(ACC\s+(?P<code>\d+)\)", re.IGNORECASE)
ADMONITION_RE = re.compile(
    r"^!!!\s+(?P<kind>[A-Za-z0-9_-]+)(?:\s+(?P<title>.+?))?\s*$"
)
TAB_RE = re.compile(r"^===\s+(?P<label>.+?)\s*$")
CODE_FENCE_RE = re.compile(r"^```(?P<language>[A-Za-z0-9_-]+)?(?:\s+.*)?$")
INLINEHILITE_CODE_RE = re.compile(r"`#![A-Za-z0-9_-]+(?:\s+([^`]+))?`")
ICON_SHORTCODE_RE = re.compile(r":[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+:")
IMAGE_WITH_ATTRS_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)(?:\{[^}]+\})?")
MARKDOWN_ATTR_RE = re.compile(r"(?<=\))\{[^}\n]+\}|\{\s*\.[^}\n]+\}")
STRIKE_LINK_RE = re.compile(r"~(\[[^\]]+\]\([^)]+\))~")
HTML_ANCHOR_RE = re.compile(
    r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.IGNORECASE,
)
HTML_HEADING_RE = re.compile(
    r"^\s*<h(?P<level>[1-6])\b[^>]*>(?P<content>.*?)</h[1-6]>\s*$",
    re.IGNORECASE,
)
HTML_ARIA_LABEL_RE = re.compile(
    r"<[^>]+\baria-label=[\"']([^\"']+)[\"'][^>]*>.*?</[^>]+>",
    re.IGNORECASE,
)
HTML_TAG_RE = re.compile(r"<[^>]+>")
HTML_WRAPPER_LINE_RE = re.compile(
    r"^\s*</?(?:div|span|section|p|button|table|thead|tbody|tr|td|th|script|html|body|svg|path|use)\b[^>]*>\s*$",
    re.IGNORECASE,
)
HTML_OPEN_TAG_START_RE = re.compile(
    r"^\s*<(?:a|button|div|span|section|p|table|thead|tbody|tr|td|th|script|svg|path|use)\b[^>]*$",
    re.IGNORECASE,
)
REDIRECT_RE = re.compile(r"window\.location\.replace\([\"']([^\"']+)[\"']\);")
KEYBOARD_KEY_RE = re.compile(r"\+\+([^\n]+?)\+\+")
MARKER_HEADING_RE = re.compile(
    r"^#{6}\s+(?P<marker>#std\d+|(?:bslls|acc|v8cs):[A-Za-z0-9_-]+)\s*$"
)
DEEP_HEADING_RE = re.compile(r"^#{6}\s+(.+?)\s*$")

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


def llms_ignored(front_matter: dict) -> bool:
    llms = front_matter.get("llms")
    if isinstance(llms, dict):
        return llms.get("ignore") is True
    return False


def clean_label(value: str) -> str:
    label = value.strip().strip('"').strip("'")
    label = ICON_SHORTCODE_RE.sub("", label)
    label = strip_markdown(label)
    return re.sub(r"\s+", " ", label).strip()


def leading_spaces(value: str) -> int:
    return len(value) - len(value.lstrip(" "))


def clean_keyboard_key(match: re.Match[str]) -> str:
    key_map = {
        "ctrl": "Ctrl",
        "shift": "Shift",
        "alt": "Alt",
        "cmd": "Cmd",
        "command": "Cmd",
        "enter": "Enter",
        "space": "Space",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
        "tab": "Tab",
        "esc": "Esc",
    }
    parts = []
    for part in match.group(1).split("+"):
        lower = part.lower()
        if lower in key_map:
            parts.append(key_map[lower])
        elif re.fullmatch(r"f\d{1,2}", part, re.I) or re.fullmatch(r"[a-z]", part, re.I):
            parts.append(part.upper())
        else:
            parts.append(part)
    return "+".join(parts)


def clean_inline_markup(line: str) -> str:
    def replace_inlinehilite(match: re.Match[str]) -> str:
        content = (match.group(1) or "").strip()
        return f"`{content}`" if content else "`#!`"

    line = INLINEHILITE_CODE_RE.sub(replace_inlinehilite, line)
    line = STRIKE_LINK_RE.sub(r"\1", line)
    line = KEYBOARD_KEY_RE.sub(clean_keyboard_key, line)
    line = IMAGE_WITH_ATTRS_RE.sub(
        lambda match: f"Изображение: {clean_label(match.group(1)) or match.group(2)} ({match.group(2)})",
        line,
    )
    line = MARKDOWN_ATTR_RE.sub("", line)
    line = ICON_SHORTCODE_RE.sub("", line)
    return line


def clean_html_markup(line: str) -> str | None:
    redirect_match = REDIRECT_RE.search(line)
    if redirect_match:
        return f"Redirect: {redirect_match.group(1)}"

    heading_match = HTML_HEADING_RE.match(line)
    if heading_match:
        level = min(int(heading_match.group("level")) + 2, 6)
        content = clean_label(heading_match.group("content"))
        return f"{'#' * level} {content}" if content else None

    if HTML_WRAPPER_LINE_RE.match(line):
        return None

    line = re.sub(r"<br\s*/?>", "; ", line, flags=re.IGNORECASE)
    line = HTML_ANCHOR_RE.sub(
        lambda match: f"[{clean_label(match.group(2))}]({match.group(1)})",
        line,
    )
    line = HTML_ARIA_LABEL_RE.sub(lambda match: match.group(1), line)
    line = HTML_TAG_RE.sub("", line)
    line = unescape(line)
    return line


def normalize_blank_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    previous_blank = False

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            if not previous_blank:
                result.append("")
            previous_blank = True
            continue
        result.append(stripped)
        previous_blank = False

    while result and not result[0]:
        result.pop(0)
    while result and not result[-1]:
        result.pop()

    return result


def clean_llm_markdown(content: str) -> str:
    lines: list[str] = []
    dedent_stack: list[int] = []
    in_code_block = False
    in_multiline_html_tag = False
    code_block_indent = 0

    for raw_line in content.splitlines():
        if raw_line.strip():
            while dedent_stack and leading_spaces(raw_line) < sum(dedent_stack):
                dedent_stack.pop()

        dedent = sum(dedent_stack)
        line = raw_line[dedent:] if raw_line.startswith(" " * dedent) else raw_line.lstrip()
        stripped_line = line.lstrip()

        if stripped_line.strip() == "```":
            in_code_block = not in_code_block
            code_block_indent = 0
            lines.append("```")
            continue

        fence_match = CODE_FENCE_RE.match(stripped_line)
        if not in_code_block and fence_match:
            language = fence_match.group("language") or ""
            code_block_indent = leading_spaces(line)
            lines.append(f"```{language}")
            in_code_block = not in_code_block
            continue


        if in_code_block:
            if code_block_indent and line.startswith(" " * code_block_indent):
                line = line[code_block_indent:]
            lines.append(line.rstrip())
            continue

        if in_multiline_html_tag:
            if ">" in line:
                in_multiline_html_tag = False
            continue

        if HTML_OPEN_TAG_START_RE.match(line):
            in_multiline_html_tag = True
            continue

        marker_match = MARKER_HEADING_RE.match(line)
        if marker_match:
            lines.append(f"ID: {marker_match.group('marker')}")
            continue

        deep_heading_match = DEEP_HEADING_RE.match(line)
        if deep_heading_match:
            lines.append(f"#### {deep_heading_match.group(1).strip()}")
            continue

        tab_match = TAB_RE.match(line)
        if tab_match:
            label = clean_label(tab_match.group("label"))
            lines.append(f"#### {label}" if label else "#### Вкладка")
            dedent_stack.append(4)
            continue

        admonition_match = ADMONITION_RE.match(line)
        if admonition_match:
            title = clean_label(admonition_match.group("title") or admonition_match.group("kind"))
            lines.append(f"#### {title}")
            dedent_stack.append(4)
            continue

        line = clean_inline_markup(line)
        cleaned_html = clean_html_markup(line)
        if cleaned_html is None:
            continue
        line = cleaned_html
        if line.strip():
            lines.append(line.rstrip())
        else:
            lines.append("")

    return "\n".join(normalize_blank_lines(lines)).strip()


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


def build_aliases(
    page_id: str,
    relative: Path,
    page_type: str,
    title: str,
    retrieval_rules: RetrievalRules | None = None,
) -> list[str]:
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

    if retrieval_rules is not None:
        aliases.extend(retrieval_rules.aliases_for_page(page_id))

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


def canonical_page_url(project: dict, relative: Path) -> str:
    site_url = (project.get("site_url") or "").rstrip("/")
    route = relative_route(relative)
    path = f"/{route}" if route else "/"
    return f"{site_url}{path}" if site_url else path


def canonical_markdown_url(project: dict, relative: Path) -> str:
    site_url = (project.get("site_url") or "").rstrip("/")
    path = f"/{relative.as_posix()}"
    return f"{site_url}{path}" if site_url else path


def absolute_internal_url(source: Path, docs_dir: Path, project: dict, target: str) -> str | None:
    target = target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None

    if target.startswith("#"):
        return f"{canonical_page_url(project, source.relative_to(docs_dir))}{target}"

    if target.startswith("/") and not target.startswith("//"):
        site_url = (project.get("site_url") or "").rstrip("/")
        return f"{site_url}{target}" if site_url else target

    relative_target = local_link_target(source, docs_dir, target)
    if relative_target is None:
        return None

    parsed = urlsplit(target)
    suffix = ""
    if parsed.query:
        suffix += f"?{parsed.query}"
    if parsed.fragment:
        suffix += f"#{parsed.fragment}"
    return f"{canonical_page_url(project, relative_target)}{suffix}"


def normalize_internal_markdown_links(
    markdown: str,
    source: Path,
    docs_dir: Path,
    project: dict,
) -> str:
    lines: list[str] = []
    in_code_block = False

    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            lines.append(line)
            in_code_block = not in_code_block
            continue

        if in_code_block:
            lines.append(line)
            continue

        def replace_link(match: re.Match[str]) -> str:
            absolute_url = absolute_internal_url(source, docs_dir, project, match.group(2))
            if absolute_url is None:
                return match.group(0)
            return f"[{match.group(1)}]({absolute_url})"

        lines.append(MARKDOWN_LINK_RE.sub(replace_link, line))

    return "\n".join(lines).strip()


def normalize_title_for_compare(value: str) -> str:
    text = clean_label(value)
    text = re.sub(r"^#?std\d+\s*[:.-]?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:bslls|acc|v8cs):[A-Za-z0-9_-]+\s*[:.-]?\s*", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip().casefold()


def remove_duplicate_title_heading(markdown: str, title: str) -> str:
    title_key = normalize_title_for_compare(title)
    if not title_key:
        return markdown

    lines = markdown.splitlines()
    for index, line in enumerate(lines[:5]):
        if not line.startswith("# "):
            continue

        heading_key = normalize_title_for_compare(line.removeprefix("# "))
        if heading_key and (heading_key == title_key or title_key.endswith(heading_key)):
            del lines[index]
            if index < len(lines) and not lines[index].strip():
                del lines[index]
            break

    return "\n".join(lines).strip()


def wrap_llm_markdown_lines(markdown: str, width: int = 480) -> str:
    lines: list[str] = []
    in_code_block = False

    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            lines.append(line)
            in_code_block = not in_code_block
            continue

        if in_code_block or len(line) <= width or not line.strip():
            lines.append(line)
            continue

        list_match = re.match(r"^((?:[-*+]|\d+[.)])\s+)(.+)$", line)
        if list_match:
            prefix = list_match.group(1)
            wrapped = textwrap.wrap(
                list_match.group(2),
                width=width,
                initial_indent=prefix,
                subsequent_indent=" " * len(prefix),
                break_long_words=False,
                break_on_hyphens=False,
            )
        else:
            wrapped = textwrap.wrap(
                line,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )

        lines.extend(wrapped or [line])

    return "\n".join(lines).strip()


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
        "markdown_url": target["markdown_url"],
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


def build_ai_page(
    source: Path,
    docs_dir: Path,
    project: dict,
    retrieval_rules: RetrievalRules | None = None,
) -> dict:
    relative = source.relative_to(docs_dir)
    raw = source.read_text(encoding="utf-8")
    front_matter, content = extract_front_matter(raw)
    content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    page_type = classify_page(relative)
    page_id = build_page_id(relative, content, page_type)
    metadata = build_page_metadata(source, docs_dir, project)
    body_markdown = clean_llm_markdown(content)
    body_markdown = normalize_internal_markdown_links(body_markdown, source, docs_dir, project)
    body_markdown = remove_duplicate_title_heading(body_markdown, metadata["seo_title"])
    body_markdown = wrap_llm_markdown_lines(body_markdown)

    return {
        "id": page_id,
        "type": page_type,
        "title": metadata["seo_title"],
        "description": metadata["description"],
        "url": metadata["canonical"],
        "markdown_url": canonical_markdown_url(project, relative),
        "source_path": str(relative),
        "aliases": build_aliases(
            page_id,
            relative,
            page_type,
            metadata["seo_title"],
            retrieval_rules,
        ),
        "related": [],
        "source_urls": extract_source_urls(content),
        "body_markdown": body_markdown,
        "_llms_ignored": llms_ignored(front_matter),
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


def related_ids(page: dict, relation: str) -> list[str]:
    return [item["id"] for item in page["related"] if item["relation"] == relation]


def format_id_list(ids: list[str], limit: int = 8) -> str:
    if not ids:
        return "нет"
    visible = ids[:limit]
    suffix = "" if len(ids) <= limit else f", +{len(ids) - limit}"
    return ", ".join(visible) + suffix


def page_markdown_link(page: dict, label: str | None = None) -> str:
    return f"[{label or page['title']}]({page['markdown_url']})"


def canonical_url(value: str) -> str:
    return value.split("#", 1)[0].rstrip("/")


def ignored_text_refs(page: dict) -> list[str]:
    return [f"#{page['id']}"]


def build_ignored_ref_context(ignored_pages: list[dict]) -> dict:
    quick_refs = []
    pages = []
    for page in ignored_pages:
        quick_refs.append(page["url"])
        text_refs = ignored_text_refs(page)
        quick_refs.extend(text_refs)
        pages.append({**page, "_ignored_text_refs": text_refs})

    return {
        "pages": pages,
        "urls": {canonical_url(page["url"]) for page in ignored_pages},
        "quick_re": re.compile("|".join(re.escape(ref) for ref in quick_refs))
        if quick_refs
        else None,
    }


def strip_ignored_plain_text_refs(value: str, ignored_refs: dict) -> str:
    quick_re = ignored_refs["quick_re"]
    if not quick_re or not quick_re.search(value):
        return value

    result = value

    for page in ignored_refs["pages"]:
        title = re.escape(page["title"])

        for text_ref in page["_ignored_text_refs"]:
            result = re.sub(
                rf"\s*{re.escape(text_ref)}:?\s*{title}",
                "",
                result,
                flags=re.IGNORECASE,
            )
            result = re.sub(
                rf"\s*{re.escape(text_ref)}\b",
                "",
                result,
                flags=re.IGNORECASE,
            )

    return re.sub(r"\s+", " ", result).strip(" ,;.")


def strip_ignored_markdown_refs(markdown: str, ignored_refs: dict) -> str:
    quick_re = ignored_refs["quick_re"]
    if not quick_re or not quick_re.search(markdown):
        return markdown

    ignored_urls = ignored_refs["urls"]
    lines: list[str] = []
    in_code_block = False

    def is_ignored_target(target: str) -> bool:
        return canonical_url(target) in ignored_urls

    def replace_link(match: re.Match) -> str:
        if is_ignored_target(match.group(2)):
            return ""
        return match.group(0)

    def replace_url(match: re.Match) -> str:
        if is_ignored_target(match.group(0)):
            return ""
        return match.group(0)

    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            lines.append(line)
            in_code_block = not in_code_block
            continue

        if in_code_block:
            lines.append(line)
            continue

        if not quick_re.search(line):
            lines.append(line)
            continue

        cleaned = MARKDOWN_LINK_RE.sub(replace_link, line)
        cleaned = DIRECT_URL_RE.sub(replace_url, cleaned)
        cleaned = strip_ignored_plain_text_refs(cleaned, ignored_refs)
        cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned).strip()
        cleaned = re.sub(r"^[-*+]\s*$", "", cleaned).strip()

        if cleaned in {"", "См", "См.", "см", "см."}:
            continue

        lines.append(cleaned)

    return "\n".join(lines).strip()


def llm_visible_pages(pages: list[dict]) -> list[dict]:
    ignored_pages = [page for page in pages if page.get("_llms_ignored", False)]
    ignored_ids = {page["id"] for page in ignored_pages}
    ignored_refs = build_ignored_ref_context(ignored_pages)
    visible_pages = []

    for page in pages:
        if page["id"] in ignored_ids:
            continue

        visible_page = dict(page)
        visible_page["description"] = strip_ignored_plain_text_refs(
            page["description"],
            ignored_refs,
        )
        visible_page["body_markdown"] = strip_ignored_markdown_refs(
            page["body_markdown"],
            ignored_refs,
        )
        visible_page["related"] = [
            item for item in page["related"] if item["id"] not in ignored_ids
        ]
        visible_pages.append(visible_page)

    return visible_pages


def append_metadata_values(
    lines: list[str],
    label: str,
    values: list[str],
    *,
    inline_limit: int = 180,
) -> None:
    if not values:
        lines.append(f"{label}: нет")
        return

    inline = ", ".join(values)
    if len(inline) <= inline_limit:
        lines.append(f"{label}: {inline}")
        return

    lines.append(f"{label}:")
    lines.extend(f"- {value}" for value in values)


def build_llms_txt(index: dict) -> str:
    project = index["project"]
    pages = llm_visible_pages(index["pages"])
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
        "Этот файл является компактной картой сайта для LLM. Полный корпус и машинный индекс лежат в отдельных статических файлах.",
        "Для каждой публичной страницы также публикуется очищенная Markdown-версия по исходному пути `.md`: например, HTML `https://v8std.ru/std/437/` соответствует Markdown `https://v8std.ru/std/437.md`.",
        "",
        "## Machine-Readable Files",
        f"- [Full Markdown corpus]({site_url}/{LLMS_FULL_TXT}): очищенный полный текст всех Markdown-страниц без front matter и служебной разметки темы.",
        f"- [Pages JSONL]({site_url}/{AI_DIR}/{PAGES_JSONL}): JSONL-индекс страниц, алиасов, связей и очищенных Markdown-текстов.",
        "",
        "## Standards",
    ]

    for page in standards:
        diagnostics_ids = related_ids(page, "diagnostic")
        lines.append(
            f"- {page_markdown_link(page, '#' + page['id'])}: {page['title']}. "
            f"HTML: {page['url']}. "
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
            f"- {page_markdown_link(page, page['id'])}: HTML: {page['url']}. "
            f"{'; '.join(details)}. "
            f"{normalize_description(page['description'], 140)}"
        )

    lines.extend(["", "## Patterns"])
    for page in patterns:
        lines.append(
            f"- {page_markdown_link(page)}: HTML: {page['url']}. "
            f"{normalize_description(page['description'], 140)}"
        )

    lines.extend(["", "## Service Pages"])
    for page in services:
        lines.append(
            f"- {page_markdown_link(page)}: HTML: {page['url']}. "
            f"{normalize_description(page['description'], 140)}"
        )

    return "\n".join(lines).rstrip() + "\n"


def build_llms_full_txt(index: dict) -> str:
    project = index["project"]
    lines = [
        f"# {project.get('site_name', 'v8std.ru')} - полный корпус",
        "",
        "> Очищенный Markdown/plain-text корпус сайта для LLM и локальной индексации.",
        "",
    ]

    current_type = None
    pages = llm_visible_pages(index["pages"])
    for page in pages:
        if page["type"] != current_type:
            current_type = page["type"]
            lines.extend(["", f"## {current_type}", ""])

        related = [f"{item['relation']}:{item['id']}" for item in page["related"]]
        lines.extend(
            [
                f"### {page['id']} - {page['title']}",
                f"URL: {page['url']}",
                f"Markdown URL: {page['markdown_url']}",
                f"Source path: {page['source_path']}",
            ]
        )
        append_metadata_values(lines, "Aliases", page["aliases"])
        append_metadata_values(lines, "Related", related)
        append_metadata_values(lines, "External sources", page["source_urls"])
        lines.extend(["", page["body_markdown"], ""])

    return "\n".join(lines).rstrip() + "\n"


def build_pages_jsonl(pages: list[dict]) -> str:
    lines = []
    for page in llm_visible_pages(pages):
        payload = {
            key: page[key]
            for key in (
                "id",
                "type",
                "title",
                "description",
                "url",
                "markdown_url",
                "source_path",
                "aliases",
                "related",
                "source_urls",
                "body_markdown",
            )
        }
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + "\n"


def build_site_ai_index(root: Path) -> dict:
    project = load_project(root)
    docs_dir = root / project.get("docs_dir", "docs")
    retrieval_rules = RetrievalRules.load(root / "retrieval-rules.yml")
    pages = sort_pages(
        [
            build_ai_page(source, docs_dir, project, retrieval_rules)
            for source in sorted(docs_dir.rglob("*.md"))
        ]
    )
    resolve_relations(pages, docs_dir)

    return {
        "project": project,
        "docs_dir": docs_dir,
        "pages": pages,
    }


def write_ai_artifacts(index: dict) -> None:
    docs_dir: Path = index["docs_dir"]
    ai_dir = docs_dir / AI_DIR
    ai_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / LLMS_TXT).write_text(build_llms_txt(index), encoding="utf-8")
    (docs_dir / LLMS_FULL_TXT).write_text(build_llms_full_txt(index), encoding="utf-8")
    (ai_dir / PAGES_JSONL).write_text(build_pages_jsonl(index["pages"]), encoding="utf-8")
    for filename in REMOVED_AI_ARTIFACTS:
        (ai_dir / filename).unlink(missing_ok=True)


def build_page_markdown(page: dict) -> str:
    lines = [
        f"# {page['title']}",
        "",
        f"> {page['description']}",
        "",
        f"ID: {page['id']}",
        f"Type: {page['type']}",
        f"Canonical HTML: {page['url']}",
        f"Markdown URL: {page['markdown_url']}",
        f"Source path: {page['source_path']}",
    ]

    append_metadata_values(lines, "Aliases", page["aliases"])
    related = [
        f"{item['relation']}:{item['id']} ({item['markdown_url']}; HTML: {item['url']})"
        for item in page["related"]
    ]
    append_metadata_values(lines, "Related", related)
    append_metadata_values(lines, "External sources", page["source_urls"])
    lines.extend(["", "## Content", "", page["body_markdown"]])
    return "\n".join(lines).rstrip() + "\n"


def write_site_markdown_pages(index: dict, site_dir: Path) -> None:
    for page in llm_visible_pages(index["pages"]):
        output_path = site_dir / page["source_path"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_page_markdown(page), encoding="utf-8")


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        "--write-site-markdown",
        type=Path,
        help="Write public per-page Markdown files into an already built site directory.",
    )
    args = parser.parse_args()

    root = discover_project_root()
    index = build_site_ai_index(root)
    write_ai_artifacts(index)

    if args.write_site_markdown:
        write_site_markdown_pages(index, args.write_site_markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
