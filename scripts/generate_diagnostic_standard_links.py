from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.diagnostic_articles import load_catalog
    from scripts.diagnostic_standard_links import (
        load_reviews,
        rewrite_diagnostic_page,
        rewrite_standard_page,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from diagnostic_articles import load_catalog
    from diagnostic_standard_links import (
        load_reviews,
        rewrite_diagnostic_page,
        rewrite_standard_page,
    )


def load_standard_titles(standards_dir: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    for path in sorted(standards_dir.glob("[0-9]*.md")):
        title = next(
            (
                line.removeprefix("# ").strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.startswith("# ")
            ),
            None,
        )
        if title is None:
            raise ValueError(f"standard page lacks H1 title: {path}")
        titles[f"std{path.stem}"] = title
    return titles


def generate(root: Path, *, write: bool) -> tuple[int, int, int]:
    catalog = load_catalog(root / "data/diagnostic-sources.json")
    reviews = load_reviews(root / "data/diagnostic-standard-links.json")
    standard_titles = load_standard_titles(root / "docs/std")
    reviews_by_diagnostic: dict[str, list] = {}
    for review in reviews:
        reviews_by_diagnostic.setdefault(review.diagnostic, []).append(review)

    changed_diagnostics = 0
    diagnostic_count = 0
    family_settings = {
        "bslls": ("bslls", "bslls"),
        "v8-code-style": ("v8-code-style", "v8cs"),
    }
    for family in catalog.families:
        directory, prefix = family_settings[family.family]
        for entry in catalog.diagnostics[family.family]:
            diagnostic_count += 1
            diagnostic = f"{prefix}:{entry.id}"
            path = root / "docs/diagnostics" / directory / f"{entry.id}.md"
            source = path.read_text(encoding="utf-8")
            expected = rewrite_diagnostic_page(
                source,
                diagnostic,
                reviews_by_diagnostic.get(diagnostic, ()),
                standard_titles,
            )
            if expected != source:
                changed_diagnostics += 1
                if write:
                    path.write_text(expected, encoding="utf-8")

    changed_standards = 0
    standard_count = 0
    for path in sorted((root / "docs/std").glob("[0-9]*.md")):
        standard_count += 1
        standard = f"std{path.stem}"
        source = path.read_text(encoding="utf-8")
        expected = rewrite_standard_page(source, standard, reviews)
        if expected != source:
            changed_standards += 1
            if write:
                path.write_text(expected, encoding="utf-8")

    return diagnostic_count, changed_diagnostics, changed_standards


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate exact diagnostic/standard relationship links"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    diagnostic_count, changed_diagnostics, changed_standards = generate(
        args.root.resolve(), write=args.write
    )
    if args.check:
        if changed_diagnostics or changed_standards:
            print(
                "relationship graph differs: "
                f"diagnostics={changed_diagnostics}, standards={changed_standards}"
            )
            return 1
        print(f"relationship graph clean: diagnostics={diagnostic_count}")
        return 0

    print(
        "relationship graph written: "
        f"diagnostics={changed_diagnostics}, standards={changed_standards}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
