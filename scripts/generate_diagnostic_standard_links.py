from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.autoformat_fixes import load_autoformat_catalog
    from scripts.acc_diagnostics import build_link_reviews, load_catalog as load_acc_catalog, load_overrides
    from scripts.diagnostic_articles import load_catalog
    from scripts.diagnostic_standard_links import (
        load_reviews,
        heading_anchor,
        rewrite_diagnostic_page,
        rewrite_standard_page,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from autoformat_fixes import load_autoformat_catalog
    from acc_diagnostics import build_link_reviews, load_catalog as load_acc_catalog, load_overrides
    from diagnostic_articles import load_catalog
    from diagnostic_standard_links import (
        load_reviews,
        heading_anchor,
        rewrite_diagnostic_page,
        rewrite_standard_page,
    )


def load_all_reviews(root: Path) -> tuple:
    reviewed = load_reviews(root / "data/diagnostic-standard-links.json")
    acc_catalog = load_acc_catalog(root / "data/acc-diagnostics.json")
    acc_overrides = load_overrides(root / "data/acc-standard-link-overrides.json")
    return reviewed + build_link_reviews(acc_catalog, acc_overrides)


@dataclass(frozen=True)
class StandardClause:
    clause: str
    anchor: str
    summary: str | None


@dataclass(frozen=True)
class StandardPage:
    title: str
    clauses: tuple[StandardClause, ...]


NUMERIC_HEADING_RE = re.compile(
    r"^######\s+(?P<clause>\d+(?:\.\d+)*(?:\.?[а-яa-z])?)\.?\s*$",
    re.IGNORECASE,
)
H1_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
MARKDOWN_LINK_RE = re.compile(r"\[([^]]+)]\([^)]+\)")


def _clause_sort_key(clause: str) -> tuple:
    parts = re.findall(r"\d+|[а-яa-z]+", clause.casefold())
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts)


def _clause_summary(lines: list[str]) -> str | None:
    in_fence = False
    in_managed = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("<!-- diagnostic-backlinks:start"):
            in_managed = True
            continue
        if line.startswith("<!-- diagnostic-backlinks:end"):
            in_managed = False
            continue
        if in_managed:
            continue
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue
        if line.startswith(("<!--", "!!!", "???", "#", "- ", "* ", ">")):
            continue
        text = re.sub(r"#![a-z]+\s+", "", line, flags=re.IGNORECASE)
        text = MARKDOWN_LINK_RE.sub(r"\1", text)
        text = re.sub(r"[`*_~]", "", text).strip()
        text = re.split(
            r"\s*[«»]?\s*\(англ\.", text, maxsplit=1, flags=re.IGNORECASE
        )[0].rstrip(" «»")
        if not text:
            continue
        sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].rstrip(".!?")
        return sentence or None
    return None


def _russian_count(value: int, forms: tuple[str, str, str]) -> str:
    remainder_100 = value % 100
    remainder_10 = value % 10
    if 11 <= remainder_100 <= 14:
        form = forms[2]
    elif remainder_10 == 1:
        form = forms[0]
    elif 2 <= remainder_10 <= 4:
        form = forms[1]
    else:
        form = forms[2]
    return f"{value} {form}"


