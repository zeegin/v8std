#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from collections import Counter
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont


CARD_WIDTH = 1200
CARD_HEIGHT = 630
MANIFEST_NAME = ".manifest.json"
PAGE_META_PARTIAL = "page_meta.html"
ROBOTS_TXT = "robots.txt"
MAX_TITLE_LINES = 3
MAX_DESCRIPTION_LINES = 2
HEADER_TOP = 56
HEADER_LEFT = 60
HEADER_GAP = 28
TITLE_LEFT = 64
TITLE_TOP = 170
TITLE_MAX_WIDTH = 940
DESCRIPTION_LEFT = 64
DESCRIPTION_TOP = 514
DESCRIPTION_MAX_WIDTH = 1040
TITLE_FONT_SIZES = (82, 78, 74, 70, 66)
SEO_DESCRIPTION_LENGTH = 180

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
TAG_RE = re.compile(r"<[^>]+>")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
INLINEHILITE_RE = re.compile(r"^#![A-Za-z0-9_-]+\s+(?P<content>.+)$", re.DOTALL)
WHITESPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"^https?://\S+$")
ACC_TITLE_RE = re.compile(r"\s*\(ACC\s+(?P<code>\d+)\)\s*$", re.IGNORECASE)
BSLLS_TITLE_RE = re.compile(r"\s*\((?P<code>[A-Za-z][A-Za-z0-9]+)\)\s*$")
STRONG_EMPHASIS_RE = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", re.DOTALL)
EMPHASIS_RE = re.compile(r"(?<!\*)\*(?=\S)(.+?)(?<=\S)\*(?!\*)", re.DOTALL)
UNDERSCORE_EMPHASIS_RE = re.compile(r"(?<!_)_(?=\S)(.+?)(?<=\S)_(?!_)", re.DOTALL)
STRIKETHROUGH_RE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.DOTALL)
SUBSCRIPT_RE = re.compile(r"(?<!~)~(?=\S)(.+?)(?<=\S)~(?!~)", re.DOTALL)


def find_font(*names: str) -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in [*names, *candidates]:
        if path and Path(path).exists():
            return path
    return None


def load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    preferred = find_font(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    if preferred:
        return ImageFont.truetype(preferred, size=size)
    return ImageFont.load_default()


def load_project(root: Path) -> dict:
    with (root / "zensical.toml").open("rb") as handle:
        config = tomllib.load(handle)
    return config.get("project", config)


def discover_project_root() -> Path:
    candidates: list[Path] = []

    env_root = os.environ.get("V8STD_REPO_ROOT")
    if env_root:
        candidates.append(Path(env_root).expanduser())

    cwd = Path.cwd().resolve()
    candidates.extend([cwd, *cwd.parents])

    script_path = Path(__file__).resolve()
    candidates.extend([script_path.parent, *script_path.parent.parents])

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "zensical.toml").is_file():
            return resolved

    raise FileNotFoundError(
        "Could not locate project root with zensical.toml. "
        "Run this command from the repository root or set V8STD_REPO_ROOT."
    )


def strip_markdown(value: str) -> str:
    text = IMAGE_RE.sub("", value)
    text = LINK_RE.sub(r"\1", text)
    text = TAG_RE.sub("", text)

    def normalize_inline_code(match: re.Match[str]) -> str:
        code = match.group(1).strip()
        inlinehilite = INLINEHILITE_RE.match(code)
        if inlinehilite:
            return inlinehilite.group("content").strip()
        return code

    text = INLINE_CODE_RE.sub(normalize_inline_code, text)

    previous = None
    while text != previous:
        previous = text
        text = STRONG_EMPHASIS_RE.sub(r"\2", text)
        text = EMPHASIS_RE.sub(r"\1", text)
        text = UNDERSCORE_EMPHASIS_RE.sub(r"\1", text)
        text = STRIKETHROUGH_RE.sub(r"\1", text)
        text = SUBSCRIPT_RE.sub(r"\1", text)

    return WHITESPACE_RE.sub(" ", text).strip()


