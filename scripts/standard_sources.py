from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

try:
    from scripts.atomic_files import atomic_write_text
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from atomic_files import atomic_write_text


STANDARD_RE = re.compile(r"std\d+")
SOURCE_SECTION_RE = re.compile(
    r"^###### Источник(?:и)?\n\n.*\Z", re.MULTILINE | re.DOTALL
)
ITS_SOURCE_RE = re.compile(r"https://its\.1c\.ru/db/v8std#content:(\d+)")
ENGLISH_PATH_PREFIX = (
    "/1C_Enterprise_Platform/Guides/Developer_Guides/"
    "1C_Enterprise_Development_Standards/"
)


def _validate_english_url(url: object) -> str:
    if not isinstance(url, str):
        raise ValueError("english_url must be a string")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "kb.1ci.com"
        or not parsed.path.startswith(ENGLISH_PATH_PREFIX)
        or not parsed.path.endswith("/")
        or parsed.fragment
        or parse_qs(parsed.query) != {"language": ["en"]}
    ):
        raise ValueError(f"noncanonical English standard URL: {url}")
    return url


def load_registry(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"version", "sources"}:
        raise ValueError("registry must contain only version and sources")
    if payload["version"] != 1 or not isinstance(payload["sources"], list):
        raise ValueError("registry requires version 1 and a sources array")

    result: dict[str, str] = {}
    seen_urls: set[str] = set()
    ordered_ids: list[str] = []
    for item in payload["sources"]:
        if not isinstance(item, dict) or set(item) != {"standard", "english_url"}:
            raise ValueError("each source requires standard and english_url")
        standard = item["standard"]
        if not isinstance(standard, str) or not STANDARD_RE.fullmatch(standard):
            raise ValueError(f"invalid standard id: {standard}")
        url = _validate_english_url(item["english_url"])
        if standard in result:
            raise ValueError(f"duplicate standard id: {standard}")
        if url in seen_urls:
            raise ValueError(f"duplicate English URL: {url}")
        result[standard] = url
        seen_urls.add(url)
        ordered_ids.append(standard)

    expected_order = sorted(ordered_ids, key=lambda value: int(value[3:]))
    if ordered_ids != expected_order:
        raise ValueError("registry sources must be sorted by numeric standard id")
    return result


def render_sources(
    standard: str, russian_url: str, english_url: str | None
) -> str:
    if not STANDARD_RE.fullmatch(standard):
        raise ValueError(f"invalid standard id: {standard}")
    match = ITS_SOURCE_RE.fullmatch(russian_url)
    if match is None or match.group(1) != standard[3:]:
        raise ValueError(f"ITS source does not match {standard}: {russian_url}")
    if english_url is None:
        return f"###### Источник\n\n{russian_url}\n"
    _validate_english_url(english_url)
    return (
        "###### Источники\n\n"
        f"- [Русская версия — ИТС]({russian_url})\n"
        f"- [English version — 1Ci Knowledge Base]({english_url})\n"
    )


def sync_standard_sources(
    docs_dir: Path, registry_path: Path, write: bool
) -> list[Path]:
    registry = load_registry(registry_path)
    rendered: dict[Path, str] = {}
    for standard, english_url in registry.items():
        page = docs_dir / f"{standard[3:]}.md"
        if not page.is_file():
            raise FileNotFoundError(f"standard page is missing: {page}")
        content = page.read_text(encoding="utf-8")
        source_match = SOURCE_SECTION_RE.search(content)
        if source_match is None:
            raise ValueError(f"source section is missing: {page}")
        its_matches = ITS_SOURCE_RE.findall(source_match.group(0))
        if len(its_matches) != 1:
            raise ValueError(f"expected one ITS source in {page}")
        russian_url = f"https://its.1c.ru/db/v8std#content:{its_matches[0]}"
        replacement = render_sources(standard, russian_url, english_url)
        rendered[page] = content[: source_match.start()] + replacement

    changed = [
        page
        for page, content in rendered.items()
        if page.read_text(encoding="utf-8") != content
    ]
    if write:
        for page in changed:
            atomic_write_text(page, rendered[page])
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize standard source links")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report Markdown drift")
    mode.add_argument("--write", action="store_true", help="update Markdown pages")
    parser.add_argument(
        "--docs-dir", type=Path, default=Path("docs/std"), help="standard pages"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("data/standard-english-sources.json"),
        help="verified English source registry",
    )
    args = parser.parse_args()
    changed = sync_standard_sources(args.docs_dir, args.registry, write=args.write)
    if changed:
        action = "updated" if args.write else "out of date"
        print(f"standard sources {action}: {len(changed)}")
        for page in changed:
            print(page)
        return 0 if args.write else 1
    print("standard sources are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
