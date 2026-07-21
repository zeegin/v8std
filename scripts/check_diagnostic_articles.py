#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.diagnostic_articles import content_sha256, load_catalog
    from scripts.diagnostic_standard_links import (
        SourceProposal,
        V8STD_NAVIGATION_RE,
        V8STD_URL_RE,
        load_reviews,
        parse_v8std_url,
        validate_review_coverage,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from diagnostic_articles import content_sha256, load_catalog
    from diagnostic_standard_links import (
        SourceProposal,
        V8STD_NAVIGATION_RE,
        V8STD_URL_RE,
        load_reviews,
        parse_v8std_url,
        validate_review_coverage,
    )


SOURCE_BLOCK_RE = re.compile(
    r"^<!-- diagnostic-source:start\n"
    r"(?P<metadata>.*?)\n"
    r"-->\n\n"
    r"(?P<body>.*?)\n\n"
    r"<!-- diagnostic-source:end -->\s*$",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True)
class IntegritySummary:
    families: int
    pages: int
    proposals: int


def _source_metadata(raw: str, page: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if line.startswith("SPDX-License-Identifier: "):
            key, value = line.split(": ", 1)
        elif "=" in line:
            key, value = line.split("=", 1)
        else:
            raise ValueError(f"invalid provenance marker in {page}: {line}")
        if key in metadata:
            raise ValueError(f"duplicate provenance marker in {page}: {key}")
        metadata[key] = value
    return metadata


def verify_committed_articles(root: Path) -> IntegritySummary:
    catalog = load_catalog(root / "data/diagnostic-sources.json")
    reviews = load_reviews(root / "data/diagnostic-standard-links.json")
    proposals: set[SourceProposal] = set()
    diagnostic_ids: set[str] = set()
    source_urls: dict[str, str] = {}
    page_count = 0

    for family in catalog.families:
        pages_directory = root / "docs/diagnostics" / family.family
        expected_ids = catalog.ids(family.family)
        actual_ids = {
            path.stem
            for path in pages_directory.glob("*.md")
            if path.name != "index.md"
        }
        if actual_ids != expected_ids:
            raise ValueError(
                f"catalog composition mismatch for {family.family}: "
                f"missing={sorted(expected_ids - actual_ids)}, "
                f"extra={sorted(actual_ids - expected_ids)}"
            )

        prefix = "bslls" if family.family == "bslls" else "v8cs"
        for entry in catalog.diagnostics[family.family]:
            page_count += 1
            diagnostic = f"{prefix}:{entry.id}"
            diagnostic_ids.add(diagnostic)
            source_urls[diagnostic] = entry.source_url
            page = pages_directory / f"{entry.id}.md"
            source = page.read_text(encoding="utf-8")
            marker = re.search(r"^######\s+(\S+)\s*$", source, re.MULTILINE)
            if marker is None or marker.group(1) != diagnostic:
                actual = marker.group(1) if marker else None
                raise ValueError(
                    f"diagnostic marker mismatch in {page}: expected {diagnostic}, got {actual}"
                )

            blocks = list(SOURCE_BLOCK_RE.finditer(source))
            if len(blocks) != 1:
                raise ValueError(f"expected one managed source block in {page}; got {len(blocks)}")
            block = blocks[0]
            metadata = _source_metadata(block.group("metadata"), page)
            expected_metadata = {
                "source_url": entry.source_url,
                "source_path": entry.source_path,
                "revision": family.revision,
                "SPDX-License-Identifier": family.license,
                "sha256": entry.content_sha256,
            }
            if metadata != expected_metadata:
                raise ValueError(
                    f"provenance marker mismatch in {page}: "
                    f"expected {expected_metadata}, got {metadata}"
                )

            body = block.group("body").strip() + "\n"
            actual_hash = content_sha256(body)
            if actual_hash != entry.content_sha256:
                raise ValueError(
                    f"content hash mismatch in {page}: "
                    f"expected {entry.content_sha256}, got {actual_hash}"
                )

            provenance_lines = (
                f"- [Исходная статья]({entry.source_url})",
                f"- Ревизия: `{family.revision}`",
                f"- Лицензия: `{family.license}`",
            )
            for line in provenance_lines:
                if source.count(line) != 1:
                    raise ValueError(f"missing or duplicate provenance line in {page}: {line}")

            for match in V8STD_URL_RE.finditer(body):
                referenced_url = match.group(0).rstrip(".,;")
                if V8STD_NAVIGATION_RE.fullmatch(referenced_url):
                    continue
                standard, proposed_clause = parse_v8std_url(referenced_url)
                proposals.add(
                    SourceProposal(
                        diagnostic=diagnostic,
                        standard=standard,
                        proposed_clause=proposed_clause,
                        source_url=entry.source_url,
                        referenced_url=referenced_url,
                    )
                )

    for review in reviews:
        if review.diagnostic not in diagnostic_ids:
            raise ValueError(f"review targets unknown diagnostic: {review.diagnostic}")
        immutable_evidence = [
            value for value in review.evidence if value.startswith("https://github.com/")
        ]
        if immutable_evidence and source_urls[review.diagnostic] not in immutable_evidence:
            raise ValueError(
                f"review evidence does not match manifest source: {review.diagnostic}"
            )
    validate_review_coverage(proposals, reviews)
    return IntegritySummary(len(catalog.families), page_count, len(proposals))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify committed diagnostic article bodies and provenance offline"
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args(argv)
    try:
        summary = verify_committed_articles(args.root.resolve())
    except (OSError, ValueError) as error:
        parser.exit(1, f"diagnostic article integrity failed: {error}\n")
    print(
        "diagnostic article integrity clean: "
        f"families={summary.families}, pages={summary.pages}, "
        f"proposals={summary.proposals}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