def extract_front_matter(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text

    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    return data, text[match.end() :]


def extract_description(text: str) -> str:
    lines = text.splitlines()
    paragraph: list[str] = []
    in_code_block = False
    skip_indented_block = False

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```") or line.startswith("~~~"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if skip_indented_block:
            if not line:
                skip_indented_block = False
                continue
            if raw_line.startswith(("    ", "\t")):
                continue
            skip_indented_block = False
        if not line:
            if paragraph:
                break
            continue
        if line.startswith("#"):
            continue
        if line.startswith(("!!!", "???", ":::")):
            if paragraph:
                break
            skip_indented_block = True
            continue
        if raw_line.startswith(("    ", "\t")):
            if paragraph:
                break
            continue
        if line.startswith(("![](", "![", "|", "{", "<", "- ", "* ", "1. ", "1) ", ">")):
            if paragraph:
                break
            continue
        paragraph.append(line)

    return strip_markdown(" ".join(paragraph))


def truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value

    truncated = value[: limit + 1].rsplit(" ", 1)[0].rstrip()
    if not truncated:
        truncated = value[:limit].rstrip()
    return f"{truncated}..."


def normalize_description(value: str, limit: int = SEO_DESCRIPTION_LENGTH) -> str:
    return truncate_text(strip_markdown(value), limit)


def looks_like_url(value: str) -> bool:
    return bool(URL_RE.fullmatch(value.strip()))


def extract_list_summary(text: str, *, max_items: int = 3) -> str:
    lines = text.splitlines()
    items: list[str] = []
    in_code_block = False
    skip_indented_block = False

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```") or line.startswith("~~~"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if skip_indented_block:
            if not line:
                skip_indented_block = False
                continue
            if raw_line.startswith(("    ", "\t")):
                continue
            skip_indented_block = False
        if not line:
            continue
        if line == "###### Источник":
            break
        if line.startswith("#"):
            continue
        if line.startswith(("!!!", "???", ":::")):
            skip_indented_block = True
            continue
        if raw_line.startswith(("    ", "\t")):
            continue
        if not line.startswith(("- ", "* ")):
            continue
        item = strip_markdown(line[2:])
        if not item or looks_like_url(item):
            continue
        items.append(item.rstrip("."))
        if len(items) >= max_items:
            break

    return ". ".join(items)


def build_seo_title(relative: Path, title: str) -> str:
    if relative.parts[:2] == ("diagnostics", "acc") and relative.stem.isdigit():
        normalized = ACC_TITLE_RE.sub("", title).strip()
        suffix = f"АПК:{relative.stem}"
        if suffix not in normalized:
            return f"{normalized} {suffix}"
        return normalized

    if relative.parts[:2] == ("diagnostics", "bslls"):
        normalized = BSLLS_TITLE_RE.sub("", title).strip()
        suffix = f"BSLLS:{relative.stem}"
        if suffix not in normalized:
            return f"{normalized} {suffix}"
        return normalized

    if relative.parts and relative.parts[0] == "std" and relative.stem.isdigit():
        suffix = f"#std{relative.stem}"
        if suffix not in title:
            return f"{title} {suffix}"
    return title


def build_page_metadata(source: Path, docs_dir: Path, project: dict) -> dict:
    relative = source.relative_to(docs_dir)
    raw = source.read_text(encoding="utf-8")
    front_matter, content = extract_front_matter(raw)
    heading_match = HEADING_RE.search(content)

    title = (
        front_matter.get("social_title")
        or front_matter.get("title")
        or (strip_markdown(heading_match.group(1)) if heading_match else None)
        or source.stem.replace("-", " ")
    )
    seo_title = front_matter.get("seo_title") or build_seo_title(relative, title)
    extracted_description = extract_description(content)
    list_summary = extract_list_summary(content)
    paragraph_description = (
        extracted_description if extracted_description and not looks_like_url(extracted_description) else ""
    )

    if front_matter.get("description") or front_matter.get("social_description"):
        description_source = front_matter.get("description") or front_matter.get("social_description")
    elif paragraph_description:
        description_source = paragraph_description
    elif list_summary:
        description_source = f"{seo_title}. {list_summary}"
    elif relative == Path("index.md"):
        description_source = project.get("site_description", "") or seo_title
    else:
        description_source = seo_title or project.get("site_description", "")

    description = normalize_description(description_source)
    card_description = normalize_description(
        front_matter.get("social_description")
        or description
        or project.get("site_description")
    )

    if relative.name == "index.md":
        url_path = "/".join(relative.parts[:-1])
        output = (
            docs_dir / "assets" / "social" / relative.parent / "index.png"
            if relative.parts[:-1]
            else docs_dir / "assets" / "social" / "index.png"
        )
    else:
        url_path = "/".join(relative.with_suffix("").parts)
        output = docs_dir / "assets" / "social" / relative.with_suffix("") / "index.png"

    relative_url = f"{url_path}/" if url_path else ""
    site_url = project.get("site_url", "").rstrip("/")
    canonical = f"{site_url}/{relative_url}" if site_url else relative_url

    return {
        "source": str(relative),
        "page_url": relative_url,
        "title": title,
        "seo_title": seo_title,
        "description": description,
        "card_description": card_description,
        "output": output,
        "canonical": canonical,
        "section": " / ".join(relative.parts[:-1]) or project.get("site_name", ""),
    }


def split_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        probe = f"{current} {word}"
        width = draw.textbbox((0, 0), probe, font=font)[2]
        if width <= max_width:
            current = probe
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def fit_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
) -> tuple[list[str], bool]:
    lines = split_lines(draw, text, font, max_width)
    if len(lines) <= max_lines:
        return lines, False

    trimmed = lines[:max_lines]
    last = trimmed[-1]
    while last:
        probe = f"{last}..."
        width = draw.textbbox((0, 0), probe, font=font)[2]
        if width <= max_width:
            trimmed[-1] = probe
            break
        last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
    return trimmed, True


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    sizes: tuple[int, ...],
    *,
    bold: bool,
    max_width: int,
    max_lines: int,
) -> tuple[ImageFont.ImageFont, list[str]]:
    for size in sizes:
        font = load_font(size, bold=bold)
        lines, overflow = fit_lines(draw, text, font, max_width, max_lines)
        if not overflow:
            return font, lines

    fallback = load_font(sizes[-1], bold=bold)
    lines, _ = fit_lines(draw, text, fallback, max_width, max_lines)
    return fallback, lines


