#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote


ROUTE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def route_segment(value: object, context: str) -> str:
    if not isinstance(value, str) or not ROUTE_SEGMENT_RE.fullmatch(value):
        raise ValueError(f"invalid {context}: {value!r}")
    return value


def load_diagnostic_inventory(repo_root: Path) -> dict[str, tuple[str, ...]]:
    source_catalog = json.loads(
        (repo_root / "data/diagnostic-sources.json").read_text(encoding="utf-8")
    )
    if (
        not isinstance(source_catalog, dict)
        or source_catalog.get("version") != 1
        or not isinstance(source_catalog.get("families"), list)
    ):
        raise ValueError("diagnostic source inventory requires version 1 and families")
    inventory: dict[str, tuple[str, ...]] = {}

    for family in source_catalog["families"]:
        if not isinstance(family, dict) or not isinstance(
            family.get("diagnostics"), list
        ):
            raise ValueError("invalid diagnostic family entry")
        family_name = route_segment(family.get("family"), "diagnostic family")
        if family_name in inventory:
            raise ValueError(f"duplicate diagnostic family: {family_name}")
        diagnostic_ids = []
        for diagnostic in family["diagnostics"]:
            if not isinstance(diagnostic, dict):
                raise ValueError(f"invalid diagnostic entry in family: {family_name}")
            diagnostic_ids.append(
                route_segment(diagnostic.get("id"), "diagnostic id")
            )
        inventory[family_name] = tuple(diagnostic_ids)

    if "acc" in inventory:
        raise ValueError("duplicate diagnostic family: acc")
    acc_catalog = json.loads(
        (repo_root / "data/acc-diagnostics.json").read_text(encoding="utf-8")
    )
    if (
        not isinstance(acc_catalog, dict)
        or acc_catalog.get("version") != 1
        or not isinstance(acc_catalog.get("diagnostics"), list)
    ):
        raise ValueError("ACC inventory requires version 1 and diagnostics")
    acc_ids = []
    for diagnostic in acc_catalog["diagnostics"]:
        code = diagnostic.get("code") if isinstance(diagnostic, dict) else None
        if not isinstance(code, str) or not code.isdigit():
            raise ValueError(f"invalid diagnostic id for acc: {code!r}")
        acc_ids.append(code)
    inventory["acc"] = tuple(acc_ids)

    for family_name, diagnostic_ids in inventory.items():
        if len(diagnostic_ids) != len(set(diagnostic_ids)):
            raise ValueError(f"duplicate diagnostic id in family: {family_name}")

    return inventory


def diagnostic_family_counts(repo_root: Path) -> dict[str, int]:
    return {
        family: len(diagnostic_ids)
        for family, diagnostic_ids in load_diagnostic_inventory(repo_root).items()
    }


def diagnostic_urls(repo_root: Path, site_url: str) -> tuple[str, ...]:
    base_url = site_url.rstrip("/")
    inventory = load_diagnostic_inventory(repo_root)
    return tuple(
        f"{base_url}/diagnostics/{quote(family, safe='-._~')}/"
        f"{quote(diagnostic_id, safe='-._~')}/"
        for family in sorted(inventory)
        for diagnostic_id in sorted(inventory[family])
    )
