#!/usr/bin/env python3
"""Deterministic CLI for the v8std architecture process."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.v8std_architecture_model import (  # noqa: E402
    ArchitectureModelError,
    build_graph,
    discover_documents,
    load_process_schema,
)
from scripts.v8std_architecture_validation import (  # noqa: E402
    ValidationIssue,
    _load_base_documents,
    compute_states,
    find_impact_candidates,
    validate_frozen_documents,
    validate_graph,
    validate_merge_readiness,
)


def _print_issues(issues: Sequence[ValidationIssue]) -> None:
    for issue in sorted(set(issues)):
        print(f"{issue.code} {issue.path}: {issue.message}")


def _load_graph(root: Path):
    schema = load_process_schema(root)
    graph = build_graph(discover_documents(root, schema))
    return schema, graph


def command_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        schema, graph = _load_graph(root)
    except (ArchitectureModelError, OSError) as error:
        _print_issues([ValidationIssue("MODEL_ERROR", ".", str(error))])
        return 1

    issues = validate_graph(graph)
    if args.base_ref:
        issues.extend(validate_frozen_documents(root, args.base_ref, graph, schema))
    if args.merge_ready:
        issues.extend(validate_merge_readiness(graph))
    issues = sorted(set(issues))
    _print_issues(issues)
    return 1 if issues else 0


def command_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        schema, graph = _load_graph(root)
    except (ArchitectureModelError, OSError) as error:
        _print_issues([ValidationIssue("MODEL_ERROR", ".", str(error))])
        return 1

    accepted_keys: frozenset[str]
    if args.main_ref:
        base_documents, issues = _load_base_documents(root, args.main_ref, schema)
        if issues:
            _print_issues(issues)
            return 1
        accepted_keys = frozenset(base_documents).intersection(graph.documents)
    else:
        accepted_keys = frozenset(graph.documents)
    for key, states in compute_states(graph, accepted_keys).items():
        print(f"{key}\t{','.join(sorted(states))}")
    return 0


def command_impact(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        _, graph = _load_graph(root)
    except (ArchitectureModelError, OSError) as error:
        _print_issues([ValidationIssue("MODEL_ERROR", ".", str(error))])
        return 1

    commands = (
        ["git", "diff", "--name-only", f"{args.base_ref}...HEAD"],
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    )
    try:
        results = [
            subprocess.run(
                command,
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            for command in commands
        ]
    except FileNotFoundError:
        _print_issues([ValidationIssue("GIT_UNAVAILABLE", ".", "git executable is unavailable")])
        return 1
    failed = next((result for result in results if result.returncode != 0), None)
    if failed is not None:
        _print_issues(
            [
                ValidationIssue(
                    "BASE_REF_UNRESOLVED",
                    ".",
                    failed.stderr.strip() or f"cannot inspect changes from {args.base_ref}",
                )
            ]
        )
        return 1
    changed_paths = sorted(
        {
            line
            for result in results
            for line in result.stdout.splitlines()
            if line
        }
    )
    for key, path in find_impact_candidates(graph, changed_paths):
        print(f"{key}\t{path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate artifact graph")
    validate_parser.add_argument("--root", default=".")
    validate_parser.add_argument("--base-ref")
    validate_parser.add_argument("--merge-ready", action="store_true")
    validate_parser.set_defaults(handler=command_validate)

    status_parser = subparsers.add_parser("status", help="print computed artifact states")
    status_parser.add_argument("--root", default=".")
    status_parser.add_argument("--main-ref", default="main")
    status_parser.set_defaults(handler=command_status)

    impact_parser = subparsers.add_parser("impact", help="list governed changed paths")
    impact_parser.add_argument("--root", default=".")
    impact_parser.add_argument("--base-ref", required=True)
    impact_parser.set_defaults(handler=command_impact)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
