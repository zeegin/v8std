from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from scripts.v8std_architecture_model import (
    ArchitectureDocument,
    ArtifactRef,
    build_graph,
)
from scripts.v8std_architecture_validation import (
    compute_states,
    validate_graph,
    validate_merge_readiness,
)


def _references(value: object) -> Iterable[ArtifactRef]:
    if isinstance(value, str) and value.startswith(
        ("design:", "adr:", "invariant:", "contract:", "plan:", "process:")
    ):
        yield ArtifactRef.parse(value)
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _references(nested)


def document(
    kind: str,
    identity: str,
    *,
    body: str = "",
    checkbox_count: int = 0,
    checked_count: int = 0,
    requirement_definitions: tuple[str, ...] = (),
    **fields: Any,
) -> ArchitectureDocument:
    front_matter: dict[str, object] = {
        "schema_version": 1,
        "kind": kind,
        "id": identity,
        **fields,
    }
    suffix = identity.lower().replace("_", "-")
    if kind == "contract":
        filename = f"{suffix}-v{fields.get('version', 1)}-r{fields.get('revision', 0)}.md"
    elif kind == "process":
        filename = f"{suffix}-v{fields.get('version', 1)}.md"
    else:
        filename = f"{suffix}.md"
    return ArchitectureDocument(
        path=Path("spec") / kind / filename,
        kind=kind,
        identity=identity,
        scope=fields.get("scope") if isinstance(fields.get("scope"), str) else None,
        front_matter=front_matter,
        body=body,
        references=tuple(_references(front_matter)),
        created_on=date(2026, 8, 14) if kind in {"design", "adr", "plan"} else None,
        checkbox_count=checkbox_count,
        checked_count=checked_count,
        requirement_definitions=requirement_definitions,
    )


def design(
    identity: str,
    *,
    scope: str = "product",
    introduces: tuple[str, ...] = (),
    uses: tuple[str, ...] = (),
    replaces: dict[str, str] | None = None,
    requirement_cancels: tuple[str, ...] = (),
    supersedes: tuple[str, ...] = (),
    cancels: tuple[str, ...] = (),
) -> ArchitectureDocument:
    return document(
        "design",
        identity,
        scope=scope,
        requirements={
            "introduces": list(introduces),
            "uses": list(uses),
            "replaces": replaces or {},
            "cancels": list(requirement_cancels),
        },
        decisions=[],
        invariants=[],
        contracts=[],
        supersedes=list(supersedes),
        cancels=list(cancels),
        requirement_definitions=introduces,
    )


def adr(
    identity: str,
    design_ref: str,
    *,
    requirements: tuple[str, ...] = (),
    aliases: tuple[str, ...] = (),
    supersedes: tuple[str, ...] = (),
    cancels: tuple[str, ...] = (),
    invariants: dict[str, object] | None = None,
    contracts: dict[str, object] | None = None,
    body: str = "",
) -> ArchitectureDocument:
    return document(
        "adr",
        identity,
        scope="product",
        design=design_ref,
        requirements=list(requirements),
        aliases=list(aliases),
        supersedes=list(supersedes),
        cancels=list(cancels),
        invariants=invariants
        or {"introduces": [], "preserves": [], "replaces": {}, "cancels": []},
        contracts=contracts
        or {"introduces": [], "preserves": [], "replaces": {}, "cancels": []},
        body=body,
    )


def codes(issues: Iterable[object]) -> set[str]:
    return {getattr(issue, "code") for issue in issues}


