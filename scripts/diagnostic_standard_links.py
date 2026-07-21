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
DIAGNOSTIC_RE = re.compile(r"^(?:bslls|v8cs):[^\s:]+$")
NUMERIC_CLAUSE_RE = re.compile(r"^\d+(?:\.\d+)*$")
IMMUTABLE_GITHUB_RE = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/blob/[0-9a-f]{40}/.+$"
)
LOCAL_EVIDENCE_RE = re.compile(r"^local:docs/std/\d+\.md#[a-z0-9-]+$")
V8STD_URL_RE = re.compile(r"https://its\.1c\.ru/db/v8std[^\s<>)\"\]]*")
V8STD_NAVIGATION_RE = re.compile(
    r"^https://its\.1c\.ru/db/v8std#browse:\d+:-?\d+:\d+:\d+$"
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
            if anchor != expected_anchor:
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


def heading_anchor(clause: str) -> str:
    if STANDARD_RE.fullmatch(clause):
        return clause
    if not NUMERIC_CLAUSE_RE.fullmatch(clause):
        raise ValueError(f"unsupported clause: {clause}")
    return clause.replace(".", "")


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
    seen: set[tuple[str, str]] = set()
    for review in reviews:
        key = (review.diagnostic, review.standard)
        if key in seen:
            raise ValueError(f"duplicate relationship: {review.diagnostic} -> {review.standard}")
        seen.add(key)
    if tuple(sorted(reviews, key=lambda item: (item.diagnostic, item.standard))) != reviews:
        raise ValueError("relationship reviews must use stable diagnostic/standard sorting")
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
        if len(matches) != 1:
            raise ValueError(
                "source proposal has multiple reviews: "
                f"{proposal.diagnostic} -> {proposal.standard}"
            )


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
