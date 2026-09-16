from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+$")


@dataclass(frozen=True)
class SourceFamily:
    family: str
    repository: str
    revision: str
    license: str
    source_root: str


@dataclass(frozen=True)
class SourceEntry:
    id: str
    source_path: str
    source_url: str
    content_sha256: str


@dataclass(frozen=True)
class SourceCatalog:
    families: tuple[SourceFamily, ...]
    diagnostics: dict[str, tuple[SourceEntry, ...]]

    def family(self, name: str) -> SourceFamily:
        for family in self.families:
            if family.family == name:
                return family
        raise KeyError(name)

    def ids(self, name: str) -> set[str]:
        return {entry.id for entry in self.diagnostics[name]}


@dataclass(frozen=True)
class LocalShell:
    marker: str
    title: str
    metadata: tuple[str, ...]
    standards_markdown: str


def normalize_article(source: str) -> tuple[str, str]:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    # Markdown source articles occasionally contain spaces and tabs at EOL.
    # They carry no semantic information here, make generated pages fail
    # ``git diff --check`` and would otherwise return on every synchronization.
    lines = [line.rstrip() for line in normalized.splitlines()]
    first = next((index for index, line in enumerate(lines) if line.strip()), None)
    heading = re.fullmatch(r"#(?!#)\s*(.+)", lines[first]) if first is not None else None
    if heading is None:
        raise ValueError("first non-empty line must be H1")

    title = heading.group(1).strip()
    body = "\n".join(lines[first + 1 :]).strip() + "\n"
    return title, body


def content_sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def immutable_source_url(family: SourceFamily, path: str) -> str:
    if not GITHUB_REPOSITORY_RE.fullmatch(family.repository):
        raise ValueError(f"unsupported GitHub repository URL: {family.repository}")
    if not FULL_SHA_RE.fullmatch(family.revision):
        raise ValueError(f"source revision must be a full lowercase SHA: {family.revision}")
    normalized_path = path.strip("/")
    if not normalized_path or ".." in normalized_path.split("/"):
        raise ValueError(f"invalid source path: {path}")
    return f"{family.repository}/blob/{family.revision}/{normalized_path}"


