from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlsplit

try:
    from scripts.diagnostic_articles import SourceCatalog, load_catalog, verify_checkout_revision
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from diagnostic_articles import SourceCatalog, load_catalog, verify_checkout_revision


STANDARD_RE = re.compile(r"^std\d+$")
DIAGNOSTIC_RE = re.compile(r"^(?:acc|bslls|v8cs):[^\s:]+$")
NUMERIC_CLAUSE_RE = re.compile(r"^\d+(?:\.\d+)*(?:[а-яa-z])?$", re.IGNORECASE)
IMMUTABLE_GITHUB_RE = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/blob/[0-9a-f]{40}/.+$"
)
LOCAL_EVIDENCE_RE = re.compile(r"^local:docs/std/\d+\.md#[a-z0-9-]+$")
V8STD_URL_RE = re.compile(r"https://its\.1c\.ru/db/v8std[^\s<>)\"\]]*")
V8STD_NAVIGATION_RE = re.compile(
    r"^https://its\.1c\.ru/db/v8std#browse:\d+:-?\d+:\d+:\d+$"
)
DIAGNOSTIC_STANDARDS_RE = re.compile(
    r"^<!-- diagnostic-standards:start -->\n.*?"
    r"^<!-- diagnostic-standards:end -->\n?",
    re.MULTILINE | re.DOTALL,
)
DIAGNOSTIC_BACKLINKS_RE = re.compile(
    r"^<!-- diagnostic-backlinks:start clause=[^\n]+ -->\n.*?"
    r"^<!-- diagnostic-backlinks:end clause=[^\n]+ -->\n?",
    re.MULTILINE | re.DOTALL,
)
FIX_BACKLINKS_RE = re.compile(
    r"^<!-- fix-backlinks:start clause=[^\n]+ -->\n.*?"
    r"^<!-- fix-backlinks:end clause=[^\n]+ -->\n?",
    re.MULTILINE | re.DOTALL,
)
LEGACY_MANAGED_BACKLINK_RE = re.compile(
    r"^.*\[#(?P<family>acc|bslls|v8cs):(?P<identifier>[^\]]+)\]"
    r"\([^\n)]+\)~?[ \t]*\n?",
    re.MULTILINE,
)
LEVEL_SIX_HEADING_RE = re.compile(r"^######\s+(?P<label>[^\n]+?)\s*$", re.MULTILINE)
ANY_HEADING_RE = re.compile(r"^#{1,6}\s+[^\n]+$", re.MULTILINE)
NUMERIC_HEADING_RE = re.compile(
    r"^(?P<clause>\d+(?:\.\d+)*(?:\.?[а-яa-z])?)\.?$", re.IGNORECASE
)


@dataclass(frozen=True, order=True)
class SourceProposal:
    diagnostic: str
    standard: str
    proposed_clause: str | None
    source_url: str
    referenced_url: str


@dataclass(frozen=True)
class LinkReview:
    diagnostic: str
    standard: str
    clause: str | None
    anchor: str | None
    evidence: tuple[str, ...]
    reason: str
    review: str
    notes: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LinkReview":
        if not isinstance(payload, dict):
            raise ValueError("review must be a JSON object")
        required = {
            "diagnostic",
            "standard",
            "clause",
            "anchor",
            "evidence",
            "reason",
            "review",
        }
        allowed = required | {"notes"}
        unknown = set(payload) - allowed
        missing = required - set(payload)
        if unknown:
            raise ValueError(f"unknown review fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing review fields: {', '.join(sorted(missing))}")

        diagnostic = payload["diagnostic"]
        standard = payload["standard"]
        clause = payload["clause"]
        anchor = payload["anchor"]
        evidence = payload["evidence"]
        reason = payload["reason"]
        review = payload["review"]
        notes = payload.get("notes")

        if not isinstance(diagnostic, str) or not DIAGNOSTIC_RE.fullmatch(diagnostic):
            raise ValueError(f"invalid diagnostic id: {diagnostic}")
        if not isinstance(standard, str) or not STANDARD_RE.fullmatch(standard):
            raise ValueError(f"invalid standard id: {standard}")
        if review not in {"confirmed", "rejected"}:
            raise ValueError("review must be confirmed or rejected")
        if review == "confirmed" and not isinstance(clause, str):
            raise ValueError("confirmed review requires clause")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{review} review requires reason")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{review} review requires evidence")
        if any(not _is_immutable_evidence(item) for item in evidence):
            raise ValueError("review evidence must use immutable source URLs or local citations")
        if len(evidence) != len(set(evidence)):
            raise ValueError("review evidence must not contain duplicates")
        if notes is not None and (not isinstance(notes, str) or not notes.strip()):
            raise ValueError("review notes must be a non-empty string when present")

        if clause is not None:
            if not isinstance(clause, str):
                raise ValueError("clause must be a string or null")
            expected_anchor = heading_anchor(clause)
            if clause.startswith("std") and clause != standard:
                raise ValueError("top-level clause must match standard")
            valid_anchor = isinstance(anchor, str) and bool(
                re.fullmatch(re.escape(expected_anchor) + r"(?:_[1-9]\d*)?", anchor)
            )
            if not valid_anchor or (clause.startswith("std") and anchor != expected_anchor):
                raise ValueError(f"anchor must be {expected_anchor} for clause {clause}")
        elif anchor is not None:
            raise ValueError("anchor must be null when clause is null")

        return cls(
            diagnostic=diagnostic,
            standard=standard,
            clause=clause,
            anchor=anchor,
            evidence=tuple(evidence),
            reason=reason.strip(),
            review=review,
            notes=notes.strip() if notes is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "diagnostic": self.diagnostic,
            "standard": self.standard,
            "clause": self.clause,
            "anchor": self.anchor,
            "evidence": list(self.evidence),
            "reason": self.reason,
            "review": self.review,
        }
        if self.notes is not None:
            payload["notes"] = self.notes
        return payload


