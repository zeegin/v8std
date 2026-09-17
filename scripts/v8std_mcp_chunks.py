"""Shared canonical chunk rules for vector generation and snapshot verification."""

from __future__ import annotations

import re
from typing import Any


MAX_CHUNK_CHARS = 2200


def page_chunks(page: dict[str, Any]) -> list[tuple[str, int, str]]:
    metadata = " ".join(
        [
            page.get("id", ""),
            page.get("title", ""),
            page.get("description", ""),
            " ".join(page.get("aliases", [])),
        ]
    ).strip()
    chunks: list[tuple[str, int, str]] = []
    if metadata:
        chunks.append(("metadata", 0, metadata))

    body = page.get("body_markdown") or ""
    paragraphs = [item.strip() for item in re.split(r"\n{2,}", body) if item.strip()]
    current: list[str] = []
    current_len = 0
    chunk_index = 0
    for paragraph in paragraphs:
        next_len = current_len + len(paragraph) + 2
        if current and next_len > MAX_CHUNK_CHARS:
            chunks.append(("body", chunk_index, "\n\n".join(current)))
            chunk_index += 1
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += len(paragraph) + 2
    if current:
        chunks.append(("body", chunk_index, "\n\n".join(current)))

    return chunks