def verify_checkout_revision(checkout: Path, expected: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    actual = result.stdout.strip()
    if actual != expected:
        raise ValueError(f"checkout revision mismatch: expected {expected}, got {actual}")


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def render_article(
    *,
    marker: str,
    title: str,
    metadata: list[str],
    body: str,
    entry: SourceEntry,
    family: SourceFamily,
    standards_markdown: str,
) -> str:
    metadata_block = "\n".join(metadata).strip()
    standards = standards_markdown.strip() or "Нет подтверждённых связей со стандартами."
    parts = [
        f"###### {marker}",
        f"# {title}",
    ]
    if metadata_block:
        parts.append(metadata_block)
    parts.extend(
        [
            "\n".join(
                [
                    "<!-- diagnostic-source:start",
                    f"source_url={entry.source_url}",
                    f"source_path={entry.source_path}",
                    f"revision={family.revision}",
                    f"SPDX-License-Identifier: {family.license}",
                    f"sha256={entry.content_sha256}",
                    "-->",
                ]
            ),
            body.strip(),
            "<!-- diagnostic-source:end -->",
            "\n".join(
                [
                    "<!-- diagnostic-standards:start -->",
                    "## Соответствие стандартам",
                    "",
                    standards,
                    "<!-- diagnostic-standards:end -->",
                ]
            ),
            "\n".join(
                [
                    "## Источник диагностики",
                    "",
                    f"- [Исходная статья]({entry.source_url})",
                    f"- Ревизия: `{family.revision}`",
                    f"- Лицензия: `{family.license}`",
                ]
            ),
        ]
    )
    return "\n\n".join(parts).rstrip() + "\n"


def extract_local_shell(content: str) -> LocalShell:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    marker_match = re.search(r"^######\s+([^\s]+)\s*$", normalized, re.MULTILINE)
    title_match = re.search(r"^#\s+(.+?)\s*$", normalized, re.MULTILINE)
    if marker_match is None or title_match is None:
        raise ValueError("diagnostic page must contain a marker and H1 title")

    after_title = normalized[title_match.end() :].lstrip("\n")
    metadata: list[str] = []
    for line in after_title.splitlines():
        if line.startswith("- "):
            metadata.append(line.rstrip())
            continue
        if not line.strip() and not metadata:
            continue
        if not line.strip() and metadata:
            continue
        break

    legacy = re.search(
        r"^######\s+Стандарт\s*$\n(?P<body>.*?)(?=^######\s+Источник\s*$|\Z)",
        normalized,
        re.MULTILINE | re.DOTALL,
    )
    managed_region = re.search(
        r"^<!-- diagnostic-standards:start -->\s*$\n"
        r"^##\s+Соответствие стандартам\s*$\n"
        r"(?P<body>.*?)"
        r"^<!-- diagnostic-standards:end -->\s*$",
        normalized,
        re.MULTILINE | re.DOTALL,
    )
    managed_legacy = re.search(
        r"^##\s+Соответствие стандартам\s*$\n(?P<body>.*?)(?=^##\s+Источник диагностики\s*$|\Z)",
        normalized,
        re.MULTILINE | re.DOTALL,
    )
    section = managed_region or managed_legacy or legacy
    standards = section.group("body").strip() + "\n" if section else ""
    return LocalShell(
        marker=marker_match.group(1),
        title=title_match.group(1).strip(),
        metadata=tuple(metadata),
        standards_markdown=standards,
    )


def discover_family(
    checkout: Path,
    family: SourceFamily,
) -> dict[str, tuple[Path, str, str]]:
    source_root = checkout / family.source_root
    if family.family == "bslls":
        paths = source_root.glob("*.md")
    elif family.family == "v8-code-style":
        paths = source_root.glob("**/markdown/ru/*.md")
    else:
        raise ValueError(f"unsupported diagnostic family: {family.family}")

    discovered: dict[str, tuple[Path, str, str]] = {}
    for source_path in sorted(paths):
        if source_path.name == "index.md":
            continue
        relative = source_path.relative_to(checkout)
        title, body = normalize_article(source_path.read_text(encoding="utf-8"))
        if source_path.stem in discovered:
            raise ValueError(f"duplicate upstream diagnostic id: {source_path.stem}")
        discovered[source_path.stem] = (relative, title, body)
    return discovered


def _exact_fields(payload: dict[str, Any], expected: set[str], context: str) -> None:
    unknown = set(payload) - expected
    missing = expected - set(payload)
    if unknown:
        raise ValueError(f"unknown {context} fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ValueError(f"missing {context} fields: {', '.join(sorted(missing))}")


def load_catalog(path: Path) -> SourceCatalog:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source catalog must be a JSON object")
    _exact_fields(payload, {"version", "families"}, "catalog")
    if payload["version"] != 1 or not isinstance(payload["families"], list):
        raise ValueError("source catalog requires version 1 and a families array")

    families: list[SourceFamily] = []
    diagnostics: dict[str, tuple[SourceEntry, ...]] = {}
    family_fields = {
        "family",
        "repository",
        "revision",
        "license",
        "source_root",
        "diagnostics",
    }
    entry_fields = {"id", "source_path", "source_url", "content_sha256"}
    seen_families: set[str] = set()
    for raw_family in payload["families"]:
        if not isinstance(raw_family, dict):
            raise ValueError("family entry must be a JSON object")
        _exact_fields(raw_family, family_fields, "family")
        family = SourceFamily(
            family=str(raw_family["family"]),
            repository=str(raw_family["repository"]),
            revision=str(raw_family["revision"]),
            license=str(raw_family["license"]),
            source_root=str(raw_family["source_root"]),
        )
        if family.family in seen_families:
            raise ValueError(f"duplicate family: {family.family}")
        immutable_source_url(family, f"{family.source_root}/probe.md")
        seen_families.add(family.family)

        entries: list[SourceEntry] = []
        seen_ids: set[str] = set()
        if not isinstance(raw_family["diagnostics"], list):
            raise ValueError(f"diagnostics must be an array for {family.family}")
        for raw_entry in raw_family["diagnostics"]:
            if not isinstance(raw_entry, dict):
                raise ValueError("diagnostic entry must be a JSON object")
            _exact_fields(raw_entry, entry_fields, "diagnostic")
            entry = SourceEntry(
                id=str(raw_entry["id"]),
                source_path=str(raw_entry["source_path"]),
                source_url=str(raw_entry["source_url"]),
                content_sha256=str(raw_entry["content_sha256"]),
            )
            if entry.id in seen_ids:
                raise ValueError(f"duplicate diagnostic id in {family.family}: {entry.id}")
            if entry.source_url != immutable_source_url(family, entry.source_path):
                raise ValueError(f"noncanonical source URL for {family.family}:{entry.id}")
            if not re.fullmatch(r"[0-9a-f]{64}", entry.content_sha256):
                raise ValueError(f"invalid content hash for {family.family}:{entry.id}")
            seen_ids.add(entry.id)
            entries.append(entry)
        families.append(family)
        diagnostics[family.family] = tuple(entries)
    return SourceCatalog(tuple(families), diagnostics)


def _catalog_json(
    families: tuple[SourceFamily, ...],
    entries_by_family: dict[str, list[SourceEntry]],
) -> str:
    payload = {
        "version": 1,
        "families": [
            {
                "family": family.family,
                "repository": family.repository,
                "revision": family.revision,
                "license": family.license,
                "source_root": family.source_root,
                "diagnostics": [
                    {
                        "id": entry.id,
                        "source_path": entry.source_path,
                        "source_url": entry.source_url,
                        "content_sha256": entry.content_sha256,
                    }
                    for entry in sorted(
                        entries_by_family[family.family], key=lambda item: item.id.casefold()
                    )
                ],
            }
            for family in families
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def synchronize_articles(
    *,
    repo_root: Path,
    checkouts: dict[str, Path],
    families: tuple[SourceFamily, ...],
    write: bool,
) -> list[Path]:
    acc_root = repo_root / "docs/diagnostics/acc"
    acc_before = hash_tree(acc_root)
    entries_by_family: dict[str, list[SourceEntry]] = {}
    rendered_pages: dict[Path, str] = {}

    for family in families:
        checkout = checkouts.get(family.family)
        if checkout is None:
            raise ValueError(f"missing source checkout for {family.family}")
        verify_checkout_revision(checkout, family.revision)
        discovered = discover_family(checkout, family)
        local_root = repo_root / "docs/diagnostics" / family.family
        local_paths = {
            path.stem: path
            for path in local_root.glob("*.md")
            if path.name != "index.md"
        }
        if set(discovered) != set(local_paths):
            missing_local = sorted(set(discovered) - set(local_paths), key=str.casefold)
            missing_source = sorted(set(local_paths) - set(discovered), key=str.casefold)
            raise ValueError(
                f"catalog composition mismatch for {family.family}: "
                f"missing local={missing_local}, missing source={missing_source}"
            )

        family_entries: list[SourceEntry] = []
        for diagnostic_id in sorted(discovered, key=str.casefold):
            source_path, source_title, body = discovered[diagnostic_id]
            entry = SourceEntry(
                id=diagnostic_id,
                source_path=source_path.as_posix(),
                source_url=immutable_source_url(family, source_path.as_posix()),
                content_sha256=content_sha256(body),
            )
            family_entries.append(entry)
            local_path = local_paths[diagnostic_id]
            shell = extract_local_shell(local_path.read_text(encoding="utf-8"))
            expected_marker_prefix = "bslls:" if family.family == "bslls" else "v8cs:"
            expected_marker = expected_marker_prefix + diagnostic_id
            if shell.marker != expected_marker:
                raise ValueError(
                    f"marker mismatch in {local_path}: expected {expected_marker}, got {shell.marker}"
                )
            title = source_title
            if not title.endswith(f"({diagnostic_id})"):
                title = f"{title} ({diagnostic_id})"
            rendered_pages[local_path] = render_article(
                marker=expected_marker,
                title=title,
                metadata=list(shell.metadata),
                body=body,
                entry=entry,
                family=family,
                standards_markdown=shell.standards_markdown,
            )
        entries_by_family[family.family] = family_entries

    manifest_path = repo_root / "data/diagnostic-sources.json"
    expected_files = {manifest_path: _catalog_json(families, entries_by_family), **rendered_pages}
    changed = [
        path
        for path, expected in expected_files.items()
        if not path.exists() or path.read_text(encoding="utf-8") != expected
    ]
    if write:
        for path in changed:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected_files[path], encoding="utf-8")

    if hash_tree(acc_root) != acc_before:
        raise RuntimeError("ACC diagnostic tree changed during article synchronization")
    return changed
