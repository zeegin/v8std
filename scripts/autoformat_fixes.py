from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STANDARD_RE = re.compile(r"^std\d+$")
CLAUSE_RE = re.compile(r"^(?:std\d+|\d+(?:\.\d+)*)$")


@dataclass(frozen=True)
class AutoformatFix:
    key: str
    standard: str
    clause: str
    anchor: str
    description: str
    source_url: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AutoformatFix":
        required = {
            "key",
            "standard",
            "clause",
            "anchor",
            "description",
            "source_url",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise ValueError("autoformat fix must contain the exact supported fields")
        for field in ("key", "description", "source_url"):
            if not isinstance(payload[field], str) or not payload[field].strip():
                raise ValueError(f"autoformat fix {field} must be a non-empty string")
        standard = payload["standard"]
        clause = payload["clause"]
        anchor = payload["anchor"]
        if not isinstance(standard, str) or not STANDARD_RE.fullmatch(standard):
            raise ValueError(f"invalid autoformat standard: {standard}")
        if not isinstance(clause, str) or not CLAUSE_RE.fullmatch(clause):
            raise ValueError(f"invalid autoformat clause: {clause}")
        if clause.startswith("std") and clause != standard:
            raise ValueError("whole-standard autoformat clause must match standard")
        if not isinstance(anchor, str) or not anchor:
            raise ValueError("autoformat anchor must be a non-empty string")
        if not payload["source_url"].startswith("https://its.1c.ru/db/v8std"):
            raise ValueError("autoformat source must be an ITS standards URL")
        return cls(**payload)


@dataclass(frozen=True)
class AutoformatCatalog:
    version: int
    tool_url: str
    download_url: str
    artifact_sha256: str
    fixes: tuple[AutoformatFix, ...]


def load_autoformat_catalog(path: Path) -> AutoformatCatalog:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "version",
        "tool_url",
        "download_url",
        "artifact_sha256",
        "fixes",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("autoformat catalog has unexpected fields")
    if payload["version"] != 1:
        raise ValueError("unsupported autoformat catalog version")
    for field in ("tool_url", "download_url", "artifact_sha256"):
        if not isinstance(payload[field], str) or not payload[field]:
            raise ValueError(f"autoformat catalog {field} must be a non-empty string")
    if not re.fullmatch(r"[0-9a-f]{64}", payload["artifact_sha256"]):
        raise ValueError("autoformat artifact_sha256 must be SHA-256")
    if not isinstance(payload["fixes"], list) or not payload["fixes"]:
        raise ValueError("autoformat fixes must be a non-empty array")
    fixes = tuple(AutoformatFix.from_dict(item) for item in payload["fixes"])
    keys = [item.key for item in fixes]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate autoformat fix key")
    return AutoformatCatalog(
        version=payload["version"],
        tool_url=payload["tool_url"],
        download_url=payload["download_url"],
        artifact_sha256=payload["artifact_sha256"],
        fixes=fixes,
    )

