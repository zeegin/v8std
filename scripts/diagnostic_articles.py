from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+$")


@dataclass(frozen=True)
class SourceFamily:
    family: str
    repository: str
    revision: str
    license: str
    source_root: str


def normalize_article(source: str) -> tuple[str, str]:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.splitlines()
    first = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first is None or not lines[first].startswith("# "):
        raise ValueError("first non-empty line must be H1")

    title = lines[first][2:].strip()
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
