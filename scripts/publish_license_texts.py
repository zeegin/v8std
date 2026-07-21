#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit


LICENSE_FILENAMES = frozenset(
    {
        "EPL-2.0.txt",
        "GPL-3.0.txt",
        "LGPL-3.0.txt",
    }
)
THIRD_PARTY_PAGE = Path("THIRD_PARTY_DIAGNOSTIC_ARTICLES/index.html")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        for name, value in attrs:
            if name.casefold() == "href" and value:
                self.hrefs.append(value)


def default_repo_root() -> Path:
    configured = os.environ.get("V8STD_REPO_ROOT")
    return Path(configured) if configured else Path(__file__).resolve().parents[1]


def publish_license_texts(repo_root: Path, site_dir: Path) -> set[str]:
    source_dir = repo_root / "LICENSES"
    target_dir = site_dir / "LICENSES"
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename in sorted(LICENSE_FILENAMES):
        source = source_dir / filename
        if not source.is_file():
            raise FileNotFoundError(f"canonical license text is missing: {source}")
        shutil.copyfile(source, target_dir / filename)

    return set(LICENSE_FILENAMES)


def check_published_license_links(repo_root: Path, site_dir: Path) -> set[str]:
    page = site_dir / THIRD_PARTY_PAGE
    if not page.is_file():
        raise FileNotFoundError(f"built third-party attribution page is missing: {page}")

    parser = LinkParser()
    parser.feed(page.read_text(encoding="utf-8"))
    checked: set[str] = set()
    page_url = f"https://v8std.invalid/{THIRD_PARTY_PAGE.as_posix()}"

    for href in parser.hrefs:
        resolved = urlsplit(urljoin(page_url, href))
        if resolved.netloc != "v8std.invalid":
            continue
        filename = Path(resolved.path).name
        if filename not in LICENSE_FILENAMES:
            continue
        target = site_dir / resolved.path.lstrip("/")
        canonical = repo_root / "LICENSES" / filename
        if not target.is_file():
            raise FileNotFoundError(f"published license link is broken: {href} -> {target}")
        if target.read_bytes() != canonical.read_bytes():
            raise ValueError(f"published license differs from canonical text: {target}")
        checked.add(filename)

    missing = LICENSE_FILENAMES - checked
    if missing:
        raise ValueError(
            f"third-party page does not link canonical license texts: {sorted(missing)}"
        )
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish or verify canonical third-party license texts in the built site."
    )
    parser.add_argument("--root", type=Path, default=default_repo_root())
    parser.add_argument("--site", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    repo_root = args.root.resolve()
    site_dir = (args.site or repo_root / "site").resolve()
    if args.check:
        checked = check_published_license_links(repo_root, site_dir)
        print(f"published license links clean: files={len(checked)}")
    else:
        published = publish_license_texts(repo_root, site_dir)
        print(f"published canonical license texts: files={len(published)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