def _is_immutable_evidence(value: Any) -> bool:
    return isinstance(value, str) and bool(
        IMMUTABLE_GITHUB_RE.fullmatch(value) or LOCAL_EVIDENCE_RE.fullmatch(value)
    )


def heading_anchor(clause: str, occurrence: int = 0) -> str:
    if not isinstance(occurrence, int) or occurrence < 0:
        raise ValueError("heading occurrence must be a non-negative integer")
    if STANDARD_RE.fullmatch(clause):
        if occurrence:
            raise ValueError("top-level standard heading cannot be duplicated")
        return clause
    if not NUMERIC_CLAUSE_RE.fullmatch(clause):
        raise ValueError(f"unsupported clause: {clause}")
    # Zensical drops Cyrillic suffixes such as ``а``/``б`` from slugs. The
    # explicit occurrence disambiguates those headings from the numeric one.
    base = re.sub(r"[^0-9a-z]", "", clause, flags=re.IGNORECASE)
    return f"{base}_{occurrence}" if occurrence else base


def _normalize_source_clause(raw: str | None) -> str | None:
    if raw in {None, "", "_top"}:
        return None
    clause = raw.split("@", 1)[0]
    if not NUMERIC_CLAUSE_RE.fullmatch(clause):
        raise ValueError(f"unsupported v8std URL clause: {raw}")
    return clause


def parse_v8std_url(url: str) -> tuple[str, str | None]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "its.1c.ru":
        raise ValueError(f"unsupported v8std URL: {url}")

    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) - {"ysclid"}:
        raise ValueError(f"unsupported v8std URL: {url}")

    if parsed.path == "/db/v8std":
        match = re.fullmatch(
            r"(?:content|contrut):(\d+)(?::hdoc)?(?::([^:]+))?",
            parsed.fragment,
        )
        if match is None:
            raise ValueError(f"unsupported v8std URL: {url}")
        return f"std{match.group(1)}", _normalize_source_clause(match.group(2))

    match = re.fullmatch(
        r"/db/v8std/content/(\d+)/hdoc(?:/_top(?:/[^#?]*)?)?/?",
        parsed.path,
    )
    if match is None:
        raise ValueError(f"unsupported v8std URL: {url}")
    return f"std{match.group(1)}", _normalize_source_clause(parsed.fragment)


