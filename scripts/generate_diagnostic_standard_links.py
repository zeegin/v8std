from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from scripts.acc_diagnostics import build_link_reviews, load_catalog as load_acc_catalog, load_overrides
    from scripts.diagnostic_articles import load_catalog
    from scripts.diagnostic_standard_links import (
        load_reviews,
        rewrite_diagnostic_page,
        rewrite_standard_page,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from acc_diagnostics import build_link_reviews, load_catalog as load_acc_catalog, load_overrides
    from diagnostic_articles import load_catalog
    from diagnostic_standard_links import (
        load_reviews,
        rewrite_diagnostic_page,
        rewrite_standard_page,
    )


def load_all_reviews(root: Path) -> tuple:
    reviewed = load_reviews(root / "data/diagnostic-standard-links.json")
    acc_catalog = load_acc_catalog(root / "data/acc-diagnostics.json")
    acc_overrides = load_overrides(root / "data/acc-standard-link-overrides.json")
    return reviewed + build_link_reviews(acc_catalog, acc_overrides)


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


def _registry_diagnostic_path(diagnostic: str) -> str:
    family, identifier = diagnostic.split(":", 1)
    directory = {"acc": "acc", "bslls": "bslls", "v8cs": "v8-code-style"}[family]
    return f"{directory}/{identifier}.md"


def _registry_diagnostic_sort_key(diagnostic: str) -> tuple:
    family, identifier = diagnostic.split(":", 1)
    if family == "acc":
        return (family, 0, int(identifier))
    return (family, 1, identifier.casefold())


def render_registry_index(reviews: list | tuple, standard_titles: dict[str, str]) -> str:
    by_standard: dict[str, set[str]] = {standard: set() for standard in standard_titles}
    for review in reviews:
        if review.review == "confirmed":
            by_standard[review.standard].add(review.diagnostic)
    lines = [
        "---",
        "title: Реестр диагностик по стандартам",
        "llms:",
        "  ignore: true",
        "---",
        "",
        "# Реестр диагностик по стандартам",
        "",
        "| Стандарт | Диагностики |",
        "| --- | --- |",
    ]
    for standard in sorted(standard_titles, key=lambda item: int(item[3:])):
        number = standard[3:]
        title = standard_titles[standard]
        diagnostics = sorted(
            by_standard[standard], key=_registry_diagnostic_sort_key
        )
        rendered = " <br> ".join(
            f"[{diagnostic}]({_registry_diagnostic_path(diagnostic)})"
            for diagnostic in diagnostics
        ) or "Нет диагностик"
        lines.append(
            f"| [#{standard}: {title}](../std/{number}.md) | {rendered} |"
        )
    return "\n".join(lines) + "\n"


def _page_metadata(path: Path, labels: tuple[str, ...]) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    values = []
    for label in labels:
        match = re.search(rf"^- {re.escape(label)}:\s*(.+?)\s*$", source, re.MULTILINE)
        if match is None:
            raise ValueError(f"missing {label} metadata: {path}")
        values.append(match.group(1))
    return tuple(values)


def _render_family_relations(
    reviews: list | tuple,
    standard_titles: dict[str, str],
) -> str:
    confirmed = sorted(
        (review for review in reviews if review.review == "confirmed"),
        key=lambda item: (item.standard, item.clause or "", item.anchor or ""),
    )
    links = []
    for review in confirmed:
        title = standard_titles[review.standard]
        if review.clause == review.standard:
            label = f"#{review.standard}: {title}"
        else:
            label = f"#{review.standard}, п. {review.clause}: {title}"
        links.append(
            f"[{label}](../../std/{review.standard[3:]}.md#{review.anchor})"
        )
    return "<br>".join(links) or "—"


def render_family_index(
    family: str,
    entries: list | tuple,
    reviews: list | tuple,
    standard_titles: dict[str, str],
    pages_directory: Path,
) -> str:
    settings = {
        "bslls": {
            "prefix": "bslls",
            "title": "Диагностики BSL Language Server и стандарты",
            "metadata": ("Тип", "Важность"),
            "header": "| Диагностика | Тип | Важность | Стандарты |",
            "separator": "|---|---|---|---|",
        },
        "v8-code-style": {
            "prefix": "v8cs",
            "title": "Диагностики EDT v8-code-style и стандарты",
            "metadata": ("Категория",),
            "header": "| Диагностика | Категория | Стандарты |",
            "separator": "|---|---|---|",
        },
    }
    try:
        config = settings[family]
    except KeyError as error:
        raise ValueError(f"unsupported diagnostic family index: {family}") from error

    reviews_by_diagnostic: dict[str, list] = {}
    for review in reviews:
        reviews_by_diagnostic.setdefault(review.diagnostic, []).append(review)
    title = config["title"]
    lines = [
        "---",
        f"title: {title}",
        "llms:",
        "  ignore: true",
        "---",
        "",
        f"# {title}",
        "",
        config["header"],
        config["separator"],
    ]
    for entry in entries:
        metadata = _page_metadata(
            pages_directory / f"{entry.id}.md", config["metadata"]
        )
        diagnostic = f"{config['prefix']}:{entry.id}"
        relations = _render_family_relations(
            reviews_by_diagnostic.get(diagnostic, ()), standard_titles
        )
        cells = [f"[{entry.id}]({entry.id}.md)", *metadata, relations]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def generate(root: Path, *, write: bool) -> tuple[int, int, int, bool, int]:
    catalog = load_catalog(root / "data/diagnostic-sources.json")
    reviews = load_all_reviews(root)
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

    changed_family_indexes = 0
    for family in catalog.families:
        directory, _ = family_settings[family.family]
        family_directory = root / "docs/diagnostics" / directory
        index_path = family_directory / "index.md"
        expected_index = render_family_index(
            family.family,
            catalog.diagnostics[family.family],
            reviews,
            standard_titles,
            family_directory,
        )
        actual_index = index_path.read_text(encoding="utf-8")
        if actual_index != expected_index:
            changed_family_indexes += 1
            if write:
                index_path.write_text(expected_index, encoding="utf-8")

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

    registry_path = root / "docs/diagnostics/index.md"
    expected_registry = render_registry_index(reviews, standard_titles)
    registry_changed = registry_path.read_text(encoding="utf-8") != expected_registry
    if write and registry_changed:
        registry_path.write_text(expected_registry, encoding="utf-8")

    return (
        diagnostic_count,
        changed_diagnostics,
        changed_standards,
        registry_changed,
        changed_family_indexes,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate exact diagnostic/standard relationship links"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    (
        diagnostic_count,
        changed_diagnostics,
        changed_standards,
        registry_changed,
        changed_family_indexes,
    ) = generate(args.root.resolve(), write=args.write)
    if args.check:
        if (
            changed_diagnostics
            or changed_standards
            or registry_changed
            or changed_family_indexes
        ):
            print(
                "relationship graph differs: "
                f"diagnostics={changed_diagnostics}, standards={changed_standards}, "
                f"registry={int(registry_changed)}, family_indexes={changed_family_indexes}"
            )
            return 1
        print(f"relationship graph clean: diagnostics={diagnostic_count}")
        return 0

    print(
        "relationship graph written: "
        f"diagnostics={changed_diagnostics}, standards={changed_standards}, "
        f"registry={int(registry_changed)}, family_indexes={changed_family_indexes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
