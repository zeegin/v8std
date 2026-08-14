"""Structured Markdown model for v8std architecture artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml


PROCESS_SCHEMA_PATH = Path("spec/process/architecture-artifacts-v1.md")
REFERENCE_RE = re.compile(
    r"^(?P<kind>design|adr|invariant|contract|plan|process):"
    r"(?P<identity>[A-Za-z][A-Za-z0-9_-]*)"
    r"(?:@(?P<version>\d+)(?:\.(?P<revision>\d+))?)?$"
)
CHECKBOX_RE = re.compile(r"^\s*-\s+\[(?P<checked>[ xX])\]", re.MULTILINE)
REQUIREMENT_HEADING_RE = re.compile(r"^### ([A-Z][A-Z_]*)\s*$")
DATED_NAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>.+)\.md$")


class ArchitectureModelError(ValueError):
    """Raised when an artifact cannot be represented by the process model."""


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ArchitectureModelError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    identity: str
    version: int | None = None
    revision: int | None = None

    @classmethod
    def parse(cls, value: str) -> "ArtifactRef":
        match = REFERENCE_RE.fullmatch(value)
        if match is None:
            raise ArchitectureModelError(f"invalid typed reference: {value!r}")

        kind = match.group("kind")
        version_text = match.group("version")
        revision_text = match.group("revision")
        version = int(version_text) if version_text is not None else None
        revision = int(revision_text) if revision_text is not None else None

        if kind == "contract":
            if version is None or revision is None:
                raise ArchitectureModelError(
                    f"contract reference requires @version.revision: {value!r}"
                )
        elif kind == "process":
            if version is None or revision is not None:
                raise ArchitectureModelError(
                    f"process reference requires @version: {value!r}"
                )
        elif version is not None:
            raise ArchitectureModelError(
                f"{kind} reference cannot contain a version: {value!r}"
            )

        return cls(
            kind=kind,
            identity=match.group("identity"),
            version=version,
            revision=revision,
        )

    def __str__(self) -> str:
        value = f"{self.kind}:{self.identity}"
        if self.kind == "contract":
            return f"{value}@{self.version}.{self.revision}"
        if self.kind == "process":
            return f"{value}@{self.version}"
        return value


@dataclass(frozen=True)
class ProcessSchema:
    version: int
    directories: dict[str, str]
    semantic_id_pattern: re.Pattern[str]
    document_id_pattern: re.Pattern[str]
    typed_reference_pattern: re.Pattern[str]
    contract_reference_pattern: re.Pattern[str]
    adr_filename_pattern: re.Pattern[str]
    frozen_kinds: frozenset[str]
    forbidden_fields: frozenset[str]


@dataclass(frozen=True)
class ArchitectureDocument:
    path: Path
    kind: str
    identity: str
    scope: str | None
    front_matter: dict[str, object]
    body: str
    references: tuple[ArtifactRef, ...]
    created_on: date | None
    checkbox_count: int
    checked_count: int
    requirement_definitions: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        if self.kind == "contract":
            version = self.front_matter.get("version")
            revision = self.front_matter.get("revision")
            return f"contract:{self.identity}@{version if isinstance(version, int) else '?'}.{revision if isinstance(revision, int) else '?'}"
        if self.kind == "process":
            version = self.front_matter.get("version")
            return f"process:{self.identity}@{version if isinstance(version, int) else '?'}"
        return f"{self.kind}:{self.identity}"

    @property
    def is_complete_plan(self) -> bool:
        return (
            self.kind == "plan"
            and self.checkbox_count > 0
            and self.checkbox_count == self.checked_count
        )


@dataclass(frozen=True)
class ArchitectureGraph:
    documents: dict[str, ArchitectureDocument]
    aliases: dict[str, str]
    requirements: dict[str, str]
    incoming: dict[str, tuple[str, ...]]
    duplicate_keys: tuple[str, ...] = ()
    duplicate_aliases: tuple[str, ...] = ()
    duplicate_requirements: tuple[str, ...] = ()


def _split_front_matter(text: str, path: Path) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        raise ArchitectureModelError(f"{path}: missing YAML front matter")
    delimiter = text.find("\n---\n", 4)
    if delimiter < 0:
        raise ArchitectureModelError(f"{path}: unterminated YAML front matter")

    payload_text = text[4:delimiter]
    try:
        payload = yaml.load(payload_text, Loader=_UniqueKeyLoader)
    except ArchitectureModelError:
        raise
    except yaml.YAMLError as error:
        raise ArchitectureModelError(f"{path}: malformed YAML front matter: {error}") from error
    if not isinstance(payload, dict):
        raise ArchitectureModelError(f"{path}: front matter must be a mapping")
    if not all(isinstance(key, str) for key in payload):
        raise ArchitectureModelError(f"{path}: front matter keys must be strings")
    return payload, text[delimiter + 5 :]


def load_process_schema(repo_root: Path) -> ProcessSchema:
    path = repo_root / PROCESS_SCHEMA_PATH
    payload, _ = _split_front_matter(path.read_text(encoding="utf-8"), path)
    schema = payload.get("schema")
    if payload.get("kind") != "process" or not isinstance(schema, dict):
        raise ArchitectureModelError(f"{path}: invalid process schema document")

    def compile_pattern(name: str) -> re.Pattern[str]:
        value = schema.get(name)
        if not isinstance(value, str):
            raise ArchitectureModelError(f"{path}: schema.{name} must be a string")
        return re.compile(value)

    directories = schema.get("directories")
    frozen_kinds = schema.get("frozen_kinds")
    forbidden_fields = schema.get("forbidden_fields")
    if not isinstance(directories, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in directories.items()
    ):
        raise ArchitectureModelError(f"{path}: schema.directories must map strings")
    if not isinstance(frozen_kinds, list) or not all(
        isinstance(value, str) for value in frozen_kinds
    ):
        raise ArchitectureModelError(f"{path}: schema.frozen_kinds must be a list")
    if not isinstance(forbidden_fields, list) or not all(
        isinstance(value, str) for value in forbidden_fields
    ):
        raise ArchitectureModelError(f"{path}: schema.forbidden_fields must be a list")

    version = payload.get("version")
    if not isinstance(version, int):
        raise ArchitectureModelError(f"{path}: process version must be an integer")
    return ProcessSchema(
        version=version,
        directories=dict(directories),
        semantic_id_pattern=compile_pattern("semantic_id_pattern"),
        document_id_pattern=compile_pattern("document_id_pattern"),
        typed_reference_pattern=compile_pattern("typed_reference_pattern"),
        contract_reference_pattern=compile_pattern("contract_reference_pattern"),
        adr_filename_pattern=compile_pattern("adr_filename_pattern"),
        frozen_kinds=frozenset(frozen_kinds),
        forbidden_fields=frozenset(forbidden_fields),
    )


def _iter_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _iter_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_strings(nested)


def _extract_references(front_matter: dict[str, object]) -> tuple[ArtifactRef, ...]:
    references: list[ArtifactRef] = []
    for value in _iter_strings(front_matter):
        if re.match(r"^(design|adr|invariant|contract|plan|process):", value):
            references.append(ArtifactRef.parse(value))
    return tuple(references)


def _extract_requirement_definitions(body: str) -> tuple[str, ...]:
    definitions: list[str] = []
    in_requirements = False
    for line in body.splitlines():
        if line == "## Требования":
            in_requirements = True
            continue
        if line.startswith("## "):
            in_requirements = False
        if in_requirements:
            match = REQUIREMENT_HEADING_RE.fullmatch(line)
            if match is not None:
                definitions.append(match.group(1))
    return tuple(definitions)


def _parse_created_on(filename: str, path: Path) -> date:
    match = DATED_NAME_RE.fullmatch(filename)
    if match is None:
        raise ArchitectureModelError(f"{path}: filename must start with YYYY-MM-DD")
    try:
        return date.fromisoformat(match.group("date"))
    except ValueError as error:
        raise ArchitectureModelError(f"{path}: invalid Gregorian date") from error


def _semantic_slug(identity: str) -> str:
    return identity.lower().replace("_", "-")


def _validate_identity(kind: str, identity: str, schema: ProcessSchema, path: Path) -> None:
    pattern = (
        schema.semantic_id_pattern
        if kind in {"adr", "invariant", "contract"}
        else schema.document_id_pattern
    )
    if pattern.fullmatch(identity) is None:
        raise ArchitectureModelError(f"{path}: invalid {kind} id {identity!r}")


def _validate_filename(
    path: Path,
    kind: str,
    identity: str,
    payload: dict[str, object],
    schema: ProcessSchema,
) -> date | None:
    filename = path.name
    created_on: date | None = None
    if kind in {"design", "adr", "plan"}:
        created_on = _parse_created_on(filename, path)

    if kind == "adr":
        if schema.adr_filename_pattern.fullmatch(filename) is None:
            raise ArchitectureModelError(f"{path}: invalid ADR filename")
        expected_suffix = f"-{_semantic_slug(identity)}.md"
        if not filename.endswith(expected_suffix):
            raise ArchitectureModelError(f"{path}: filename does not match id {identity}")
    elif kind == "design":
        expected_suffix = f"-{identity}-design.md"
        if not filename.endswith(expected_suffix):
            raise ArchitectureModelError(f"{path}: filename does not match id {identity}")
    elif kind == "plan":
        expected_suffix = f"-{identity}-plan.md"
        if not filename.endswith(expected_suffix):
            raise ArchitectureModelError(f"{path}: filename does not match id {identity}")
    elif kind == "invariant":
        if filename != f"{_semantic_slug(identity)}.md":
            raise ArchitectureModelError(f"{path}: filename does not match id {identity}")
    elif kind == "contract":
        version = payload.get("version")
        revision = payload.get("revision")
        if not isinstance(version, int) or not isinstance(revision, int):
            raise ArchitectureModelError(f"{path}: contract version and revision must be integers")
        expected = f"{_semantic_slug(identity)}-v{version}-r{revision}.md"
        if filename != expected:
            raise ArchitectureModelError(f"{path}: filename does not match id/version")
    elif kind == "process":
        version = payload.get("version")
        if not isinstance(version, int):
            raise ArchitectureModelError(f"{path}: process version must be an integer")
        if filename != f"{identity}-v{version}.md":
            raise ArchitectureModelError(f"{path}: filename does not match id/version")
    return created_on


def load_document(
    path: Path,
    repo_root: Path,
    schema: ProcessSchema,
    *,
    validate_path: bool = True,
) -> ArchitectureDocument:
    try:
        relative_path = path.resolve().relative_to(repo_root.resolve())
    except ValueError as error:
        raise ArchitectureModelError(f"{path}: artifact is outside repository root") from error

    payload, body = _split_front_matter(path.read_text(encoding="utf-8"), relative_path)
    forbidden = schema.forbidden_fields.intersection(payload)
    if forbidden:
        field_name = sorted(forbidden)[0]
        raise ArchitectureModelError(f"{relative_path}: forbidden field {field_name!r}")

    schema_version = payload.get("schema_version")
    kind = payload.get("kind")
    identity = payload.get("id")
    if schema_version != 1:
        raise ArchitectureModelError(f"{relative_path}: schema_version must be 1")
    if not isinstance(kind, str) or kind not in schema.directories:
        raise ArchitectureModelError(f"{relative_path}: unknown artifact kind {kind!r}")
    if not isinstance(identity, str):
        raise ArchitectureModelError(f"{relative_path}: id must be a string")
    _validate_identity(kind, identity, schema, relative_path)

    created_on: date | None = None
    if validate_path:
        expected_directory = Path(schema.directories[kind])
        if relative_path.parent != expected_directory:
            raise ArchitectureModelError(
                f"{relative_path}: {kind} must be stored in {expected_directory}"
            )
        created_on = _validate_filename(relative_path, kind, identity, payload, schema)
    elif kind in {"design", "adr", "plan"} and DATED_NAME_RE.fullmatch(path.name):
        created_on = _parse_created_on(path.name, relative_path)

    scope = payload.get("scope")
    if scope is not None and not isinstance(scope, str):
        raise ArchitectureModelError(f"{relative_path}: scope must be a string")
    checkboxes = CHECKBOX_RE.findall(body)
    return ArchitectureDocument(
        path=relative_path,
        kind=kind,
        identity=identity,
        scope=scope,
        front_matter=payload,
        body=body,
        references=_extract_references(payload),
        created_on=created_on,
        checkbox_count=len(checkboxes),
        checked_count=sum(value.lower() == "x" for value in checkboxes),
        requirement_definitions=_extract_requirement_definitions(body),
    )


def discover_documents(
    repo_root: Path, schema: ProcessSchema
) -> list[ArchitectureDocument]:
    paths: set[Path] = set()
    for directory in schema.directories.values():
        artifact_directory = repo_root / directory
        if artifact_directory.exists():
            paths.update(
                path
                for path in artifact_directory.glob("*.md")
                if path.name != "README.md"
            )
    return [load_document(path, repo_root, schema) for path in sorted(paths)]


def build_graph(documents: Iterable[ArchitectureDocument]) -> ArchitectureGraph:
    document_map: dict[str, ArchitectureDocument] = {}
    duplicate_keys: set[str] = set()
    aliases: dict[str, str] = {}
    duplicate_aliases: set[str] = set()
    requirements: dict[str, str] = {}
    duplicate_requirements: set[str] = set()

    for document in documents:
        if document.key in document_map:
            duplicate_keys.add(document.key)
        else:
            document_map[document.key] = document

        aliases_value = document.front_matter.get("aliases", [])
        if isinstance(aliases_value, list):
            for alias in aliases_value:
                if not isinstance(alias, str):
                    continue
                if alias in aliases and aliases[alias] != document.key:
                    duplicate_aliases.add(alias)
                else:
                    aliases[alias] = document.key

        for requirement in document.requirement_definitions:
            if requirement in requirements and requirements[requirement] != document.key:
                duplicate_requirements.add(requirement)
            else:
                requirements[requirement] = document.key

    incoming_lists: dict[str, list[str]] = {key: [] for key in document_map}
    for source_key, document in document_map.items():
        for reference in document.references:
            target_key = str(reference)
            if target_key in incoming_lists:
                incoming_lists[target_key].append(source_key)

    return ArchitectureGraph(
        documents=document_map,
        aliases=aliases,
        requirements=requirements,
        incoming={
            key: tuple(sorted(values)) for key, values in sorted(incoming_lists.items())
        },
        duplicate_keys=tuple(sorted(duplicate_keys)),
        duplicate_aliases=tuple(sorted(duplicate_aliases)),
        duplicate_requirements=tuple(sorted(duplicate_requirements)),
    )