class ArchitectureValidationTest(unittest.TestCase):
    def test_reports_dangling_wrong_type_and_duplicate_references(self) -> None:
        feature = design("feature", introduces=("FEATURE_EXISTS",))
        decision = adr("FEATURE_DECISION", "design:feature", requirements=("FEATURE_EXISTS",))
        wrong_plan = document(
            "plan",
            "wrong",
            design="adr:FEATURE_DECISION",
            implements=["design:missing"],
            checkbox_count=1,
            checked_count=1,
        )
        duplicate = document(
            "adr",
            "FEATURE_DECISION",
            scope="product",
            design="design:feature",
            requirements=["FEATURE_EXISTS"],
            aliases=[],
            supersedes=[],
            cancels=[],
            invariants={"introduces": [], "preserves": [], "replaces": {}, "cancels": []},
            contracts={"introduces": [], "preserves": [], "replaces": {}, "cancels": []},
        )

        issue_codes = codes(validate_graph(build_graph([feature, decision, wrong_plan, duplicate])))

        self.assertIn("DANGLING_REFERENCE", issue_codes)
        self.assertIn("INVALID_REFERENCE_TYPE", issue_codes)
        self.assertIn("DUPLICATE_IDENTITY", issue_codes)

    def test_reports_relation_cycle_and_mixed_cancel_supersede(self) -> None:
        first = design("first", supersedes=("design:second",))
        second = design("second", supersedes=("design:first",))
        mixed = design(
            "mixed",
            supersedes=("design:first",),
            cancels=("design:first",),
        )

        issue_codes = codes(validate_graph(build_graph([first, second, mixed])))

        self.assertIn("RELATION_CYCLE", issue_codes)
        self.assertIn("MIXED_CANCEL_AND_SUPERSEDE", issue_codes)

    def test_allows_one_to_many_and_many_to_one_adr_replacements_within_design(self) -> None:
        feature = design("feature")
        old_one = adr("OLD_ONE", "design:feature")
        old_two = adr("OLD_TWO", "design:feature")
        new_one = adr("NEW_ONE", "design:feature", supersedes=("adr:OLD_ONE", "adr:OLD_TWO"))
        new_two = adr("NEW_TWO", "design:feature", supersedes=("adr:OLD_ONE",))

        issue_codes = codes(
            validate_graph(build_graph([feature, old_one, old_two, new_one, new_two]))
        )

        self.assertNotIn("COMPOSITE_REPLACEMENT_SPLIT", issue_codes)

    def test_rejects_composite_replacement_split_between_designs(self) -> None:
        first_design = design("first")
        second_design = design("second")
        old = adr("OLD", "design:first")
        first_successor = adr("FIRST_SUCCESSOR", "design:first", supersedes=("adr:OLD",))
        second_successor = adr("SECOND_SUCCESSOR", "design:second", supersedes=("adr:OLD",))

        issue_codes = codes(
            validate_graph(
                build_graph(
                    [first_design, second_design, old, first_successor, second_successor]
                )
            )
        )

        self.assertIn("COMPOSITE_REPLACEMENT_SPLIT", issue_codes)

    def test_reports_undefined_cancelled_and_dropped_requirements(self) -> None:
        original = design("original", introduces=("ORIGINAL_REQUIREMENT",))
        successor = design(
            "successor",
            supersedes=("design:original",),
            requirement_cancels=("ORIGINAL_REQUIREMENT",),
        )
        undefined = adr(
            "UNDEFINED_USER",
            "design:successor",
            requirements=("UNKNOWN_REQUIREMENT",),
        )
        cancelled = adr(
            "CANCELLED_USER",
            "design:successor",
            requirements=("ORIGINAL_REQUIREMENT",),
        )
        dropping = design("dropping", supersedes=("design:original",))

        issue_codes = codes(
            validate_graph(
                build_graph([original, successor, undefined, cancelled, dropping])
            )
        )

        self.assertIn("UNDEFINED_REQUIREMENT", issue_codes)
        self.assertIn("CANCELLED_REQUIREMENT", issue_codes)
        self.assertIn("DROPPED_REQUIREMENT", issue_codes)

    def test_allows_comprehensive_requirement_cancellation(self) -> None:
        original = design("original", introduces=("ORIGINAL_REQUIREMENT",))
        old_decision = adr(
            "OLD_DECISION",
            "design:original",
            requirements=("ORIGINAL_REQUIREMENT",),
        )
        successor = design(
            "successor",
            introduces=("NEW_DIRECTION",),
            requirement_cancels=("ORIGINAL_REQUIREMENT",),
            supersedes=("design:original",),
        )
        new_decision = adr(
            "NEW_DECISION",
            "design:successor",
            requirements=("NEW_DIRECTION",),
            supersedes=("adr:OLD_DECISION",),
        )

        issue_codes = codes(
            validate_graph(
                build_graph([original, old_decision, successor, new_decision])
            )
        )

        self.assertNotIn("CANCELLED_REQUIREMENT", issue_codes)

    def test_replaced_requirement_is_historical_not_current(self) -> None:
        original = design("original", introduces=("ORIGINAL_REQUIREMENT",))
        old_decision = adr(
            "OLD_DECISION",
            "design:original",
            requirements=("ORIGINAL_REQUIREMENT",),
        )
        successor = design(
            "successor",
            introduces=("NEW_REQUIREMENT",),
            replaces={"ORIGINAL_REQUIREMENT": "NEW_REQUIREMENT"},
            supersedes=("design:original",),
        )
        new_decision = adr(
            "NEW_DECISION",
            "design:successor",
            requirements=("NEW_REQUIREMENT",),
            supersedes=("adr:OLD_DECISION",),
        )
        valid_graph = build_graph([original, old_decision, successor, new_decision])

        self.assertNotIn("REPLACED_REQUIREMENT", codes(validate_graph(valid_graph)))

        invalid_current = adr(
            "INVALID_CURRENT",
            "design:successor",
            requirements=("ORIGINAL_REQUIREMENT",),
        )
        invalid_codes = codes(
            validate_graph(
                build_graph(
                    [original, old_decision, successor, new_decision, invalid_current]
                )
            )
        )

        self.assertIn("REPLACED_REQUIREMENT", invalid_codes)

    def test_rejects_process_requirement_used_by_product_architecture(self) -> None:
        process_design = design(
            "architecture-process",
            scope="process",
            introduces=("PROCESS_RULE",),
        )
        product_design = design("product")
        decision = adr(
            "PRODUCT_DECISION",
            "design:product",
            requirements=("PROCESS_RULE",),
        )

        issue_codes = codes(
            validate_graph(build_graph([process_design, product_design, decision]))
        )

        self.assertIn("PROCESS_REQUIREMENT_USED_BY_PRODUCT", issue_codes)

    def test_product_artifacts_cannot_claim_process_scope(self) -> None:
        process_design = design(
            "architecture-process",
            scope="process",
            introduces=("PROCESS_RULE",),
        )
        disguised = document(
            "adr",
            "DISGUISED_PRODUCT_DECISION",
            scope="process",
            design="design:architecture-process",
            requirements=["PROCESS_RULE"],
            aliases=[],
            supersedes=[],
            cancels=[],
            invariants={
                "introduces": [],
                "preserves": [],
                "replaces": {},
                "cancels": [],
            },
            contracts={
                "introduces": [],
                "preserves": [],
                "replaces": {},
                "cancels": [],
            },
        )

        self.assertIn(
            "INVALID_SCOPE",
            codes(validate_graph(build_graph([process_design, disguised]))),
        )

    def test_rejects_nonbootstrap_alias_and_adr_without_requirements(self) -> None:
        feature = design("feature")
        invalid = adr(
            "NEW_DECISION",
            "design:feature",
            aliases=("ADR-9999",),
        )

        issue_codes = codes(validate_graph(build_graph([feature, invalid])))

        self.assertIn("INVALID_ADR_ALIAS", issue_codes)
        self.assertIn("ADR_WITHOUT_REQUIREMENTS", issue_codes)

    def test_replacing_adr_disposes_all_dependent_artifacts(self) -> None:
        feature = design("feature", introduces=("FEATURE_EXISTS",))
        old_decision = adr(
            "OLD_DECISION",
            "design:feature",
            requirements=("FEATURE_EXISTS",),
            invariants={
                "introduces": ["invariant:FEATURE_STAYS_AVAILABLE"],
                "preserves": [],
                "replaces": {},
                "cancels": [],
            },
            contracts={
                "introduces": ["contract:FEATURE_API@1.0"],
                "preserves": [],
                "replaces": {},
                "cancels": [],
            },
        )
        invariant = document(
            "invariant",
            "FEATURE_STAYS_AVAILABLE",
            scope="product",
            introduced_by="adr:OLD_DECISION",
            requirements=["FEATURE_EXISTS"],
            check={"module": "tests.test_v8std_architecture_validation"},
        )
        contract = document(
            "contract",
            "FEATURE_API",
            scope="product",
            version=1,
            revision=0,
            compatibility="backward-compatible",
            design="design:feature",
            producer="producer",
            consumers=["consumer"],
            requirements=["FEATURE_EXISTS"],
            governs=["scripts/feature.py"],
            conformance={"module": "tests.test_v8std_architecture_validation"},
            supersedes=[],
            deprecates=[],
        )
        incomplete_successor = adr(
            "NEW_DECISION",
            "design:feature",
            requirements=("FEATURE_EXISTS",),
            supersedes=("adr:OLD_DECISION",),
        )

        incomplete_codes = codes(
            validate_graph(
                build_graph(
                    [feature, old_decision, invariant, contract, incomplete_successor]
                )
            )
        )
        self.assertIn("UNDISPOSED_INVARIANT", incomplete_codes)
        self.assertIn("UNDISPOSED_CONTRACT", incomplete_codes)

        complete_successor = adr(
            "NEW_DECISION",
            "design:feature",
            requirements=("FEATURE_EXISTS",),
            supersedes=("adr:OLD_DECISION",),
            invariants={
                "introduces": [],
                "preserves": ["invariant:FEATURE_STAYS_AVAILABLE"],
                "replaces": {},
                "cancels": [],
            },
            contracts={
                "introduces": [],
                "preserves": ["contract:FEATURE_API@1.0"],
                "replaces": {},
                "cancels": [],
            },
        )
        complete_codes = codes(
            validate_graph(
                build_graph(
                    [feature, old_decision, invariant, contract, complete_successor]
                )
            )
        )
        self.assertNotIn("UNDISPOSED_INVARIANT", complete_codes)
        self.assertNotIn("UNDISPOSED_CONTRACT", complete_codes)

    def test_rejects_invariant_without_basis_or_check(self) -> None:
        invalid = document(
            "invariant",
            "UNSUPPORTED_INVARIANT",
            scope="product",
            introduced_by=None,
            requirements=[],
            check={},
        )

        issue_codes = codes(validate_graph(build_graph([invalid])))

        self.assertIn("INVARIANT_WITHOUT_BASIS", issue_codes)
        self.assertIn("INVARIANT_WITHOUT_CHECK", issue_codes)

    def test_rejects_incomplete_contract_boundary(self) -> None:
        invalid = document(
            "contract",
            "INCOMPLETE_BOUNDARY",
            scope="product",
            revision=0,
            compatibility="backward-compatible",
            design="design:missing",
            producer="",
            consumers=[],
            requirements=[],
            governs=[],
            conformance={},
            supersedes=[],
            deprecates=[],
        )

        issue_codes = codes(validate_graph(build_graph([invalid])))

        self.assertIn("CONTRACT_WITHOUT_VERSION", issue_codes)
        self.assertIn("CONTRACT_WITHOUT_PRODUCER", issue_codes)
        self.assertIn("CONTRACT_WITHOUT_CONSUMERS", issue_codes)
        self.assertIn("CONTRACT_WITHOUT_CONFORMANCE", issue_codes)

    def test_rejects_retiring_invariant_while_requirement_remains_active(self) -> None:
        feature = design("feature", introduces=("FEATURE_SAFETY",))
        basis = adr("BASIS", "design:feature", requirements=("FEATURE_SAFETY",))
        invariant = document(
            "invariant",
            "FEATURE_IS_SAFE",
            scope="product",
            introduced_by="adr:BASIS",
            requirements=["FEATURE_SAFETY"],
            check={"module": "tests.test_v8std_architecture_validation"},
            required_when="accepted",
        )
        retirement = adr(
            "RETIREMENT",
            "design:feature",
            requirements=("FEATURE_SAFETY",),
            invariants={
                "introduces": [],
                "preserves": [],
                "replaces": {},
                "cancels": ["invariant:FEATURE_IS_SAFE"],
            },
        )

        issue_codes = codes(
            validate_graph(build_graph([feature, basis, invariant, retirement]))
        )

        self.assertIn("PREMATURE_RETIREMENT", issue_codes)

    def test_historical_alias_is_allowed_in_prose_but_not_current_reference(self) -> None:
        feature = design("feature")
        decision = adr(
            "PAGE_READING_VIA_RESOURCES",
            "design:feature",
            aliases=("ADR-0004",),
            body="Historical note: ADR-0004 used the old identity.",
        )
        valid_codes = codes(validate_graph(build_graph([feature, decision])))
        invalid_plan = document(
            "plan",
            "alias-user",
            design="design:feature",
            implements=["adr:ADR-0004"],
            checkbox_count=1,
            checked_count=1,
        )
        invalid_codes = codes(validate_graph(build_graph([feature, decision, invalid_plan])))

        self.assertNotIn("HISTORICAL_ALIAS_REFERENCE", valid_codes)
        self.assertIn("HISTORICAL_ALIAS_REFERENCE", invalid_codes)

    def test_plan_owns_design_association_without_reverse_plan_field(self) -> None:
        feature = design("feature")
        implementation = document(
            "plan",
            "feature-implementation",
            design="design:feature",
            implements=["design:feature"],
            checkbox_count=1,
            checked_count=1,
        )

        issue_codes = codes(validate_graph(build_graph([feature, implementation])))

        self.assertNotIn("MISSING_REQUIRED_FIELD", issue_codes)

    def test_incomplete_candidate_is_valid_but_not_merge_ready(self) -> None:
        feature = design("feature")
        candidate = document(
            "plan",
            "feature",
            design="design:feature",
            implements=["design:feature"],
            checkbox_count=2,
            checked_count=1,
        )
        graph = build_graph([feature, candidate])

        self.assertNotIn("INCOMPLETE_PLAN", codes(validate_graph(graph)))
        self.assertIn("INCOMPLETE_PLAN", codes(validate_merge_readiness(graph)))
        self.assertEqual(
            compute_states(graph, frozenset(graph.documents))["design:feature"],
            frozenset({"ACCEPTED"}),
        )

    def test_complete_plan_implements_only_explicit_targets(self) -> None:
        first = design("first")
        second = design("second")
        plan = document(
            "plan",
            "first",
            design="design:first",
            implements=["design:first"],
            checkbox_count=1,
            checked_count=1,
        )
        graph = build_graph([first, second, plan])

        states = compute_states(graph, frozenset(graph.documents))

        self.assertEqual(states["design:first"], frozenset({"ACCEPTED", "IMPLEMENTED"}))
        self.assertEqual(states["design:second"], frozenset({"ACCEPTED"}))

    def test_computes_superseded_cancelled_deprecated_and_retired_states(self) -> None:
        feature = design("feature")
        old_decision = adr("OLD_DECISION", "design:feature")
        cancelled_decision = adr("CANCELLED_DECISION", "design:feature")
        old_invariant = document(
            "invariant",
            "OLD_INVARIANT",
            scope="product",
            introduced_by="adr:OLD_DECISION",
            requirements=[],
            check={"module": "tests.test_v8std_architecture_validation"},
        )
        old_contract = document(
            "contract",
            "OLD_CONTRACT",
            scope="product",
            version=1,
            revision=0,
            compatibility="backward-compatible",
            design="design:feature",
            producer="producer",
            consumers=["consumer"],
            requirements=[],
            governs=["scripts/old.py"],
            conformance={"module": "tests.test_v8std_architecture_validation"},
            supersedes=[],
            deprecates=[],
        )
        successor = adr(
            "SUCCESSOR",
            "design:feature",
            supersedes=("adr:OLD_DECISION",),
            cancels=("adr:CANCELLED_DECISION",),
            invariants={
                "introduces": [],
                "preserves": [],
                "replaces": {},
                "cancels": ["invariant:OLD_INVARIANT"],
            },
            contracts={
                "introduces": [],
                "preserves": [],
                "replaces": {},
                "cancels": ["contract:OLD_CONTRACT@1.0"],
            },
        )
        graph = build_graph(
            [
                feature,
                old_decision,
                cancelled_decision,
                old_invariant,
                old_contract,
                successor,
            ]
        )

        states = compute_states(graph, frozenset(graph.documents))

        self.assertEqual(states["adr:OLD_DECISION"], frozenset({"SUPERSEDED"}))
        self.assertEqual(states["adr:CANCELLED_DECISION"], frozenset({"CANCELLED"}))
        self.assertEqual(states["invariant:OLD_INVARIANT"], frozenset({"RETIRED"}))
        self.assertEqual(states["contract:OLD_CONTRACT@1.0"], frozenset({"DEPRECATED"}))

    def test_fitness_evidence_is_deferred_until_implemented(self) -> None:
        feature = design("feature")
        future_contract = document(
            "contract",
            "FUTURE_API",
            scope="product",
            version=1,
            revision=0,
            compatibility="backward-compatible",
            design="design:feature",
            producer="future producer",
            consumers=["future consumer"],
            requirements=[],
            governs=["scripts/future.py"],
            conformance={"module": "tests.test_module_that_does_not_exist"},
            required_when="implemented",
            supersedes=[],
            deprecates=[],
        )
        graph = build_graph([feature, future_contract])

        self.assertNotIn(
            "MISSING_FITNESS_EVIDENCE",
            codes(validate_merge_readiness(graph)),
        )

        implementation_plan = document(
            "plan",
            "future-api",
            design="design:feature",
            implements=["contract:FUTURE_API@1.0"],
            checkbox_count=1,
            checked_count=1,
        )
        implemented_graph = build_graph([feature, future_contract, implementation_plan])
        self.assertIn(
            "MISSING_FITNESS_EVIDENCE",
            codes(validate_merge_readiness(implemented_graph)),
        )

    def test_terminal_contracts_do_not_require_fitness_evidence(self) -> None:
        for relation, terminal_state in (
            ("supersedes", "SUPERSEDED"),
            ("cancels", "CANCELLED"),
            ("deprecates", "DEPRECATED"),
        ):
            for required_when in ("accepted", "implemented"):
                with self.subTest(relation=relation, required_when=required_when):
                    feature = design("feature")
                    fields = {
                        "scope": "product",
                        "version": 1,
                        "revision": 0,
                        "compatibility": "backward-compatible",
                        "design": "design:feature",
                        "producer": "producer",
                        "consumers": ["consumer"],
                        "requirements": [],
                        "governs": ["scripts/feature.py"],
                        "conformance": {"module": "tests.test_module_that_does_not_exist"},
                        "required_when": required_when,
                        "supersedes": [],
                        "deprecates": [],
                    }
                    old_contract = document("contract", "OLD_API", **fields)
                    active_contract = document("contract", "ACTIVE_API", **fields)
                    successor = document(
                        "contract",
                        "SUCCESSOR_API",
                        **{
                            **fields,
                            relation: ["contract:OLD_API@1.0"],
                            "conformance": {"module": "tests.test_v8std_architecture_validation"},
                        },
                    )
                    documents = [feature, old_contract, active_contract, successor]
                    expected_state = {terminal_state}
                    if required_when == "implemented":
                        documents.append(
                            document(
                                "plan",
                                "feature",
                                design="design:feature",
                                implements=["contract:OLD_API@1.0", "contract:ACTIVE_API@1.0"],
                                checkbox_count=1,
                                checked_count=1,
                            )
                        )
                        expected_state.add("IMPLEMENTED")
                    graph = build_graph(documents)
                    self.assertEqual(validate_graph(graph), [])
                    self.assertEqual(
                        compute_states(graph, frozenset(graph.documents))["contract:OLD_API@1.0"],
                        frozenset(expected_state),
                    )

                    issues = validate_merge_readiness(graph)

                    self.assertEqual(
                        [(item.code, item.path) for item in issues],
                        [("MISSING_FITNESS_EVIDENCE", "spec/contract/active-api-v1-r0.md")],
                    )
                    # Terminal artifacts still participate in reference validation.
                    unresolved_graph = build_graph(documents[1:])
                    self.assertEqual(
                        sorted(
                            item.path for item in validate_graph(unresolved_graph)
                            if item.code == "DANGLING_REFERENCE" and "spec/contract/" in item.path
                        ),
                        [
                            "spec/contract/active-api-v1-r0.md",
                            "spec/contract/old-api-v1-r0.md",
                            "spec/contract/successor-api-v1-r0.md",
                        ],
                    )

    def test_retired_invariant_does_not_require_fitness_evidence(self) -> None:
        for required_when in ("accepted", "implemented"):
            with self.subTest(required_when=required_when):
                feature = design("feature", introduces=("OLD_REQUIREMENT", "ACTIVE_REQUIREMENT"))
                old_decision = adr("OLD_DECISION", "design:feature", requirements=("OLD_REQUIREMENT",))
                old_invariant = document(
                    "invariant",
                    "OLD_INVARIANT",
                    scope="product",
                    introduced_by="adr:OLD_DECISION",
                    requirements=["OLD_REQUIREMENT"],
                    check={"module": "tests.test_module_that_does_not_exist"},
                    required_when=required_when,
                )
                active_invariant = document(
                    "invariant",
                    "ACTIVE_INVARIANT",
                    scope="product",
                    introduced_by="adr:SUCCESSOR",
                    requirements=["ACTIVE_REQUIREMENT"],
                    check={"module": "tests.test_module_that_does_not_exist"},
                    required_when=required_when,
                )
                documents = [feature, old_decision, old_invariant, active_invariant]
                if required_when == "implemented":
                    documents.append(
                        document(
                            "plan",
                            "feature",
                            design="design:feature",
                            implements=["invariant:OLD_INVARIANT", "invariant:ACTIVE_INVARIANT"],
                            checkbox_count=1,
                            checked_count=1,
                        )
                    )
                    before_retirement = build_graph(documents)
                    self.assertEqual(
                        compute_states(before_retirement, frozenset(before_retirement.documents))[
                            "invariant:OLD_INVARIANT"
                        ],
                        frozenset({"ACCEPTED", "IMPLEMENTED"}),
                    )
                retirement = design(
                    "retirement",
                    uses=("ACTIVE_REQUIREMENT",),
                    requirement_cancels=("OLD_REQUIREMENT",),
                )
                successor = adr(
                    "SUCCESSOR",
                    "design:retirement",
                    requirements=("ACTIVE_REQUIREMENT",),
                    cancels=("adr:OLD_DECISION",),
                    invariants={
                        "introduces": ["invariant:ACTIVE_INVARIANT"],
                        "preserves": [],
                        "replaces": {},
                        "cancels": ["invariant:OLD_INVARIANT"],
                    },
                )
                graph = build_graph([*documents, retirement, successor])
                self.assertEqual(validate_graph(graph), [])
                self.assertEqual(
                    compute_states(graph, frozenset(graph.documents))["invariant:OLD_INVARIANT"],
                    frozenset({"RETIRED", "IMPLEMENTED"} if required_when == "implemented" else {"RETIRED"}),
                )

                issues = validate_merge_readiness(graph)

                self.assertEqual(
                    [(item.code, item.path) for item in issues],
                    [("MISSING_FITNESS_EVIDENCE", "spec/invariant/active-invariant.md")],
                )

    def test_rejects_unknown_fitness_timing(self) -> None:
        feature = design("feature")
        contract = document(
            "contract",
            "FUTURE_API",
            scope="product",
            version=1,
            revision=0,
            compatibility="backward-compatible",
            design="design:feature",
            producer="producer",
            consumers=["consumer"],
            requirements=[],
            governs=["scripts/future.py"],
            conformance={"module": "tests.test_v8std_architecture_validation"},
            required_when="implmented",
            supersedes=[],
            deprecates=[],
        )

        self.assertIn(
            "INVALID_FITNESS_TIMING",
            codes(validate_graph(build_graph([feature, contract]))),
        )


if __name__ == "__main__":
    unittest.main()