def text_height(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, spacing: int) -> int:
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    return (bbox[3] - bbox[1]) + spacing


def load_logo(logo_path: Path, size: int) -> Image.Image | None:
    if not logo_path.exists():
        return None

    logo = Image.open(logo_path).convert("RGBA")
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    logo.thumbnail((size, size))
    return logo


def render_card(page: dict, project: dict, colors: dict, logo_path: Path) -> Image.Image:
    image = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), colors["background"])
    draw = ImageDraw.Draw(image)

    brand_font = load_font(38, bold=True)
    description_font = load_font(28)
    title_font, title_lines = fit_font(
        draw,
        page["title"],
        TITLE_FONT_SIZES,
        bold=True,
        max_width=TITLE_MAX_WIDTH,
        max_lines=MAX_TITLE_LINES,
    )

    logo = load_logo(logo_path, 72)
    if logo is not None:
        image.alpha_composite(logo, (HEADER_LEFT, HEADER_TOP))

    brand_x = HEADER_LEFT + ((logo.width + HEADER_GAP) if logo is not None else 0)
    draw.text(
        (brand_x, HEADER_TOP + 6),
        project.get("site_name", "Documentation"),
        fill=colors["foreground"],
        font=brand_font,
    )

    current_y = TITLE_TOP
    title_step = text_height(draw, title_font, 18)
    for line in title_lines:
        draw.text((TITLE_LEFT, current_y), line, fill=colors["foreground"], font=title_font)
        current_y += title_step

    description_lines, _ = fit_lines(
        draw,
        page["card_description"],
        description_font,
        DESCRIPTION_MAX_WIDTH,
        MAX_DESCRIPTION_LINES,
    )
    description_step = text_height(draw, description_font, 10)
    current_y = DESCRIPTION_TOP
    for line in description_lines:
        draw.text(
            (DESCRIPTION_LEFT, current_y),
            line,
            fill=colors["foreground"],
            font=description_font,
        )
        current_y += description_step

    return image.convert("RGB")


