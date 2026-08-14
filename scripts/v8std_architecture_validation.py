"""Graph, lifecycle and merge-readiness rules for architecture artifacts."""

from __future__ import annotations

import importlib.util
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from scripts.v8std_architecture_model import ArchitectureDocument, ArchitectureGraph


@dataclass(frozen=True, order=True)
class ValidationIssue:
    code: str
    path: str
    message: str


REQUIRED_FIELDS: Mapping[str, frozenset[str]] = {
    "design": frozenset(
        {
            "scope",
            "requirements",
            "decisions",
            "invariants",
            "contracts",
            "plans",
            "supersedes",
            "cancels",
        }
    ),
    "adr": frozenset(
        {
            "scope",
            "design",
            "requirements",
            "aliases",
            "supersedes",
            "cancels",
            "invariants",
            "contracts",
        }
    ),
    "invariant": frozenset({"scope", "introduced_by", "requirements", "check"}),
    "contract": frozenset(
        {
            "scope",
            "version",
            "revision",
            "compatibility",
            "design",
            "producer",
            "consumers",
            "requirements",
            "governs",
            "conformance",
            "supersedes",
            "deprecates",
        }
    ),
    "plan": frozenset({"design", "implements"}),
    "process": frozenset({"version", "schema"}),
}

REFERENCE_FIELDS: Mapping[str, Mapping[str, frozenset[str]]] = {
    "design": {
        "decisions": frozenset({"adr"}),
        "invariants": frozenset({"invariant"}),
        "contracts": frozenset({"contract"}),
        "plans": frozenset({"plan"}),
        "supersedes": frozenset({"design"}),
        "cancels": frozenset({"design"}),
    },
    "adr": {
        "design": frozenset({"design"}),
        "supersedes": frozenset({"adr"}),
        "cancels": frozenset({"adr"}),
        "invariants": frozenset({"invariant"}),
        "contracts": frozenset({"contract"}),
    },
    "invariant": {"introduced_by": frozenset({"adr"})},
    "contract": {
        "design": frozenset({"design"}),
        "supersedes": frozenset({"contract"}),
        "deprecates": frozenset({"contract"}),
    },
    "plan": {
        "design": frozenset({"design"}),
        "implements": frozenset({"design", "adr", "invariant", "contract", "process"}),
    },
    "process": {},
}


def _issue(document: ArchitectureDocument, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(code, document.path.as_posix(), message)


def _values(value: object) -> Iterable[object]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _values(nested)
    else:
        yield value


def _typed_values(value: object) -> Iterable[str]:
    for nested in _values(value):
        if isinstance(nested, str) and nested.startswith(
            ("design:", "adr:", "invariant:", "contract:", "plan:", "process:")
        ):
            yield nested


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): nested for key, nested in value.items()}


def _reference_key(value: str) -> str:
    return value


