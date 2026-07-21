from __future__ import annotations

import argparse
import hashlib
import json
import re
import copy
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.diagnostic_standard_links import (
        LinkReview,
        heading_anchor,
        parse_v8std_url,
        render_diagnostic_relations,
        _standard_heading_anchors,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from diagnostic_standard_links import (
        LinkReview,
        heading_anchor,
        parse_v8std_url,
        render_diagnostic_relations,
        _standard_heading_anchors,
    )


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
KNOWN_BROKEN_HDOC_RE = re.compile(r"(?<=:hdoc)(?=\d)")
SITE_ACC_PRODUCT_VERSION = "1.2.9.80"
SITE_ACC_SOURCE_SHA256 = "4302557c70d119c8945cf42372693b93c0495f850ec37e60596402aa1884de4f"
EXCLUDED_ACC_SOURCE_LABELS = {"acc_index.md"}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_fields(element: ET.Element) -> dict[str, str]:
    return {
        _local_name(child.tag): (child.text or "").strip()
        for child in element
        if len(child) == 0
    }


def _parse_source_url(url: str) -> tuple[str, str | None]:
    normalized = KNOWN_BROKEN_HDOC_RE.sub(":", url)
    return parse_v8std_url(normalized)


def _is_public_acc_source(label: str) -> bool:
    return label.strip().casefold() not in EXCLUDED_ACC_SOURCE_LABELS


def _normalize_source_text(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def extract_catalog(source: Path, *, product_version: str) -> dict[str, Any]:
    source_bytes = source.read_bytes()
    root = ET.fromstring(source_bytes)
    requirements: dict[str, dict[str, str]] = {}
    for element in root.iter():
        if _local_name(element.tag) != "CatalogObject.Требования":
            continue
        fields = _direct_fields(element)
        reference = fields.get("Ref")
        if reference:
            requirements[reference] = fields

    diagnostics: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for element in root.iter():
        if _local_name(element.tag) != "CatalogObject.ОбнаруживаемыеОшибки":
            continue
        fields = _direct_fields(element)
        code = fields.get("Code", "").strip()
        if (
            fields.get("IsFolder", "").lower() != "false"
            or fields.get("DeletionMark", "").lower() != "false"
            or not code.isdigit()
        ):
            continue
        if code in seen_codes:
            raise ValueError(f"duplicate ACC code: {code}")
        seen_codes.add(code)

        standards: list[dict[str, str | None]] = []
        seen_standards: set[tuple[str, str | None]] = set()
        for child in element:
            if _local_name(child.tag) != "Требования":
                continue
            for row in child:
                row_fields = _direct_fields(row)
                source_url = row_fields.get("СсылкаНаСтандарт", "")
                if not source_url:
                    requirement = requirements.get(row_fields.get("Требование", ""), {})
                    source_url = requirement.get("СсылкаНаСтандарт", "")
                if not source_url:
                    continue
                standard, clause = _parse_source_url(source_url)
                relation_key = (standard, clause)
                if relation_key in seen_standards:
                    continue
                seen_standards.add(relation_key)
                standards.append(
                    {
                        "standard": standard,
                        "clause": clause,
                        "source_url": source_url,
                    }
                )

        estimated = fields.get("ПрогнозируемоеВремяИсправления", "").strip()
        diagnostics.append(
            {
                "code": code,
                "description": _normalize_source_text(fields.get("Description", "")),
                "severity": fields.get("Критичность", "").strip(),
                "recommendation": _normalize_source_text(fields.get("Рекомендация", "")),
                "estimated_fix_minutes": int(estimated) if estimated.isdigit() else None,
                "standards": standards,
                "edt_codes": [],
                "external_sources": [],
            }
        )

    diagnostics.sort(key=lambda item: int(item["code"]))
    return {
        "version": 1,
        "source": {
            "product": "1С:Автоматизированная проверка конфигураций",
            "product_version": product_version,
            "path": "CommonTemplates/СоставПравилПроверки/Ext/Template.bin",
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
        "diagnostics": diagnostics,
    }


def load_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("ACC catalog requires version 1")
    source = payload.get("source")
    diagnostics = payload.get("diagnostics")
    if not isinstance(source, dict) or not SHA256_RE.fullmatch(source.get("sha256", "")):
        raise ValueError("ACC catalog requires a source SHA-256")
    if not isinstance(diagnostics, list):
        raise ValueError("ACC catalog requires a diagnostics array")
    seen: set[str] = set()
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, dict):
            raise ValueError("ACC diagnostic must be an object")
        code = diagnostic.get("code")
        if not isinstance(code, str) or not code.isdigit():
            raise ValueError(f"invalid ACC code: {code}")
        if code in seen:
            raise ValueError(f"duplicate ACC code: {code}")
        seen.add(code)
        description = diagnostic.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(
                f"ACC diagnostic {code} requires a non-empty description"
            )
    return payload


def validate_site_catalog(catalog: dict[str, Any]) -> None:
    source = catalog["source"]
    product_version = source.get("product_version")
    if product_version != SITE_ACC_PRODUCT_VERSION:
        raise ValueError(
            f"ACC catalog product version must be {SITE_ACC_PRODUCT_VERSION}; "
            f"got {product_version!r}"
        )
    source_sha256 = source["sha256"]
    if source_sha256 != SITE_ACC_SOURCE_SHA256:
        raise ValueError(
            f"ACC catalog source SHA-256 must be {SITE_ACC_SOURCE_SHA256}; "
            f"got {source_sha256!r}"
        )


def build_link_reviews(
    catalog: dict[str, Any],
    overrides: Iterable[dict[str, Any]],
) -> tuple[LinkReview, ...]:
    override_map: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    for override in overrides:
        key = (
            override["code"],
            override["standard"],
            override.get("source_clause"),
        )
        if key in override_map:
            raise ValueError(f"duplicate ACC standard override: {key}")
        override_map[key] = override

    source = catalog["source"]
    evidence_prefix = (
        f"local:data/acc-diagnostics.json@{source['product_version']}@{source['sha256']}"
    )
    reviews: list[LinkReview] = []
    matched_overrides: set[tuple[str, str, str | None]] = set()
    for diagnostic in catalog["diagnostics"]:
        code = diagnostic["code"]
        for relation in diagnostic.get("standards", []):
            standard = relation["standard"]
            source_clause = relation.get("clause")
            key = (code, standard, source_clause)
            override = override_map.get(key)
            if override is None:
                review = "confirmed"
                clause = source_clause or standard
                reason = (
                    f"АПК {source['product_version']} связывает проверку с "
                    + (f"пунктом {source_clause} стандарта #{standard}." if source_clause else f"стандартом #{standard}.")
                )
                notes = None
            else:
                matched_overrides.add(key)
                review = override["review"]
                clause = override.get("clause")
                reason = override["reason"]
                notes = override.get("notes")
            anchor = heading_anchor(clause) if clause is not None else None
            reviews.append(
                LinkReview(
                    diagnostic=f"acc:{code}",
                    standard=standard,
                    clause=clause,
                    anchor=anchor,
                    evidence=(f"{evidence_prefix}#acc:{code}", relation["source_url"]),
                    reason=reason,
                    review=review,
                    notes=notes,
                )
            )
    unused = sorted(set(override_map) - matched_overrides)
    if unused:
        raise ValueError(f"unused ACC standard override: {unused[0]}")
    return tuple(
        sorted(
            reviews,
            key=lambda item: (
                int(item.diagnostic.split(":", 1)[1]),
                item.standard,
                item.clause or "",
            ),
        )
    )


def render_page(
    diagnostic: dict[str, Any],
    reviews: Iterable[LinkReview],
    *,
    standard_titles: dict[str, str],
    product_version: str,
    source_sha256: str,
) -> str:
    code = diagnostic["code"]
    lines = [
        f"###### acc:{code}",
        "",
        f"# {diagnostic['description']} (ACC {code})",
        "",
        f"- Код АПК: `{code}`",
        f"- Критичность АПК: `{diagnostic['severity']}`",
    ]
    estimated = diagnostic.get("estimated_fix_minutes")
    if estimated is not None and estimated > 0:
        lines.append(f"- Прогнозируемое время исправления: `{estimated} мин.`")
    edt_codes = diagnostic.get("edt_codes", [])
    if edt_codes:
        lines.append(
            "- Код проверки EDT: "
            + ", ".join(
                f"[{edt_code}](../v8-code-style/{edt_code}.md)"
                for edt_code in edt_codes
            )
        )

    lines.extend(["", "## Описание диагностики", "", diagnostic["description"]])

    recommendation = diagnostic.get("recommendation", "").strip()
    if recommendation:
        lines.extend(["", "## Рекомендация АПК", "", recommendation])

    lines.extend(
        [
            "",
            render_diagnostic_relations(reviews, standard_titles=standard_titles),
            "",
            "## Источник диагностики",
            "",
            (
                f"- АПК {product_version}, встроенная выгрузка `СоставПравилПроверки` "
                f"(SHA-256 `{source_sha256}`)."
            ),
        ]
    )
    for source in diagnostic.get("external_sources", []):
        if not _is_public_acc_source(source["label"]):
            continue
        lines.append(f"- [{source['label']}]({source['url']})")
    return "\n".join(lines).rstrip() + "\n"


def merge_site_metadata(catalog: dict[str, Any], acc_directory: Path) -> dict[str, Any]:
    merged = copy.deepcopy(catalog)
    edt_by_code: dict[str, list[str]] = {}
    index_path = acc_directory / "index.md"
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            match = re.match(
                r"^\|\s*\[АПК:(?P<code>\d+)\]\([^)]+\)\s*\|(?P<edt>.*?)\|",
                line,
            )
            if match is None:
                continue
            edt_by_code[match.group("code")] = re.findall(r"`([^`]+)`", match.group("edt"))

    for diagnostic in merged["diagnostics"]:
        code = diagnostic["code"]
        diagnostic["edt_codes"] = edt_by_code.get(code, diagnostic.get("edt_codes", []))
        page_path = acc_directory / f"{code}.md"
        if not page_path.exists():
            continue
        source = page_path.read_text(encoding="utf-8")
        heading = re.search(r"^#{2,6}\s+Источник(?: диагностики)?\s*$", source, re.MULTILINE)
        if heading is None:
            continue
        source_section = source[heading.end() :]
        external_sources = [
            {"label": label.strip(), "url": url.strip()}
            for label, url in re.findall(r"^-\s+\[([^]]+)\]\((https?://[^)]+)\)", source_section, re.MULTILINE)
            if _is_public_acc_source(label)
        ]
        diagnostic["external_sources"] = external_sources
    return merged


def load_overrides(path: Path) -> tuple[dict[str, Any], ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"version", "overrides"}:
        raise ValueError("ACC overrides require version and overrides fields")
    if payload["version"] != 1 or not isinstance(payload["overrides"], list):
        raise ValueError("ACC overrides require version 1 and an overrides array")
    return tuple(payload["overrides"])


def validate_review_targets(reviews: Iterable[LinkReview], standards_directory: Path) -> None:
    cache: dict[str, dict[str, tuple[int, int]]] = {}
    for review in reviews:
        if review.review != "confirmed":
            continue
        path = standards_directory / f"{review.standard[3:]}.md"
        if not path.exists():
            raise ValueError(f"missing standard page for {review.diagnostic} -> {review.standard}")
        if review.standard not in cache:
            cache[review.standard] = _standard_heading_anchors(
                path.read_text(encoding="utf-8"), review.standard
            )
        if review.anchor not in cache[review.standard]:
            raise ValueError(
                f"missing current clause: {review.diagnostic} -> {review.standard} / {review.clause}"
            )


def load_standard_titles(standards_directory: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    for path in sorted(standards_directory.glob("[0-9]*.md")):
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


def render_index(
    catalog: dict[str, Any],
    reviews: Iterable[LinkReview],
    standard_titles: dict[str, str],
) -> str:
    by_diagnostic: dict[str, list[LinkReview]] = {}
    for review in reviews:
        if review.review == "confirmed":
            by_diagnostic.setdefault(review.diagnostic, []).append(review)
    version = catalog["source"]["product_version"]
    lines = [
        "---",
        "title: Диагностики АПК (ACC) и стандарты",
        "llms:",
        "  ignore: true",
        "---",
        "",
        "# Диагностики АПК (ACC) и стандарты",
        "",
        f"Каталог сформирован из поставки АПК {version}.",
        "",
        "| Диагностика | Код EDT | Точный пункт стандарта |",
        "|---|---|---|",
    ]
    for diagnostic in catalog["diagnostics"]:
        code = diagnostic["code"]
        edt = "<br>".join(f"`{item}`" for item in diagnostic.get("edt_codes", [])) or "—"
        relations = []
        for review in sorted(
            by_diagnostic.get(f"acc:{code}", []),
            key=lambda item: (item.standard, item.clause or ""),
        ):
            title = standard_titles[review.standard]
            if review.clause == review.standard:
                label = f"#{review.standard}: {title}"
            else:
                label = f"#{review.standard}, п. {review.clause}: {title}"
            relations.append(
                f"[{label}](../../std/{review.standard[3:]}.md#{review.anchor})"
            )
        standards = "<br>".join(relations) or "—"
        lines.append(f"| [АПК:{code}]({code}.md) | {edt} | {standards} |")
    return "\n".join(lines) + "\n"


def generate(root: Path, *, write: bool) -> tuple[int, int, int, bool]:
    catalog = load_catalog(root / "data/acc-diagnostics.json")
    validate_site_catalog(catalog)
    overrides = load_overrides(root / "data/acc-standard-link-overrides.json")
    reviews = build_link_reviews(catalog, overrides)
    standards_directory = root / "docs/std"
    validate_review_targets(reviews, standards_directory)
    standard_titles = load_standard_titles(standards_directory)
    by_diagnostic: dict[str, list[LinkReview]] = {}
    for review in reviews:
        by_diagnostic.setdefault(review.diagnostic, []).append(review)

    acc_directory = root / "docs/diagnostics/acc"
    expected_paths: set[Path] = set()
    changed_pages = 0
    for diagnostic in catalog["diagnostics"]:
        code = diagnostic["code"]
        path = acc_directory / f"{code}.md"
        expected_paths.add(path)
        expected = render_page(
            diagnostic,
            by_diagnostic.get(f"acc:{code}", ()),
            standard_titles=standard_titles,
            product_version=catalog["source"]["product_version"],
            source_sha256=catalog["source"]["sha256"],
        )
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual != expected:
            changed_pages += 1
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected, encoding="utf-8")

    stale_paths = sorted(
        path
        for path in acc_directory.glob("[0-9]*.md")
        if path not in expected_paths
    )
    if write:
        for path in stale_paths:
            path.unlink()

    index_path = acc_directory / "index.md"
    expected_index = render_index(catalog, reviews, standard_titles)
    actual_index = index_path.read_text(encoding="utf-8") if index_path.exists() else None
    index_changed = actual_index != expected_index
    if write and index_changed:
        index_path.write_text(expected_index, encoding="utf-8")
    return len(catalog["diagnostics"]), changed_pages, len(stale_paths), index_changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract and generate the ACC diagnostic catalog"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("source", type=Path)
    extract_parser.add_argument("--product-version", required=True)
    extract_parser.add_argument("--site-acc-directory", type=Path)
    extract_parser.add_argument("--output", type=Path, required=True)

    generate_parser = subparsers.add_parser("generate")
    mode = generate_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    generate_parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args(argv)

    if args.command == "extract":
        catalog = extract_catalog(
            args.source.resolve(), product_version=args.product_version
        )
        if args.site_acc_directory is not None:
            catalog = merge_site_metadata(catalog, args.site_acc_directory.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"extracted ACC diagnostics: {len(catalog['diagnostics'])}")
        return 0

    count, changed, stale, index_changed = generate(
        args.root.resolve(), write=args.write
    )
    print(
        f"ACC catalog: diagnostics={count}, changed={changed}, "
        f"stale={stale}, index_changed={int(index_changed)}"
    )
    return int(args.check and bool(changed or stale or index_changed))


if __name__ == "__main__":
    raise SystemExit(main())
