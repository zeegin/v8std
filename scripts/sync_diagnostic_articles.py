#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from diagnostic_articles import SourceFamily, synchronize_articles


SOURCE_FAMILIES = (
    SourceFamily(
        family="bslls",
        repository="https://github.com/1c-syntax/bsl-language-server",
        revision="f4616cda8a216789ee40529ed857e614b9e2ea25",
        license="LGPL-3.0-or-later",
        source_root="docs/diagnostics",
    ),
    SourceFamily(
        family="v8-code-style",
        repository="https://github.com/1C-Company/v8-code-style",
        revision="c8fe7932babf718c0ace3cf836a99d6a3b98d098",
        license="EPL-2.0",
        source_root="bundles",
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Synchronize local diagnostic articles with pinned upstream checkouts."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail when committed output drifts")
    mode.add_argument("--write", action="store_true", help="write deterministic generated output")
    parser.add_argument("--bslls-checkout", type=Path, required=True)
    parser.add_argument("--v8-code-style-checkout", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    changed = synchronize_articles(
        repo_root=args.repo_root.resolve(),
        checkouts={
            "bslls": args.bslls_checkout.resolve(),
            "v8-code-style": args.v8_code_style_checkout.resolve(),
        },
        families=SOURCE_FAMILIES,
        write=args.write,
    )
    if args.check and changed:
        for path in changed:
            print(path.relative_to(args.repo_root.resolve()))
        print(f"diagnostic article drift: {len(changed)} files")
        return 1
    if args.write:
        print(f"diagnostic articles written: {len(changed)} files")
    else:
        print("diagnostic articles clean: 358")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