def compute_hash(page: dict, project: dict, colors: dict, logo_path: Path) -> str:
    payload = {
        "title": page["title"],
        "description": page["card_description"],
        "canonical": page["canonical"],
        "background": colors["background"],
        "foreground": colors["foreground"],
        "site_name": project.get("site_name"),
        "logo": str(logo_path),
        "logo_mtime": logo_path.stat().st_mtime if logo_path.exists() else None,
        "version": 2,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_locale(language: str) -> str:
    normalized = (language or "").strip().lower()
    locales = {
        "ru": "ru_RU",
        "en": "en_US",
    }
    return locales.get(normalized, normalized.replace("-", "_") if normalized else "en_US")


def build_page_meta_partial(pages: list[dict], project: dict) -> str:
    site_url = project.get("site_url", "").rstrip("/")
    theme = project.get("theme", {})
    locale = build_locale(theme.get("language") or project.get("language") or "en")
    page_meta = {
        page["page_url"]: {
            "title": page["title"],
            "seo_title": page["seo_title"],
            "description": page["description"] or project.get("site_description", ""),
            "image": f"{site_url}/assets/social/{page['page_url']}index.png"
            if page["page_url"]
            else f"{site_url}/assets/social/index.png",
            "url": page["canonical"] or site_url,
        }
        for page in pages
    }
    pages_literal = json.dumps(page_meta, ensure_ascii=False, indent=2, sort_keys=True)

    return f"""{{% set page_meta_map = {pages_literal} %}}
{{% set page_meta_locale = "{locale}" %}}
{{% set page_meta_key = page.url or '' %}}
{{% if page_meta_key in page_meta_map %}}
  {{% set page_meta = page_meta_map[page_meta_key] %}}
{{% endif %}}
"""


def build_robots_txt(project: dict) -> str:
    site_url = (project.get("site_url") or "").rstrip("/")
    lines = [
        "# Generated by scripts/generate_social_cards.py",
        "User-agent: *",
        "Allow: /",
    ]

    if site_url:
        lines.extend(
            [
                "",
                f"Sitemap: {site_url}/sitemap.xml",
            ]
        )

    return "\n".join(lines) + "\n"


def clean_empty_dirs(root: Path) -> None:
    for directory in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def uniquify_descriptions(pages: list[dict]) -> None:
    counts = Counter(page["description"] for page in pages if page.get("description"))

    for page in pages:
        description = page.get("description")
        if not description or counts[description] <= 1:
            continue
        page["description"] = normalize_description(f"{page['seo_title']}. {description}")


def main() -> int:
    root = discover_project_root()
    project = load_project(root)
    docs_dir = root / project.get("docs_dir", "docs")
    cards_dir = docs_dir / "assets" / "social"
    cards_dir.mkdir(parents=True, exist_ok=True)

    plugins = project.get("plugins", {})
    social = plugins.get("social", {})
    layout_options = social.get("cards_layout_options", {})
    colors = {
        "background": layout_options.get("background_color", "#303F8F"),
        "foreground": layout_options.get("color", "#FFFFFF"),
    }
    logo_path = root / layout_options.get("logo", "docs/assets/images/logo-social.png")
    page_meta_partial_path = root / "overrides" / "partials" / PAGE_META_PARTIAL
    robots_txt_path = docs_dir / ROBOTS_TXT

    manifest_path = cards_dir / MANIFEST_NAME
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {}

    next_manifest: dict[str, str] = {}
    pages: list[dict] = []

    for source in sorted(docs_dir.rglob("*.md")):
        page = build_page_metadata(source, docs_dir, project)
        pages.append(page)

    uniquify_descriptions(pages)

    for page in pages:
        output: Path = page["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        page_hash = compute_hash(page, project, colors, logo_path)
        key = str(output.relative_to(cards_dir))
        next_manifest[key] = page_hash

        if manifest.get(key) == page_hash and output.exists():
            continue

        image = render_card(page, project, colors, logo_path)
        image.save(output, quality=95)

    for old_key in set(manifest) - set(next_manifest):
        stale = cards_dir / old_key
        stale.unlink(missing_ok=True)

    clean_empty_dirs(cards_dir)
    manifest_path.write_text(
        json.dumps(next_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    page_meta_partial_path.parent.mkdir(parents=True, exist_ok=True)
    page_meta_partial_path.write_text(
        build_page_meta_partial(pages, project),
        encoding="utf-8",
    )
    robots_txt_path.write_text(
        build_robots_txt(project),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