def validate_references(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for key in graph.duplicate_keys:
        document = graph.documents[key]
        issues.append(_issue(document, "DUPLICATE_IDENTITY", f"duplicate canonical identity {key}"))
    for alias in graph.duplicate_aliases:
        issues.append(ValidationIssue("DUPLICATE_ALIAS", "spec", f"duplicate historical alias {alias}"))
    for requirement in graph.duplicate_requirements:
        issues.append(
            ValidationIssue(
                "DUPLICATE_REQUIREMENT",
                "spec",
                f"requirement {requirement} has multiple definitions",
            )
        )

    for document in graph.documents.values():
        for field in sorted(REQUIRED_FIELDS.get(document.kind, frozenset())):
            if field not in document.front_matter:
                issues.append(_issue(document, "MISSING_REQUIRED_FIELD", f"missing required field {field}"))

        for reference in document.references:
            key = str(reference)
            if reference.kind == "adr" and reference.identity in graph.aliases:
                issues.append(
                    _issue(
                        document,
                        "HISTORICAL_ALIAS_REFERENCE",
                        f"current front matter uses historical alias {reference.identity}",
                    )
                )
                continue
            if key not in graph.documents:
                issues.append(_issue(document, "DANGLING_REFERENCE", f"reference {key} does not resolve"))

        for field, allowed_kinds in REFERENCE_FIELDS.get(document.kind, {}).items():
            value = document.front_matter.get(field)
            for reference_text in _typed_values(value):
                reference_kind = reference_text.split(":", 1)[0]
                if reference_kind not in allowed_kinds:
                    issues.append(
                        _issue(
                            document,
                            "INVALID_REFERENCE_TYPE",
                            f"field {field} cannot reference {reference_text}",
                        )
                    )
    return issues


def _requirement_fields(document: ArchitectureDocument) -> list[str]:
    value = document.front_matter.get("requirements")
    if document.kind == "design":
        requirements = _mapping(value)
        result = _string_list(requirements.get("uses"))
        replaces = _mapping(requirements.get("replaces"))
        result.extend(replaces)
        result.extend(value for value in replaces.values() if isinstance(value, str))
        result.extend(_string_list(requirements.get("cancels")))
        return result
    return _string_list(value)


def _requirement_lifecycle(graph: ArchitectureGraph) -> tuple[set[str], dict[str, str]]:
    cancelled: set[str] = set()
    replaced: dict[str, str] = {}
    for document in graph.documents.values():
        if document.kind != "design":
            continue
        requirements = _mapping(document.front_matter.get("requirements"))
        cancelled.update(_string_list(requirements.get("cancels")))
        for old, new in _mapping(requirements.get("replaces")).items():
            if isinstance(new, str):
                replaced[old] = new
    return cancelled, replaced


def _has_mapping_cycle(edges: Mapping[str, str]) -> bool:
    for origin in edges:
        seen: set[str] = set()
        current = origin
        while current in edges:
            if current in seen:
                return True
            seen.add(current)
            current = edges[current]
    return False


def validate_requirements(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    cancelled, replaced = _requirement_lifecycle(graph)
    if _has_mapping_cycle(replaced):
        issues.append(
            ValidationIssue(
                "RELATION_CYCLE",
                "spec/designs",
                "requirement replacement graph contains a cycle",
            )
        )

    process_requirements = {
        code
        for code, owner in graph.requirements.items()
        if graph.documents.get(owner) is not None and graph.documents[owner].scope == "process"
    }

    for document in graph.documents.values():
        if document.kind == "design":
            requirements = _mapping(document.front_matter.get("requirements"))
            introduced = set(_string_list(requirements.get("introduces")))
            defined = set(document.requirement_definitions)
            for code in sorted(introduced - defined):
                issues.append(
                    _issue(document, "MISSING_REQUIREMENT_DEFINITION", f"{code} has no ### definition")
                )
            for code in sorted(defined - introduced):
                issues.append(
                    _issue(document, "UNDECLARED_REQUIREMENT", f"{code} is not listed in introduces")
                )

        for code in _requirement_fields(document):
            if code not in graph.requirements:
                issues.append(_issue(document, "UNDEFINED_REQUIREMENT", f"requirement {code} is undefined"))
                continue
            if code in cancelled and document.key != graph.requirements.get(code):
                issues.append(_issue(document, "CANCELLED_REQUIREMENT", f"requirement {code} is cancelled"))
            if document.scope == "product" and code in process_requirements:
                issues.append(
                    _issue(
                        document,
                        "PROCESS_REQUIREMENT_USED_BY_PRODUCT",
                        f"product architecture cannot use process requirement {code}",
                    )
                )

    for successor in graph.documents.values():
        if successor.kind != "design":
            continue
        lifecycle = _mapping(successor.front_matter.get("requirements"))
        handled = set(_string_list(lifecycle.get("uses")))
        handled.update(_mapping(lifecycle.get("replaces")))
        handled.update(_string_list(lifecycle.get("cancels")))
        for predecessor_ref in _string_list(successor.front_matter.get("supersedes")):
            predecessor = graph.documents.get(predecessor_ref)
            if predecessor is None or predecessor.kind != "design":
                continue
            predecessor_requirements = _mapping(predecessor.front_matter.get("requirements"))
            for code in _string_list(predecessor_requirements.get("introduces")):
                if code not in handled:
                    issues.append(
                        _issue(
                            successor,
                            "DROPPED_REQUIREMENT",
                            f"superseded requirement {code} is not preserved, replaced or cancelled",
                        )
                    )
    return issues


def _relation_values(document: ArchitectureDocument, field: str) -> set[str]:
    return set(_string_list(document.front_matter.get(field)))


def _relation_cycle(graph: ArchitectureGraph, fields: tuple[str, ...]) -> set[str]:
    edges: dict[str, set[str]] = defaultdict(set)
    for document in graph.documents.values():
        for field in fields:
            for target in _relation_values(document, field):
                if target in graph.documents:
                    edges[document.key].add(target)

    involved: set[str] = set()
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            start = trail.index(node)
            involved.update(trail[start:])
            return
        if node in visited:
            return
        visiting.add(node)
        trail.append(node)
        for target in edges.get(node, set()):
            visit(target, trail)
        trail.pop()
        visiting.remove(node)
        visited.add(node)

    for node in edges:
        visit(node, [])
    return involved


def validate_adr_relations(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for key in sorted(_relation_cycle(graph, ("supersedes", "cancels"))):
        issues.append(_issue(graph.documents[key], "RELATION_CYCLE", "artifact lifecycle contains a cycle"))

    successors: dict[str, list[ArchitectureDocument]] = defaultdict(list)
    for document in graph.documents.values():
        supersedes = _relation_values(document, "supersedes")
        cancels = _relation_values(document, "cancels")
        for predecessor in supersedes:
            successors[predecessor].append(document)
        for target in sorted(supersedes.intersection(cancels)):
            issues.append(
                _issue(
                    document,
                    "MIXED_CANCEL_AND_SUPERSEDE",
                    f"{target} is both cancelled and superseded",
                )
            )

    for predecessor, replacements in successors.items():
        adr_replacements = [document for document in replacements if document.kind == "adr"]
        if len(adr_replacements) < 2:
            continue
        designs = {
            document.front_matter.get("design")
            for document in adr_replacements
            if isinstance(document.front_matter.get("design"), str)
        }
        if len(designs) > 1:
            for document in adr_replacements:
                issues.append(
                    _issue(
                        document,
                        "COMPOSITE_REPLACEMENT_SPLIT",
                        f"replacement of {predecessor} is split between designs",
                    )
                )
    return issues


def _check_declaration_present(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        module = value.get("module")
        command = value.get("command")
        return bool(
            (isinstance(module, str) and module.strip())
            or (isinstance(command, str) and command.strip())
        )
    return False


def validate_invariants(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    cancelled_requirements, _ = _requirement_lifecycle(graph)
    for document in graph.documents.values():
        if document.kind != "invariant":
            continue
        basis = document.front_matter.get("introduced_by")
        requirements = _string_list(document.front_matter.get("requirements"))
        if not isinstance(basis, str) or not basis.startswith("adr:") or not requirements:
            issues.append(
                _issue(
                    document,
                    "INVARIANT_WITHOUT_BASIS",
                    "invariant requires an introducing ADR and at least one requirement",
                )
            )
        if not _check_declaration_present(document.front_matter.get("check")):
            issues.append(_issue(document, "INVARIANT_WITHOUT_CHECK", "invariant has no check declaration"))

    for decision in graph.documents.values():
        if decision.kind != "adr":
            continue
        impact = _mapping(decision.front_matter.get("invariants"))
        for target in _string_list(impact.get("cancels")):
            invariant = graph.documents.get(target)
            if invariant is None or invariant.kind != "invariant":
                continue
            active = [
                code
                for code in _string_list(invariant.front_matter.get("requirements"))
                if code not in cancelled_requirements
            ]
            if active:
                issues.append(
                    _issue(
                        decision,
                        "PREMATURE_RETIREMENT",
                        f"{target} is retired while requirements remain active: {', '.join(active)}",
                    )
                )
    return issues


def validate_contracts(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for document in graph.documents.values():
        if document.kind != "contract":
            continue
        version = document.front_matter.get("version")
        revision = document.front_matter.get("revision")
        if not isinstance(version, int) or version < 1:
            issues.append(_issue(document, "CONTRACT_WITHOUT_VERSION", "contract version must be positive"))
        if not isinstance(revision, int) or revision < 0:
            issues.append(_issue(document, "INVALID_CONTRACT_REVISION", "contract revision must be non-negative"))
        compatibility = document.front_matter.get("compatibility")
        if compatibility not in {"backward-compatible", "breaking"}:
            issues.append(_issue(document, "INVALID_COMPATIBILITY", "invalid contract compatibility"))
        producer = document.front_matter.get("producer")
        if not isinstance(producer, str) or not producer.strip():
            issues.append(_issue(document, "CONTRACT_WITHOUT_PRODUCER", "contract producer is empty"))
        if not _string_list(document.front_matter.get("consumers")):
            issues.append(_issue(document, "CONTRACT_WITHOUT_CONSUMERS", "contract consumers are empty"))
        if not _check_declaration_present(document.front_matter.get("conformance")):
            issues.append(_issue(document, "CONTRACT_WITHOUT_CONFORMANCE", "contract has no conformance declaration"))
    return issues


def validate_plans(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for document in graph.documents.values():
        if document.kind == "plan" and document.checkbox_count == 0:
            issues.append(_issue(document, "PLAN_WITHOUT_CHECKBOX", "plan must contain a checkbox"))
    return issues


def validate_graph(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(validate_references(graph))
    issues.extend(validate_requirements(graph))
    issues.extend(validate_adr_relations(graph))
    issues.extend(validate_invariants(graph))
    issues.extend(validate_contracts(graph))
    issues.extend(validate_plans(graph))
    return sorted(set(issues))


def _declared_module(document: ArchitectureDocument) -> str | None:
    field_name = "check" if document.kind == "invariant" else "conformance"
    declaration = document.front_matter.get(field_name)
    if isinstance(declaration, dict):
        module = declaration.get("module")
        if isinstance(module, str) and module:
            return module
    return None


def _module_exists(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def validate_merge_readiness(graph: ArchitectureGraph) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for document in graph.documents.values():
        if document.kind == "plan" and not document.is_complete_plan:
            issues.append(_issue(document, "INCOMPLETE_PLAN", "plan is not complete"))

    accepted_keys = frozenset(graph.documents)
    states = compute_states(graph, accepted_keys)
    for document in graph.documents.values():
        if document.kind not in {"invariant", "contract"}:
            continue
        required_when = document.front_matter.get("required_when", "accepted")
        must_exist = required_when == "accepted" or (
            required_when == "implemented" and "IMPLEMENTED" in states[document.key]
        )
        module = _declared_module(document)
        if must_exist and (module is None or not _module_exists(module)):
            issues.append(
                _issue(
                    document,
                    "MISSING_FITNESS_EVIDENCE",
                    f"required Python test module is unavailable: {module or '<missing>'}",
                )
            )
    return sorted(set(issues))


def _impact_targets(document: ArchitectureDocument, field: str) -> set[str]:
    impact = _mapping(document.front_matter.get(field))
    result = set(_string_list(impact.get("cancels")))
    result.update(_mapping(impact.get("replaces")))
    return result


def compute_states(
    graph: ArchitectureGraph, accepted_keys: frozenset[str]
) -> dict[str, frozenset[str]]:
    states: dict[str, set[str]] = {
        key: ({"ACCEPTED"} if key in accepted_keys else {"CANDIDATE"})
        for key in graph.documents
    }

    for document in graph.documents.values():
        if document.key not in accepted_keys:
            continue
        for target in _string_list(document.front_matter.get("supersedes")):
            if target in states:
                states[target].discard("ACCEPTED")
                states[target].add("SUPERSEDED")
        for target in _string_list(document.front_matter.get("cancels")):
            if target in states:
                states[target].discard("ACCEPTED")
                states[target].add("CANCELLED")
        if document.kind == "adr":
            for target in _impact_targets(document, "invariants"):
                if target in states:
                    states[target].discard("ACCEPTED")
                    states[target].add("RETIRED")
            for target in _impact_targets(document, "contracts"):
                if target in states:
                    states[target].discard("ACCEPTED")
                    states[target].add("DEPRECATED")
        if document.kind == "contract":
            for target in _string_list(document.front_matter.get("deprecates")):
                if target in states:
                    states[target].discard("ACCEPTED")
                    states[target].add("DEPRECATED")

    for document in graph.documents.values():
        if (
            document.kind != "plan"
            or document.key not in accepted_keys
            or not document.is_complete_plan
        ):
            continue
        for target in _string_list(document.front_matter.get("implements")):
            if target in states and target in accepted_keys:
                states[target].add("IMPLEMENTED")

    return {key: frozenset(value) for key, value in sorted(states.items())}