def load_standard_pages(standards_dir: Path) -> dict[str, StandardPage]:
    pages: dict[str, StandardPage] = {}
    for path in sorted(standards_dir.glob("[0-9]*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        title = next((match.group("title") for line in lines if (match := H1_RE.fullmatch(line))), None)
        if title is None:
            raise ValueError(f"standard page lacks H1 title: {path}")
        headings: list[tuple[int, str]] = []
        for index, line in enumerate(lines):
            match = NUMERIC_HEADING_RE.fullmatch(line)
            if match:
                clause = match.group("clause").rstrip(".")
                clause = re.sub(r"\.(?=[а-яa-z]$)", "", clause, flags=re.IGNORECASE)
                headings.append((index, clause))
        occurrences: dict[str, int] = {}
        clauses = []
        for position, (index, clause) in enumerate(headings):
            base_anchor = heading_anchor(clause)
            occurrence = occurrences.get(base_anchor, 0)
            occurrences[base_anchor] = occurrence + 1
            anchor = heading_anchor(clause, occurrence)
            end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
            clauses.append(StandardClause(clause, anchor, _clause_summary(lines[index + 1 : end])))
        clauses.sort(key=lambda item: (_clause_sort_key(item.clause), item.anchor))
        pages[f"std{path.stem}"] = StandardPage(title, tuple(clauses))
    return pages


def _registry_diagnostic_path(diagnostic: str) -> str:
    family, identifier = diagnostic.split(":", 1)
    directory = {"acc": "acc", "bslls": "bslls", "v8cs": "v8-code-style"}[family]
    return f"{directory}/{identifier}.md"


def _registry_diagnostic_sort_key(diagnostic: str) -> tuple:
    family, identifier = diagnostic.split(":", 1)
    if family == "acc":
        return (family, 0, int(identifier))
    return (family, 1, identifier.casefold())


def render_registry_index(
    reviews: list | tuple,
    standard_pages: dict[str, StandardPage],
    autoformat_fixes: list | tuple = (),
) -> str:
    by_clause: dict[tuple[str, str], set[str]] = {}
    for review in reviews:
        if review.review == "confirmed":
            if review.standard not in standard_pages:
                raise ValueError(f"missing standard {review.standard}")
            if review.clause is None or review.anchor is None:
                raise ValueError(f"confirmed relationship lacks clause: {review.diagnostic}")
            if review.clause != review.standard:
                valid_clauses = {
                    clause.clause for clause in standard_pages[review.standard].clauses
                }
                if review.clause not in valid_clauses:
                    raise ValueError(
                        f"missing clause {review.standard}:{review.clause}#{review.anchor}"
                    )
            by_clause.setdefault((review.standard, review.clause), set()).add(
                review.diagnostic
            )
    fixes_by_clause: dict[tuple[str, str], bool] = {}
    for fix in autoformat_fixes:
        if fix.standard not in standard_pages:
            raise ValueError(f"missing standard {fix.standard}")
        if fix.clause != fix.standard:
            clauses = {item.clause: item.anchor for item in standard_pages[fix.standard].clauses}
            if clauses.get(fix.clause) != fix.anchor:
                raise ValueError(
                    f"missing autoformat clause {fix.standard}:{fix.clause}#{fix.anchor}"
                )
        fixes_by_clause[(fix.standard, fix.clause)] = True
    lines = [
        "---",
        "title: Реестр проверок и исправлений по стандартам",
        "llms:",
        "  ignore: true",
        "---",
        "",
        "# Реестр проверок и исправлений по стандартам",
        "",
        '<div class="diagnostics-registry" data-diagnostics-registry>',
        '  <div class="diagnostics-registry__controls">',
        '    <label>Поиск <input type="search" data-diagnostics-search placeholder="Стандарт, пункт, проверка или исправление"></label>',
        '    <label><input type="checkbox" data-show-empty> Показать пункты без проверок и исправлений</label>',
        "  </div>",
    ]
    for standard in sorted(standard_pages, key=lambda item: int(item[3:])):
        number = standard[3:]
        page = standard_pages[standard]
        groups = []
        all_diagnostics: set[str] = set()
        clauses_with_capabilities = 0
        for clause in page.clauses:
            diagnostics = sorted(
                by_clause.get((standard, clause.clause), ()),
                key=_registry_diagnostic_sort_key,
            )
            has_fix = fixes_by_clause.get((standard, clause.clause), False)
            if diagnostics or has_fix:
                clauses_with_capabilities += 1
            if diagnostics:
                all_diagnostics.update(diagnostics)
            groups.append((clause, diagnostics, has_fix, False))
        overall = sorted(
            by_clause.get((standard, standard), ()),
            key=_registry_diagnostic_sort_key,
        )
        all_diagnostics.update(overall)
        overall_fix = fixes_by_clause.get((standard, standard), False)
        if overall or overall_fix:
            groups.append(
                (StandardClause(standard, standard, "Стандарт в целом"), overall, overall_fix, True)
            )
        fix_count = int(any(item[2] for item in groups))
        empty_standard = not all_diagnostics and not fix_count
        searchable_diagnostics = sorted(
            all_diagnostics, key=_registry_diagnostic_sort_key
        )
        search_terms = [standard, page.title, *searchable_diagnostics]
        if fix_count:
            search_terms.append("autoformat")
        search = " ".join(search_terms).casefold()
        hidden = ' hidden data-empty="true"' if empty_standard else ""
        lines.extend([
            f'  <details class="diagnostics-standard" data-standard data-search="{html.escape(search, quote=True)}"{hidden}>',
            '    <summary class="diagnostics-standard__summary">',
            f'      <span class="diagnostics-standard__title">#{standard}: {html.escape(page.title)}</span>',
            '      <span class="diagnostics-standard__counts">'
            + _russian_count(len(all_diagnostics), ("проверка", "проверки", "проверок"))
            + " · "
            + _russian_count(
                clauses_with_capabilities, ("пункт", "пункта", "пунктов")
            )
            + " · "
            + _russian_count(fix_count, ("исправление", "исправления", "исправлений"))
            + "</span>",
            "    </summary>",
            '    <div class="diagnostics-standard__clauses">',
        ])
        for clause, diagnostics, has_fix, overall_group in groups:
            is_empty = not diagnostics and not has_fix
            empty = ' hidden data-empty="true"' if is_empty else ""
            label = "Стандарт в целом" if overall_group else f"п. {clause.clause}"
            if clause.summary and not overall_group:
                label += f" — {clause.summary}"
            clause_search = " ".join(
                [label, *diagnostics, *(["autoformat"] if has_fix else [])]
            ).casefold()
            lines.append(
                f'      <section class="diagnostics-clause" data-clause data-search="{html.escape(clause_search, quote=True)}"{empty}>'
            )
            lines.append(
                f'        <h2 class="diagnostics-clause__title"><a href="../std/{number}.md#{html.escape(clause.anchor, quote=True)}">{html.escape(label)}</a></h2>'
            )
            if diagnostics:
                lines.append(
                    '        <div class="diagnostics-clause__links diagnostic-links">'
                )
                for diagnostic in diagnostics:
                    lines.append(
                        f'          <a class="diagnostic-chip" href="{_registry_diagnostic_path(diagnostic)}">{html.escape(diagnostic)}</a>'
                    )
                lines.append("        </div>")
            if has_fix:
                lines.append('        <div class="diagnostics-clause__links fix-links">')
                lines.append(
                    '          <a class="diagnostic-chip diagnostic-chip--fix" '
                    'href="autoformat/index.md">autoformat</a>'
                )
                lines.append("        </div>")
            if is_empty:
                lines.append(
                    '        <p class="diagnostics-clause__empty">Нет проверок и исправлений</p>'
                )
            lines.append("      </section>")
        lines.extend(["    </div>", "  </details>"])
    lines.append("</div>")
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
    autoformat_catalog = load_autoformat_catalog(root / "data/autoformat-fixes.json")
    standard_pages = load_standard_pages(root / "docs/std")
    standard_titles = {standard: page.title for standard, page in standard_pages.items()}
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
        expected = rewrite_standard_page(
            source, standard, reviews, autoformat_catalog.fixes
        )
        if expected != source:
            changed_standards += 1
            if write:
                path.write_text(expected, encoding="utf-8")

    registry_path = root / "docs/diagnostics/index.md"
    expected_registry = render_registry_index(
        reviews, standard_pages, autoformat_catalog.fixes
    )
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
