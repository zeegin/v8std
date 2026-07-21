#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any

from v8std_retrieval_rules import tokenize
from atomic_files import atomic_write_text


DEFAULT_DIM = 256
DEFAULT_MODEL = "v8std-hash-embeddings-v1"
MAX_CHUNK_CHARS = 2200


def signed_hash(value: str) -> tuple[int, float]:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    number = int.from_bytes(digest, "little")
    return number, -1.0 if number & 1 else 1.0


def embed_text(value: str, *, dim: int = DEFAULT_DIM) -> list[float]:
    vector = [0.0] * dim
    tokens = tokenize(value)
    features: list[str] = []
    features.extend(tokens)
    features.extend(f"{left}_{right}" for left, right in zip(tokens, tokens[1:]))

    for token in tokens:
        if len(token) >= 5:
            for index in range(0, len(token) - 2):
                features.append(f"char:{token[index:index + 3]}")

    if not features:
        return vector

    for feature in features:
        hashed, sign = signed_hash(feature)
        vector[hashed % dim] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def encode_vector(vector: list[float]) -> str:
    return base64.b64encode(struct.pack(f"<{len(vector)}f", *vector)).decode("ascii")


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


def generate_rows(pages_path: Path, *, dim: int = DEFAULT_DIM, model: str = DEFAULT_MODEL) -> list[str]:
    rows: list[str] = []
    with pages_path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            page = json.loads(line)
            for field, chunk_index, text in page_chunks(page):
                payload = {
                    "id": page["id"],
                    "field": field,
                    "chunk_index": chunk_index,
                    "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "model": model,
                    "dim": dim,
                    "vector_base64": encode_vector(embed_text(text, dim=dim)),
                }
                rows.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate static v8std MCP search vectors.")
    parser.add_argument("--pages", type=Path, default=Path("docs/ai/pages.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("docs/ai/search-vectors.jsonl"))
    parser.add_argument("--dim", type=int, default=DEFAULT_DIM)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = generate_rows(args.pages, dim=args.dim, model=args.model)
    atomic_write_text(args.output, "\n".join(rows) + "\n")
    print(f"wrote {len(rows)} vectors to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
