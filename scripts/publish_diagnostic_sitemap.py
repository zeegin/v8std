#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import stat
import tempfile
import tomllib
from pathlib import Path
from xml.etree import ElementTree

try:
    from scripts.diagnostic_inventory import diagnostic_urls
except ModuleNotFoundError:
    from diagnostic_inventory import diagnostic_urls


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def default_repo_root() -> Path:
    configured = os.environ.get("V8STD_REPO_ROOT")
    return Path(configured) if configured else Path(__file__).resolve().parents[1]


def project_site_url(repo_root: Path) -> str:
    with (repo_root / "zensical.toml").open("rb") as handle:
        config = tomllib.load(handle)
    site_url = str(config["project"]["site_url"]).rstrip("/")
    if not site_url:
        raise ValueError("project.site_url must not be empty")
    return site_url


def atomic_write_preserving_mode(path: Path, payload: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fchmod(temporary.fileno(), mode)
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def add_urls_to_sitemap(
    sitemap_path: Path,
    urls: tuple[str, ...],
) -> tuple[int, int, int]:
    tree = ElementTree.parse(sitemap_path)
    root = tree.getroot()
    expected_root = f"{{{SITEMAP_NAMESPACE}}}urlset"
    if root.tag != expected_root:
        raise ValueError(f"unexpected sitemap root element: {root.tag}")

    url_tag = f"{{{SITEMAP_NAMESPACE}}}url"
    loc_tag = f"{{{SITEMAP_NAMESPACE}}}loc"
    seen: set[str] = set()
    duplicates_removed = 0
    changed = False

    for entry in list(root.findall(url_tag)):
        location = entry.find(loc_tag)
        if location is None or not location.text or not location.text.strip():
            continue
        value = location.text.strip()
        if value in seen:
            root.remove(entry)
            duplicates_removed += 1
            changed = True
            continue
        seen.add(value)

    added = 0
    for url in urls:
        if url in seen:
            continue
        entry = ElementTree.SubElement(root, url_tag)
        ElementTree.SubElement(entry, loc_tag).text = url
        seen.add(url)
        added += 1
        changed = True

    if changed:
        ElementTree.register_namespace("", SITEMAP_NAMESPACE)
        ElementTree.indent(tree, space="  ")
        payload = ElementTree.tostring(
            root,
            encoding="unicode",
            xml_declaration=True,
        )
        atomic_write_preserving_mode(sitemap_path, payload.rstrip() + "\n")

    return added, duplicates_removed, len(seen)


def publish_diagnostic_sitemap(
    repo_root: Path,
    sitemap_path: Path,
) -> tuple[int, int, int]:
    urls = diagnostic_urls(repo_root, project_site_url(repo_root))
    return add_urls_to_sitemap(sitemap_path, urls)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add all inventoried diagnostic detail pages to a built sitemap."
    )
    parser.add_argument("--root", type=Path, default=default_repo_root())
    parser.add_argument("--sitemap", type=Path)
    args = parser.parse_args()

    repo_root = args.root.resolve()
    sitemap_path = (args.sitemap or repo_root / "site/sitemap.xml").resolve()
    added, duplicates_removed, total = publish_diagnostic_sitemap(
        repo_root,
        sitemap_path,
    )
    print(
        "diagnostic sitemap published: "
        f"added={added} duplicates_removed={duplicates_removed} urls={total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