def load_reviews(path: Path) -> tuple[LinkReview, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("relationship registry must be a JSON object")
    unknown = set(payload) - {"version", "reviews"}
    missing = {"version", "reviews"} - set(payload)
    if unknown:
        raise ValueError(f"unknown registry fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ValueError(f"missing registry fields: {', '.join(sorted(missing))}")
    if payload["version"] != 1 or not isinstance(payload["reviews"], list):
        raise ValueError("relationship registry requires version 1 and a reviews array")

    reviews = tuple(LinkReview.from_dict(item) for item in payload["reviews"])
    seen: set[tuple[str, str, str | None]] = set()
    decisions: dict[tuple[str, str], set[str]] = {}
    for review in reviews:
        pair = (review.diagnostic, review.standard)
        key = (*pair, review.anchor)
        if key in seen:
            raise ValueError(
                "duplicate relationship: "
                f"{review.diagnostic} -> {review.standard} / {review.anchor}"
            )
        seen.add(key)
        decisions.setdefault(pair, set()).add(review.review)
    mixed = [pair for pair, values in decisions.items() if len(values) > 1]
    if mixed:
        diagnostic, standard = sorted(mixed)[0]
        raise ValueError(f"mixed review decisions: {diagnostic} -> {standard}")
    if tuple(
        sorted(
            reviews,
            key=lambda item: (
                item.diagnostic,
                item.standard,
                item.clause or "",
                item.anchor or "",
            ),
        )
    ) != reviews:
        raise ValueError("relationship reviews must use stable diagnostic/standard/clause sorting")
    return reviews


def discover_source_proposals(
    catalog: SourceCatalog,
    checkouts: dict[str, Path],
) -> set[SourceProposal]:
    proposals: set[SourceProposal] = set()
    for family in catalog.families:
        if family.family not in checkouts:
            raise ValueError(f"missing source checkout: {family.family}")
        checkout = checkouts[family.family]
        verify_checkout_revision(checkout, family.revision)
        prefix = "bslls" if family.family == "bslls" else "v8cs"
        for entry in catalog.diagnostics[family.family]:
            source_path = checkout / entry.source_path
            content = source_path.read_text(encoding="utf-8")
            for match in V8STD_URL_RE.finditer(content):
                referenced_url = match.group(0).rstrip(".,;")
                if V8STD_NAVIGATION_RE.fullmatch(referenced_url):
                    continue
                standard, proposed_clause = parse_v8std_url(referenced_url)
                proposals.add(
                    SourceProposal(
                        diagnostic=f"{prefix}:{entry.id}",
                        standard=standard,
                        proposed_clause=proposed_clause,
                        source_url=entry.source_url,
                        referenced_url=referenced_url,
                    )
                )
    return proposals


def validate_review_coverage(
    proposals: set[SourceProposal],
    reviews: tuple[LinkReview, ...],
) -> None:
    for proposal in sorted(proposals):
        matches = [
            review
            for review in reviews
            if review.diagnostic == proposal.diagnostic
            and review.standard == proposal.standard
            and proposal.source_url in review.evidence
        ]
        if not matches:
            raise ValueError(
                "unreviewed source proposal: "
                f"{proposal.diagnostic} -> {proposal.standard} ({proposal.referenced_url})"
            )


def render_diagnostic_relations(
    reviews: Iterable[LinkReview],
    *,
    standard_titles: dict[str, str],
) -> str:
    confirmed = sorted(
        (review for review in reviews if review.review == "confirmed"),
        key=lambda item: (item.standard, item.clause or "", item.anchor or ""),
    )
    lines = ["<!-- diagnostic-standards:start -->", "## Соответствие стандартам", ""]
    if not confirmed:
        lines.append("Нет подтверждённых связей со стандартами.")
    for review in confirmed:
        if review.standard not in standard_titles:
            raise ValueError(f"missing standard title: {review.standard}")
        number = review.standard[3:]
        title = standard_titles[review.standard]
        if review.clause == review.standard:
            label = f"#{review.standard}: {title}"
        else:
            label = f"#{review.standard}, п. {review.clause}: {title}"
        explanation = review.reason
        if review.notes:
            explanation += f" Примечание: {review.notes}"
        lines.append(
            f"- [{label}](../../std/{number}.md#{review.anchor}) — {explanation}"
        )
    lines.append("<!-- diagnostic-standards:end -->")
    return "\n".join(lines)


def _diagnostic_path(diagnostic: str) -> str:
    family, identifier = diagnostic.split(":", 1)
    directory = {
        "acc": "acc",
        "bslls": "bslls",
        "v8cs": "v8-code-style",
    }[family]
    return f"../diagnostics/{directory}/{identifier}.md"


def render_standard_backlinks(
    reviews: Iterable[LinkReview],
) -> dict[str, dict[str, str]]:
    grouped: dict[tuple[str, str, str], list[LinkReview]] = {}
    for review in reviews:
        if review.review != "confirmed":
            continue
        assert review.anchor is not None and review.clause is not None
        grouped.setdefault((review.standard, review.anchor, review.clause), []).append(review)

    rendered: dict[str, dict[str, str]] = {}
    for (standard, anchor, clause), items in sorted(grouped.items()):
        lines = [
            f"<!-- diagnostic-backlinks:start clause={clause} -->",
            '<div class="diagnostic-links" aria-label="Проверки">',
        ]
        for review in sorted(items, key=lambda item: item.diagnostic):
            lines.append(
                f'<a class="diagnostic-chip" href="{_diagnostic_path(review.diagnostic)}">'
                f"{review.diagnostic}</a>"
            )
        lines.extend(
            [
                "</div>",
                f"<!-- diagnostic-backlinks:end clause={clause} -->",
            ]
        )
        rendered.setdefault(standard, {})[anchor] = "\n".join(lines)
    return rendered


def render_autoformat_backlinks(fixes: Iterable[Any]) -> dict[str, dict[str, str]]:
    grouped: dict[tuple[str, str, str], list[Any]] = {}
    for fix in fixes:
        grouped.setdefault((fix.standard, fix.anchor, fix.clause), []).append(fix)
    rendered: dict[str, dict[str, str]] = {}
    for (standard, anchor, clause), _items in sorted(grouped.items()):
        rendered.setdefault(standard, {})[anchor] = "\n".join(
            [
                f"<!-- fix-backlinks:start clause={clause} -->",
                '<div class="fix-links" aria-label="Исправления">',
                '<a class="diagnostic-chip diagnostic-chip--fix" '
                'href="../diagnostics/autoformat/index.md">autoformat</a>',
                "</div>",
                f"<!-- fix-backlinks:end clause={clause} -->",
            ]
        )
    return rendered


def rewrite_diagnostic_page(
    source: str,
    diagnostic: str,
    reviews: Iterable[LinkReview],
    standard_titles: dict[str, str],
) -> str:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    marker = re.search(r"^######\s+([^\s]+)\s*$", normalized, re.MULTILINE)
    if marker is None or marker.group(1) != diagnostic:
        raise ValueError(f"diagnostic page marker mismatch: {diagnostic}")

    replacement = render_diagnostic_relations(reviews, standard_titles=standard_titles)
    if DIAGNOSTIC_STANDARDS_RE.search(normalized):
        rewritten = DIAGNOSTIC_STANDARDS_RE.sub(replacement + "\n", normalized, count=1)
    else:
        source_end = normalized.find("<!-- diagnostic-source:end -->")
        source_section = normalized.find("\n## Соответствие стандартам", source_end)
        source_info = normalized.find("\n## Источник диагностики", source_end)
        if source_end < 0 or source_info < 0:
            raise ValueError(f"diagnostic page lacks managed source/source info: {diagnostic}")
        if source_section >= 0 and source_section < source_info:
            prefix = normalized[:source_section].rstrip()
        else:
            prefix = normalized[:source_info].rstrip()
        suffix = normalized[source_info:].lstrip("\n")
        rewritten = f"{prefix}\n\n{replacement}\n\n{suffix}"
    return rewritten.rstrip() + "\n"


def _remove_empty_legacy_check_sections(source: str) -> str:
    pattern = re.compile(
        r"^###### Проверки[ \t]*\n(?P<body>.*?)(?=^#{1,6}\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        return "" if not match.group("body").strip() else match.group(0)

    return pattern.sub(replace, source)


def _standard_heading_anchors(source: str, standard: str) -> dict[str, tuple[int, int]]:
    headings = list(LEVEL_SIX_HEADING_RE.finditer(source))
    all_headings = list(ANY_HEADING_RE.finditer(source))
    anchors: dict[str, tuple[int, int]] = {}
    occurrences: dict[str, int] = {}
    for index, match in enumerate(headings):
        label = match.group("label").strip()
        if label == f"#{standard}":
            anchor = standard
        else:
            numeric = NUMERIC_HEADING_RE.fullmatch(label)
            if numeric is None:
                continue
            clause = re.sub(r"\.([а-яa-z])$", r"\1", numeric.group("clause"), flags=re.IGNORECASE)
            base = heading_anchor(clause)
            occurrence = occurrences.get(base, 0)
            anchor = heading_anchor(clause, occurrence=occurrence)
            occurrences[base] = occurrence + 1
        if anchor == standard:
            # The stable ``stdNNN`` marker precedes the H1 title. A source may
            # reference the whole standard even when it has numbered clauses;
            # keep that backlink after normative content and before provenance.
            source_heading = next(
                (
                    heading
                    for heading in headings[index + 1 :]
                    if heading.group("label").strip().startswith("Источник")
                ),
                None,
            )
            boundary = source_heading.start() if source_heading else len(source)
        else:
            following = [heading for heading in all_headings if heading.start() > match.end()]
            boundary = following[0].start() if following else len(source)
        anchors[anchor] = (match.end(), boundary)
    return anchors


def rewrite_standard_page(
    source: str,
    standard: str,
    reviews: Iterable[LinkReview],
    autoformat_fixes: Iterable[Any] = (),
) -> str:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    relevant = tuple(review for review in reviews if review.standard == standard)
    reviewed_pairs = {(review.diagnostic, review.standard) for review in relevant}
    without_generated = DIAGNOSTIC_BACKLINKS_RE.sub("", normalized)
    without_generated = FIX_BACKLINKS_RE.sub("", without_generated)

    def remove_legacy(match: re.Match[str]) -> str:
        diagnostic = f"{match.group('family')}:{match.group('identifier')}"
        if (diagnostic, standard) not in reviewed_pairs:
            if match.group("family") == "acc":
                return ""
            raise ValueError(f"unreviewed legacy backlink: {diagnostic} -> {standard}")
        return ""

    without_legacy = LEGACY_MANAGED_BACKLINK_RE.sub(remove_legacy, without_generated)
    rewritten = _remove_empty_legacy_check_sections(without_legacy).rstrip() + "\n"
    blocks = render_standard_backlinks(relevant).get(standard, {})
    fix_blocks = render_autoformat_backlinks(
        fix for fix in autoformat_fixes if fix.standard == standard
    ).get(standard, {})
    for anchor, fix_block in fix_blocks.items():
        if anchor in blocks:
            blocks[anchor] = blocks[anchor] + "\n\n" + fix_block
        else:
            blocks[anchor] = fix_block
    if not blocks:
        return rewritten

    anchors = _standard_heading_anchors(rewritten, standard)
    missing = sorted(set(blocks) - set(anchors))
    if missing:
        raise ValueError(f"missing standard anchors for {standard}: {', '.join(missing)}")
    grouped_insertions: dict[int, list[tuple[str, str]]] = {}
    for anchor, block in blocks.items():
        grouped_insertions.setdefault(anchors[anchor][1], []).append((anchor, block))
    insertions = sorted(grouped_insertions.items(), reverse=True)
    for position, positioned_blocks in insertions:
        block = "\n\n".join(
            value for _, value in sorted(positioned_blocks, key=lambda item: item[0])
        )
        left = rewritten[:position].rstrip()
        right = rewritten[position:].lstrip("\n")
        rewritten = f"{left}\n\n{block}\n\n{right}"
    return rewritten.rstrip() + "\n"


def bootstrap_reviews(proposals: Iterable[SourceProposal]) -> tuple[LinkReview, ...]:
    grouped: dict[tuple[str, str], list[SourceProposal]] = {}
    for proposal in proposals:
        grouped.setdefault((proposal.diagnostic, proposal.standard), []).append(proposal)

    reviews: list[LinkReview] = []
    for (diagnostic, standard), items in sorted(grouped.items()):
        proposed_clauses = {item.proposed_clause for item in items}
        clause = next(iter(proposed_clauses)) if len(proposed_clauses) == 1 else None
        reviews.append(
            LinkReview.from_dict(
                {
                    "diagnostic": diagnostic,
                    "standard": standard,
                    "clause": clause,
                    "anchor": heading_anchor(clause) if clause is not None else None,
                    "evidence": sorted({item.source_url for item in items}),
                    "reason": "Unreviewed bootstrap record",
                    "review": "rejected",
                    "notes": "Source proposal retained pending semantic review.",
                }
            )
        )
    return tuple(reviews)


def write_registry(path: Path, reviews: tuple[LinkReview, ...]) -> None:
    payload = {"version": 1, "reviews": [review.to_dict() for review in reviews]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap diagnostic standard reviews")
    parser.add_argument("--catalog", type=Path, default=Path("data/diagnostic-sources.json"))
    parser.add_argument("--bslls-checkout", type=Path, required=True)
    parser.add_argument("--v8-code-style-checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/diagnostic-standard-links.json"))
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    proposals = discover_source_proposals(
        catalog,
        {"bslls": args.bslls_checkout, "v8-code-style": args.v8_code_style_checkout},
    )
    reviews = bootstrap_reviews(proposals)
    validate_review_coverage(proposals, reviews)
    write_registry(args.output, reviews)
    print(f"bootstrapped {len(reviews)} reviews from {len(proposals)} proposals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
